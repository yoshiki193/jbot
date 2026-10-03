import asyncio
import logging
import math
from collections import defaultdict
import discord
from discord.ext import commands
from repositories.data_repository import CounterSettings, DataRepository

logger = logging.getLogger(__name__)

BAR_WIDTH = 10

class CounterService:
    """寝落ちカウンターの集計と、集計 Embed の再投稿を行う。"""

    def __init__(self, bot: commands.Bot, repo: DataRepository):
        self.bot = bot
        self.repo = repo
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def set_channel(self, channel: discord.abc.Messageable, settings: CounterSettings):
        """カウンターの送信先チャンネルと表示設定を保存し、集計 Embed を投稿する。"""
        guild_id = channel.guild.id
        async with self._locks[guild_id]:
            old_channel_id = self.repo.get_send_channel_id(guild_id)
            old_message_id = self.repo.get_last_message_id(guild_id)

            # 送信に失敗した場合（権限不足など）は設定を変更しない
            msg = await channel.send(embed = await self.build_embed(guild_id, settings), silent = True)
            await self._delete_previous(old_channel_id, old_message_id)

            self.repo.set_counter_settings(guild_id, settings)
            self.repo.set_send_channel_id(guild_id, channel.id)
            self.repo.set_last_message_id(guild_id, msg.id)

    async def unset_channel(self, guild_id: int) -> bool:
        """カウンターの送信先チャンネルを解除する。集計値は保持する。"""
        async with self._locks[guild_id]:
            channel_id = self.repo.get_send_channel_id(guild_id)
            if not channel_id:
                return False

            await self._delete_previous(channel_id, self.repo.get_last_message_id(guild_id))
            self.repo.set_send_channel_id(guild_id, 0)
            self.repo.set_last_message_id(guild_id, 0)
            return True

    async def _delete_previous(self, channel_id: int, message_id: int):
        if not channel_id or not message_id:
            return
        channel = self.bot.get_channel(channel_id)
        if channel is not None:
            await self._delete_message(channel, message_id)

    def can_add(self, guild_id: int, channel_id: int, user_id: int) -> bool:
        send_channel_id = self.repo.get_send_channel_id(guild_id)
        return bool(send_channel_id) and channel_id == send_channel_id and user_id not in self.repo.get_ban_users(guild_id)

    def add(self, guild_id: int, member_id: int):
        self.repo.set_counter_users(guild_id, member_id, 1)

    def should_refresh(self, message: discord.Message) -> bool:
        if message.guild is None:
            return False

        send_channel_id = self.repo.get_send_channel_id(message.guild.id)
        if not send_channel_id or message.channel.id != send_channel_id:
            return False

        # 人の発言、または /add の応答（"updated"）で Embed を最下部に出し直す
        return message.author != self.bot.user or "updated" in message.content

    async def refresh(self, channel: discord.TextChannel):
        guild_id = channel.guild.id
        async with self._locks[guild_id]:
            last_id = self.repo.get_last_message_id(guild_id)
            if last_id:
                await self._delete_message(channel, last_id)

            msg = await channel.send(embed = await self.build_embed(guild_id), silent = True)
            self.repo.set_last_message_id(guild_id, msg.id)

    async def build_embed(self, guild_id: int, settings: CounterSettings | None = None) -> discord.Embed:
        settings = settings or self.repo.get_counter_settings(guild_id)
        users = self.repo.get_counter_users(guild_id)
        top = max(users.values(), default = 0)
        embed = discord.Embed(title = f"**{settings.title}**", description = "コマンド：/add")

        for user_id, count in users.items():
            name = await self._display_name(user_id)
            embed.add_field(
                name = f"__{name}\t{count}\t#1__" if count == top else f"{name}\t{count}",
                value = "█" * math.ceil(count / top * BAR_WIDTH) if top > 0 else "-",
                inline = False
            )

        embed.add_field(name = " ", value = "─" * BAR_WIDTH, inline = False)
        embed.add_field(
            name = settings.total_title,
            value = f"```{sum(users.values()) * settings.multiplier}```",
            inline = False
        )
        return embed

    async def _display_name(self, user_id: int) -> str:
        user = self.bot.get_user(user_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                return str(user_id)
        return user.display_name

    async def _delete_message(self, channel: discord.TextChannel, message_id: int):
        try:
            await channel.get_partial_message(message_id).delete()
        except discord.NotFound:
            pass
        except discord.HTTPException:
            logger.exception("failed to delete counter message: channel=%s message=%s", channel.id, message_id)
