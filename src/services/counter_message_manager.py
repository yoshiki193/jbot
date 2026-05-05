import discord
from discord.ext import commands
from services.counter_embed_service import CounterEmbedService
from repositories.data_repository import DataRepository

class CounterMessageManager:
    def __init__(self, bot: commands.Bot, repo: DataRepository, counter_embed_service: CounterEmbedService):
        self.bot = bot
        self.repo = repo
        self.counter_embed = counter_embed_service
    
    def add(self, guild_id: int, member_id: int):
        self.repo.set_counter_users(guild_id, member_id, 1)
    
    def is_counter_update_message(self, message: discord.Message):
        if message is None or message.guild is None or message.channel is None:
            return False

        send_channel_id = self.repo.get_send_channel_id(message.guild.id)
        if send_channel_id is None:
            return False

        if (message.author != self.bot.user or "updated" in message.content) and message.channel.id == send_channel_id:
            return True

        return False
    
    async def update(self, channel: discord.TextChannel):
        last_id = self.repo.get_last_message_id(channel.guild.id)

        if last_id:
            await self._delete_previous(self.repo.get_send_channel_id(channel.guild.id), last_id)

        new_id = await self._send_new(channel)
        self.repo.set_last_message_id(channel.guild.id, new_id)

    async def _delete_previous(self, channel_id: int, message_id: int):
        channel = await self.bot.fetch_channel(channel_id)
        try:
            msg = await channel.fetch_message(message_id)
            await msg.delete()
        except discord.NotFound:
            pass

    async def _send_new(self, channel: discord.TextChannel):
        embed = await self.counter_embed.generate_embed(channel.guild.id, self.bot)
        msg = await channel.send(
            embed=discord.Embed.from_dict(embed),
            silent=True
        )
        return msg.id