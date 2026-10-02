import discord
from discord import app_commands
from discord.ext import commands
from read_bot import ReadBot
from services.fix_message_service import FixMessageService

class FixMessageCog(commands.Cog):
    """チャンネル最下部への固定メッセージ。"""

    def __init__(self, bot: ReadBot):
        self.bot = bot
        self.fix_message = FixMessageService(bot, bot.repo)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.fix_message.should_repost(message):
            await self.fix_message.repost(message.channel)

    @app_commands.command(description = "fix message")
    @app_commands.guild_only()
    async def fix_msg(self, interaction: discord.Interaction, content: app_commands.Range[str, 1, 256]):
        await interaction.response.defer(ephemeral = True, thinking = True)
        await self.fix_message.set(interaction.channel, content)
        await interaction.followup.send("固定メッセージを設定しました", ephemeral = True)

    @app_commands.command(description = "delete fix message")
    @app_commands.guild_only()
    async def delete_fix_msg(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral = True, thinking = True)
        removed = await self.fix_message.remove(interaction.channel)
        await interaction.followup.send(
            "固定メッセージを削除しました" if removed else "このチャンネルに固定メッセージはありません",
            ephemeral = True
        )

async def setup(bot: ReadBot):
    await bot.add_cog(FixMessageCog(bot))
