import asyncio
import datetime
import logging
from collections import defaultdict
import discord
from repositories.data_repository import DataRepository
from services.audio_player import AudioPlayer
from services.voicevox_service import VoiceVoxService

logger = logging.getLogger(__name__)

IDLE_TIMEOUT = datetime.timedelta(minutes = 10)
RECONNECT_INTERVAL = datetime.timedelta(hours = 8)
RECONNECT_NOTICE = "再接続します"
DEFAULT_SPEAKER = 0

def has_listeners(channel: discord.abc.Connectable) -> bool:
    return any(not member.bot for member in channel.members)

class AudioManager:
    """ギルドごとの VC 接続と読み上げキューを管理する（1 ギルドにつき 1 接続）。"""

    def __init__(self, repo: DataRepository, voicevox: VoiceVoxService):
        self.repo = repo
        self.voicevox = voicevox
        self.players: dict[int, AudioPlayer] = {}
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    def get_vc(self, guild_id: int) -> discord.VoiceClient | None:
        player = self.players.get(guild_id)
        return player.vc if player else None

    def is_connected_channel(self, guild_id: int, channel_id: int) -> bool:
        vc = self.get_vc(guild_id)
        return vc is not None and vc.channel.id == channel_id

    def speak(self, guild_id: int, text: str, member_id: int | None = None) -> bool:
        player = self.players.get(guild_id)
        if player is None:
            return False

        speaker = DEFAULT_SPEAKER
        if member_id is not None:
            stored = self.repo.get_voicevox_speaker(guild_id, member_id)
            if stored is not None:
                speaker = stored

        player.enqueue(text, speaker)
        return True

    async def connect(self, channel: discord.VoiceChannel) -> bool:
        async with self._locks[channel.guild.id]:
            if channel.guild.id in self.players:
                return False
            return await self._connect(channel)

    async def ensure_connected(self, channel: discord.VoiceChannel) -> bool:
        """指定 VC に接続済みの状態にする。別 VC に接続中なら移動する。"""
        guild_id = channel.guild.id
        async with self._locks[guild_id]:
            if self.is_connected_channel(guild_id, channel.id):
                return True
            await self._disconnect(guild_id)
            return await self._connect(channel)

    async def disconnect(self, guild_id: int) -> bool:
        async with self._locks[guild_id]:
            return await self._disconnect(guild_id)

    async def handle_bot_left(self, guild_id: int):
        """キックなど外部要因で切断されたときに管理情報を片付ける。"""
        async with self._locks[guild_id]:
            player = self.players.get(guild_id)
            if player is not None and not player.vc.is_connected():
                await self._disconnect(guild_id)

    async def disconnect_idle(self):
        now = discord.utils.utcnow()
        for guild_id, player in list(self.players.items()):
            if self.repo.get_active_auto_connect(guild_id) and now - player.last_active_at >= IDLE_TIMEOUT:
                await self.disconnect(guild_id)

    async def reconnect_long_lived(self):
        now = discord.utils.utcnow()
        for guild_id, player in list(self.players.items()):
            if now - player.connected_at < RECONNECT_INTERVAL:
                continue

            channel = player.vc.channel
            player.enqueue(RECONNECT_NOTICE, DEFAULT_SPEAKER)
            await player.wait_until_idle(timeout = 15)

            async with self._locks[guild_id]:
                if self.players.get(guild_id) is not player:
                    continue
                await self._disconnect(guild_id)
                if await self._connect(channel):
                    logger.info("VC reconnected: guild=%s channel=%s", guild_id, channel.id)

    async def close_all(self):
        for guild_id in list(self.players):
            await self.disconnect(guild_id)

    async def _connect(self, channel: discord.VoiceChannel) -> bool:
        guild_id = channel.guild.id

        # 管理外の接続が残っていると connect が失敗するため先に片付ける
        stale = channel.guild.voice_client
        if stale is not None:
            await stale.disconnect(force = True)

        try:
            vc = await channel.connect(self_deaf = True)
        except Exception:
            logger.exception("VC connect failed: guild=%s channel=%s", guild_id, channel.id)
            return False

        self.players[guild_id] = AudioPlayer(vc, self.voicevox)
        logger.info(
            "VC connected: guild=%s channel=%s | connected guilds=%d",
            guild_id, channel.id, len(self.players)
        )
        return True

    async def _disconnect(self, guild_id: int) -> bool:
        player = self.players.pop(guild_id, None)
        if player is None:
            return False

        channel_id = player.vc.channel.id if player.vc.channel else None
        await player.close()
        try:
            await player.vc.disconnect(force = True)
        except Exception:
            logger.exception("VC disconnect failed: guild=%s channel=%s", guild_id, channel_id)

        logger.info(
            "VC disconnected: guild=%s channel=%s | connected guilds=%d",
            guild_id, channel_id, len(self.players)
        )
        return True
