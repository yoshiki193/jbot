import discord
import logging
import datetime
import asyncio
from services.audio_player import AudioPlayer

class AudioManager:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.players: dict[tuple[int, int], AudioPlayer] = {}
        self.connect_time: dict[tuple[int,int], datetime.datetime] = {}
        self.idol_time: dict[tuple[int,int], datetime.datetime] = {}
    
    def connected_guild_count(self) -> int:
        return len({guild_id for guild_id, _ in self.players.keys()})
    
    def connected_time_count(self) -> int:
        return len([guild_id for guild_id, _ in self.connect_time.keys()])
    
    def is_connected_channel(self, guild_id: int, channel_id: int) -> bool:
        vc = self.get_connected_vc(guild_id)
        return vc is not None and vc.channel.id == channel_id
    
    def get_connected_vc(self, guild_id: int):
        for (gid, _), player in self.players.items():
            if gid == guild_id:
                return player.vc
        return None
    
    async def connect_vc(self, guild_id: int, channel: discord.VoiceChannel) -> bool:
        if self.get_connected_vc(guild_id):
            return False 

        try:
            vc = await channel.connect(self_deaf=True)
        except Exception:
            self.logger.exception(
                "VC connect failed: guild=%s channel=%s",
                guild_id,
                channel.id,
            )
            return False

        self.add_vc(guild_id, channel.id, vc)
        return True

    def add_vc(self, guild_id: int, channel_id: int, vc):
        key = (guild_id, channel_id)
    
        self.players[key] = AudioPlayer(vc)
        self.connect_time[key] = datetime.datetime.now()

        self.logger.info(
            "VC connected: guild=%s channel=%s | connected guilds=%d",
            guild_id,
            channel_id,
            self.connected_guild_count()
        )
    
    async def update_vc(self, bot, voicevox):
        now = datetime.datetime.now()
        keys = list(self.players.keys())
        
        for guild_id, channel_id in keys:
            connect_time = self.connect_time.get((guild_id, channel_id))
            if connect_time and (now - connect_time).total_seconds() >= 8 * 3600:
                buffer = await voicevox.synthesize(
                    "再接続します",
                    0
                )
                await self.play(
                    guild_id,
                    channel_id,
                    buffer
                )

                await asyncio.sleep(2)

                channel = await bot.fetch_channel(channel_id)

                await self.disconnect_vc(guild_id, channel_id)
                await self.connect_vc(guild_id, channel)
                self.logger.info(
                    "VC reconnected: guild=%s channel=%s | connected guilds=%d time count=%d",
                    guild_id,
                    channel_id,
                    self.connected_guild_count(),
                    self.connected_time_count()
                )
    
    async def self_disconnect(self, repo):
        now = datetime.datetime.now()
        keys = list(self.players.keys())
        
        for guild_id, channel_id in keys:
            if repo.get_active_vv(str(guild_id)) == channel_id:
                idol_time = self.idol_time.get((guild_id, channel_id))
                if idol_time and (now - idol_time).total_seconds() >= 15 * 60:
                    await self.disconnect_vc(guild_id, channel_id)


    async def disconnect_vc(self, guild_id: int, channel_id: int):
        key = (guild_id, channel_id)
        player = self.players.get(key)

        if not player:
            return False
        try:
            if player.vc and player.vc.is_connected():
                if player.vc.is_playing():
                    player.vc.stop()
                
                await player.vc.disconnect()
            
            self.logger.info(
                "VC disconnected: guild=%s channel=%s | connected guilds=%d",
                guild_id,
                channel_id,
                self.connected_guild_count()
            )
        except Exception:
            self.logger.exception(
                "VC disconnect failed: guild=%s channel=%s",
                guild_id,
                channel_id,
            )
        finally:
            self.players.pop(key, None)
            self.connect_time.pop(key, None)
        return True

    async def play(self, guild_id: int, channel_id: int, buffer):
        key = (guild_id, channel_id)
        player = self.players.get((guild_id, channel_id))
        if player:
            self.idol_time[key] = datetime.datetime.now()
            await player.enqueue(buffer)