import datetime
import discord
from discord import app_commands
from discord.ext import commands
from read_bot import ReadBot
from services.counter_service import CounterService

class CounterCog(commands.Cog):
    """寝落ちカウンター。"""

    def __init__(self, bot: ReadBot):
        self.bot = bot
        self.counter = CounterService(bot, bot.repo)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.counter.should_refresh(message):
            await self.counter.refresh(message.channel)

    @app_commands.command(description = "add to counter")
    @app_commands.guild_only()
    async def add(self, interaction: discord.Interaction, member: discord.Member):
        if not self.counter.can_add(interaction.guild_id, interaction.channel_id, interaction.user.id):
            await interaction.response.send_message("このチャンネルではサポートされていません", ephemeral = True)
            return

        self.counter.add(interaction.guild_id, member.id)
        await interaction.response.send_message(
            content = f"updated\t{member.display_name}\t{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

async def setup(bot: ReadBot):
    await bot.add_cog(CounterCog(bot))
