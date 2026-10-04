import discord
from discord.ext import commands
from read_bot import ReadBot

class StickyCog(commands.Cog):
    """発言のたびに、カウンターと固定メッセージをチャンネル最下部へ貼り直す。"""

    def __init__(self, bot: ReadBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.bot.sticky.handle_message(message)

async def setup(bot: ReadBot):
    await bot.add_cog(StickyCog(bot))
