import discord
import asyncio
from collections import deque
from discord import FFmpegPCMAudio
from services.voicevox_service import VoiceVoxService

class AudioPlayer:
    def __init__(self, vc: discord.VoiceClient, voicevox: VoiceVoxService):
        self.vc = vc
        self.voicevox = voicevox
        self.queue = deque()
        self.lock = asyncio.Lock()
        self.playing = False

    async def enqueue(self, content: str, speaker: int, voicevox_url: str):
        buffer = await self.voicevox.synthesize(
            content,
            speaker
        )
        async with self.lock:
            self.queue.append(buffer)
            if not self.playing:
                self.playing = True
                asyncio.create_task(self._play_next())

    async def _play_next(self):
        async with self.lock:
            if not self.queue or not self.vc or not self.vc.is_connected():
                self.playing = False
                self.queue.clear()
                return

            buffer = self.queue.popleft()

        source = FFmpegPCMAudio(
            buffer,
            pipe=True,
            before_options="-fflags nobuffer -flags low_delay -probesize 32 -analyzeduration 0"
        )

        def after(_):
            source.cleanup()
            asyncio.run_coroutine_threadsafe(self._play_next(), self.vc.loop)

        self.vc.play(source, after=after)