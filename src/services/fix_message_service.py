import asyncio
import logging
from collections import defaultdict
import discord
from discord.ext import commands
from repositories.data_repository import DataRepository

logger = logging.getLogger(__name__)

class FixMessageService:
    """チャンネル最下部に Embed を貼り直し続ける固定メッセージ機能。"""

    def __init__(self, bot: commands.Bot, repo: DataRepository):
        self.bot = bot
        self.repo = repo
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    def should_repost(self, message: discord.Message) -> bool:
        if message.guild is None or message.author == self.bot.user:
            return False
        return self.repo.get_fix_msg(message.guild.id, message.channel.id) is not None

    async def set(self, channel: discord.abc.Messageable, content: str):
        async with self._locks[channel.id]:
            current = self.repo.get_fix_msg(channel.guild.id, channel.id)
            if current is not None:
                await self._delete_message(channel, current.message_id)
            await self._send(channel, content)

    async def remove(self, channel: discord.abc.Messageable) -> bool:
        async with self._locks[channel.id]:
            current = self.repo.get_fix_msg(channel.guild.id, channel.id)
            if current is None:
                return False
            await self._delete_message(channel, current.message_id)
            self.repo.delete_fix_msg(channel.guild.id, channel.id)
            return True

    async def repost(self, channel: discord.abc.Messageable):
        async with self._locks[channel.id]:
            current = self.repo.get_fix_msg(channel.guild.id, channel.id)
            if current is None:
                return

            content = current.content or await self._fetch_title(channel, current.message_id)
            if content is None:
                logger.warning("fix message content lost, unregistering: channel=%s", channel.id)
                self.repo.delete_fix_msg(channel.guild.id, channel.id)
                return

            await self._delete_message(channel, current.message_id)
            await self._send(channel, content)

    async def _send(self, channel: discord.abc.Messageable, content: str):
        msg = await channel.send(embed = discord.Embed(title = content), silent = True)
        self.repo.set_fix_msg(channel.guild.id, channel.id, msg.id, content)

    async def _fetch_title(self, channel: discord.abc.Messageable, message_id: int) -> str | None:
        # content 列追加前に登録されたメッセージは、元メッセージのタイトルから復元する
        try:
            msg = await channel.fetch_message(message_id)
        except discord.HTTPException:
            return None
        return msg.embeds[0].title if msg.embeds else None

    async def _delete_message(self, channel: discord.abc.Messageable, message_id: int):
        try:
            await channel.get_partial_message(message_id).delete()
        except discord.NotFound:
            pass
        except discord.HTTPException:
            logger.exception("failed to delete fix message: channel=%s message=%s", channel.id, message_id)
