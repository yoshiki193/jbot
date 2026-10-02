import asyncio
import logging
from config import Config
from read_bot import ReadBot

logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers = [
        logging.StreamHandler()
    ]
)

async def main():
    config = Config.from_env()
    bot = ReadBot(config)
    async with bot:
        await bot.start(config.token)

if __name__ == "__main__":
    asyncio.run(main())
