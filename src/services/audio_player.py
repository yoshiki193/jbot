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

    async def enqueue(self, buffer):
        async with self.lock:
            self.queue.append(buffer)
            if not self.playing:
                self.playing = True
                asyncio.create_task(self._play_loop())

    async def _play_loop(self):
        while True:
            if not self.vc or not self.vc.is_connected():
                async with self.lock:
                    self.queue.clear()
                    self.playing = False
                return
            
            async with self.lock:
                if not self.queue:
                    self.playing = False
                    return
                buffer = self.queue.popleft()

            source = FFmpegPCMAudio(buffer, pipe=True)
            done = asyncio.Event()

            self.vc.play(source, after=lambda _: done.set())
            await done.wait()
