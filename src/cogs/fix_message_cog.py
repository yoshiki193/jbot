import discord
from discord import app_commands
from discord.ext import commands
from read_bot import ReadBot

class FixMessageCog(commands.Cog):
    """チャンネル最下部への固定メッセージ。"""

    def __init__(self, bot: ReadBot):
        self.bot = bot
        self.fix_message = bot.fix_message

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
