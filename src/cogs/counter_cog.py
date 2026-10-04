import datetime
import discord
from discord import app_commands
from discord.ext import commands
from read_bot import ReadBot
from repositories.data_repository import CounterSettings

class CounterCog(commands.Cog):
    """チャンネルごとのカウンター。"""

    def __init__(self, bot: ReadBot):
        self.bot = bot
        self.counter = bot.counter

    @app_commands.command(description = "add to counter")
    @app_commands.guild_only()
    async def add(self, interaction: discord.Interaction, member: discord.Member):
        if not self.counter.can_add(interaction.guild_id, interaction.channel_id, interaction.user.id):
            await interaction.response.send_message("このチャンネルではサポートされていません", ephemeral = True)
            return

        self.counter.add(interaction.guild_id, interaction.channel_id, member.id)
        await interaction.response.send_message(
            content = f"updated\t{member.display_name}\t{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    @app_commands.command(description = "set counter channel")
    @app_commands.guild_only()
    @app_commands.describe(
        title = "カウンターのタイトル",
        multiplier = "合計欄に表示する値の倍率（合計カウント × この値）",
        total_title = "合計欄のタイトル"
    )
    async def set_counter_channel(
        self,
        interaction: discord.Interaction,
        title: app_commands.Range[str, 1, 100],
        multiplier: app_commands.Range[int, 1, 1000000],
        total_title: app_commands.Range[str, 1, 100]
    ):
        await interaction.response.defer(ephemeral = True, thinking = True)
        try:
            await self.bot.sticky.set_counter(interaction.channel, CounterSettings(title, multiplier, total_title))
        except discord.Forbidden:
            await interaction.followup.send("このチャンネルにメッセージを送信する権限がありません", ephemeral = True)
            return

        await interaction.followup.send(f"このチャンネルを「{title}」のカウンターに設定しました", ephemeral = True)

    @app_commands.command(description = "reset counter channel")
    @app_commands.guild_only()
    async def reset_counter_channel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral = True, thinking = True)
        removed = await self.counter.unset_channel(interaction.channel)
        await interaction.followup.send(
            "このチャンネルのカウンターを解除しました" if removed else "このチャンネルにカウンターは設定されていません",
            ephemeral = True
        )

async def setup(bot: ReadBot):
    await bot.add_cog(CounterCog(bot))
