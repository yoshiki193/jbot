import asyncio
import logging
from collections import defaultdict
import discord
from repositories.data_repository import CounterSettings
from services.counter_service import CounterService
from services.fix_message_service import FixMessageService

logger = logging.getLogger(__name__)

class StickyService:
    """同じチャンネルにあるカウンターと固定メッセージの貼り直し順をそろえる。

    並びは常に「カウンター → 固定メッセージ（最下部）」にする。
    """

    def __init__(self, counter: CounterService, fix_message: FixMessageService):
        self.counter = counter
        self.fix_message = fix_message
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def handle_message(self, message: discord.Message):
        refresh_counter = self.counter.should_refresh(message)
        # カウンターを出し直すと固定メッセージより下に来るため、固定メッセージも貼り直す
        repost_fix = self.fix_message.should_repost(message) or (
            refresh_counter and self.fix_message.exists(message.channel)
        )
        if not refresh_counter and not repost_fix:
            return

        async with self._locks[message.channel.id]:
            if refresh_counter:
                try:
                    await self.counter.refresh(message.channel)
                except discord.HTTPException:
                    logger.exception("failed to refresh counter: channel=%s", message.channel.id)
            if repost_fix:
                await self.fix_message.repost(message.channel)

    async def set_counter(self, channel: discord.abc.Messageable, settings: CounterSettings):
        async with self._locks[channel.id]:
            await self.counter.set_channel(channel, settings)
            await self.fix_message.repost(channel)
