import discord
from discord.ext import commands
from repositories.data_repository import DataRepository

class FixMessage:
    def __init__(self, repo: DataRepository, bot: commands.Bot):
        self.repo = repo
        self.bot = bot

    async def send_fix_msg(self, interaction: discord.Interaction, content: str):
        embed = discord.Embed(
            title = content,
            color = discord.Color.blue()
        )

        await interaction.response.send_message(embed = embed, silent = True)
        message = await interaction.original_response()

        return message.id

    def filter_fix_msg(self, message: discord.Message):
        if message is None or message.guild is None or message.channel is None:
            return False
        if self.repo.get_fix_msg(message.guild.id, message.channel.id) is None:
            return False
        if message.author == self.bot.user:
            return False
        return True

    def register_fix_msg(self, guild_id: int, channel_id: int, message_id: int):
        self.repo.set_fix_msg(guild_id, channel_id, message_id)
    
    def delete_fix_msg(self, guild_id: int, channel_id: int):
        self.repo.delete_fix_msg(guild_id, channel_id)
    
    async def update(self, message: discord.Message):
        last_id = self.repo.get_fix_msg(message.guild.id, message.channel.id)

        if last_id:
            content = await self._delete_previous(message.channel.id, last_id)

        new_id = await self._send_new(message, content)

        self.register_fix_msg(message.guild.id, message.channel.id, new_id)

    async def _delete_previous(self, channel_id: int, message_id: int):
        channel = await self.bot.fetch_channel(channel_id)
        try:
            msg = await channel.fetch_message(message_id)
            content = msg.embeds[0].title
            await msg.delete()
        except discord.NotFound:
            pass
        
        return content

    async def _send_new(self, message: discord.Message, content):
        embed = discord.Embed(
            title = content,
            color = discord.Color.blue()
        )

        msg = await message.channel.send(embed = embed, silent = True)

        return msg.id