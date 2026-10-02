import discord
from discord import app_commands
from discord.ext import commands
from read_bot import ReadBot

class AdminCog(commands.Cog):
    """管理者向けのデバッグ用コマンド。"""

    def __init__(self, bot: ReadBot):
        self.bot = bot

    @app_commands.command(description = "debug")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages = True)
    async def delete_msg(self, interaction: discord.Interaction, msg_id: str):
        if not msg_id.isdigit():
            await interaction.response.send_message("メッセージIDが不正です", ephemeral = True)
            return

        try:
            await interaction.channel.get_partial_message(int(msg_id)).delete()
        except discord.NotFound:
            await interaction.response.send_message("メッセージが見つかりません", ephemeral = True)
            return
        except discord.Forbidden:
            await interaction.response.send_message("メッセージを削除する権限がありません", ephemeral = True)
            return

        await interaction.response.send_message("メッセージを削除しました", ephemeral = True)

async def setup(bot: ReadBot):
    await bot.add_cog(AdminCog(bot))
