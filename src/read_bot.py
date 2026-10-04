import discord
from discord.ext import commands
from config import Config
from repositories.data_repository import DataRepository
from services.counter_service import CounterService
from services.fix_message_service import FixMessageService
from services.sticky_service import StickyService
from services.voicevox_service import VoiceVoxService

INITIAL_EXTENSIONS = [
    "cogs.voice_cog",
    "cogs.counter_cog",
    "cogs.fix_message_cog",
    "cogs.sticky_cog",
]

class ReadBot(commands.Bot):
    """共有リソース（DB・VOICEVOX クライアント・各サービス）を保持する Bot 本体。"""

    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix = "$", intents = intents)
        self.config = config
        self.repo = DataRepository(config.db_path)
        self.voicevox = VoiceVoxService(config.voicevox_url)
        self.counter = CounterService(self, self.repo)
        self.fix_message = FixMessageService(self, self.repo)
        self.sticky = StickyService(self.counter, self.fix_message)

    async def setup_hook(self):
        await self.voicevox.start()
        for extension in INITIAL_EXTENSIONS:
            await self.load_extension(extension)
        # on_ready は再接続のたびに呼ばれるため、コマンド同期は起動時に一度だけ行う
        await self.tree.sync()

    async def close(self):
        await super().close()
        await self.voicevox.close()
        self.repo.close()
