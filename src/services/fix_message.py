import discord
from discord.ext import commands
from repositories.data_repository import DataRepository

class FixMessage:
    def __init__(self, repo: DataRepository, bot: commands.Bot):
        self.repo = repo
        self.bot = bot
    
    def filter_fix_msg(self, message: discord.Message):
        if message is None or message.guild is None or message.channel is None:
            return False
        if self.repo.get_fix_msg(message.guild.id, message.channel.id) is None:
            return False
        if message.author == self.bot.user:
            return False
        return True

    async def send_fix_msg(self, interaction: discord.Interaction, content: str):
        msg_id = self.repo.get_fix_msg(interaction.guild_id, interaction.channel_id)
    
        if msg_id is not None:
            await self.delete_fix_msg(interaction.guild_id, interaction.channel_id)
        
        embed = discord.Embed(
            title = content
        )

        await interaction.response.send_message(embed = embed, silent = True)
        msg = await interaction.original_response()

        self.repo.set_fix_msg(interaction.guild_id, interaction.channel_id, msg.id)
    
    async def delete_fix_msg(self, guild_id: int, channel_id: int):
        msg_id = self.repo.get_fix_msg(guild_id, channel_id)
        await self._delete_previous(channel_id, msg_id)
        self.repo.delete_fix_msg(guild_id, channel_id)
    
    async def update(self, message: discord.Message):
        last_id = self.repo.get_fix_msg(message.guild.id, message.channel.id)

        if last_id:
            content = await self._delete_previous(message.channel.id, last_id)

        new_id = await self._send_new(message, content)

        self.repo.set_fix_msg(message.guild.id, message.channel.id, new_id)

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
            title = content
        )

        msg = await message.channel.send(embed = embed, silent = True)

        return msg.id