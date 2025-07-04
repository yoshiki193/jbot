import asyncio
import discord
from discord.ext import commands
import os

INITIAL_EXTENSIONS = [
    "cog",
]

token=os.environ["token"]

intents=discord.Intents.all()
bot=commands.Bot(command_prefix="$",intents=intents)

async def load_extension():
    for cog in INITIAL_EXTENSIONS:
        await bot.load_extension(cog)

async def main():
    async with bot:
        await load_extension()
        await bot.start(token=token)

@bot.event
async def on_ready():
    await bot.tree.sync()

asyncio.run(main())