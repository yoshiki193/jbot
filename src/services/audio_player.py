import discord
import asyncio
from collections import deque
from discord import FFmpegPCMAudio

class AudioPlayer:
    def __init__(self, vc: discord.VoiceClient):
        self.vc = vc
        self.queue = deque()
        self.lock = asyncio.Lock()
        self.playing = False

    async def enqueue(self, content, speaker, voicevox, voicevox_url):
        buffer = await voicevox.synthesize(
            content,
            speaker,
            voicevox_url
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
            asyncio.run_coroutine_threadsafe(self._play_next(), self.vc.loop)

        self.vc.play(source, after=after)