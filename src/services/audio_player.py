import asyncio
import io
import logging
import discord
from services.voicevox_service import VoiceVoxService

logger = logging.getLogger(__name__)

FFMPEG_BEFORE_OPTIONS = "-fflags nobuffer -flags low_delay -probesize 32 -analyzeduration 0"

class AudioPlayer:
    """1 ギルド分の読み上げキュー。

    合成は投稿と同時に並列で始め、再生は投稿順に 1 件ずつ行う。
    """

    def __init__(self, vc: discord.VoiceClient, voicevox: VoiceVoxService):
        self.vc = vc
        self.voicevox = voicevox
        self.connected_at = discord.utils.utcnow()
        self.last_active_at = self.connected_at
        self._queue: asyncio.Queue[asyncio.Task[bytes]] = asyncio.Queue()
        self._current: asyncio.Task[bytes] | None = None
        self._worker = asyncio.create_task(self._run())

    def enqueue(self, text: str, speaker: int):
        self.last_active_at = discord.utils.utcnow()
        self._queue.put_nowait(asyncio.create_task(self.voicevox.synthesize(text, speaker)))

    def clear(self):
        while True:
            try:
                task = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            task.cancel()
            self._queue.task_done()

        if self._current is not None:
            self._current.cancel()
        if self.vc.is_playing():
            self.vc.stop()

    async def wait_until_idle(self, timeout: float):
        try:
            await asyncio.wait_for(self._queue.join(), timeout)
        except asyncio.TimeoutError:
            pass

    async def close(self):
        self._worker.cancel()
        self.clear()
        try:
            await self._worker
        except asyncio.CancelledError:
            pass

    async def _run(self):
        while True:
            task = await self._queue.get()
            self._current = task
            try:
                await asyncio.wait([task])
                if task.cancelled():
                    continue
                if task.exception() is not None:
                    logger.error("synthesis failed", exc_info = task.exception())
                    continue
                await self._play(task.result())
            except asyncio.CancelledError:
                task.cancel()
                raise
            except Exception:
                logger.exception("playback failed: guild=%s", self.vc.guild.id)
            finally:
                self._current = None
                self._queue.task_done()

    async def _play(self, wav: bytes):
        if not self.vc.is_connected():
            return

        loop = asyncio.get_running_loop()
        finished = asyncio.Event()

        def after(error: Exception | None):
            if error:
                logger.error("playback error: %s", error)
            loop.call_soon_threadsafe(finished.set)

        source = discord.FFmpegPCMAudio(
            io.BytesIO(wav),
            pipe = True,
            before_options = FFMPEG_BEFORE_OPTIONS
        )
        try:
            self.vc.play(source, after = after)
        except Exception:
            source.cleanup()
            raise
        await finished.wait()
