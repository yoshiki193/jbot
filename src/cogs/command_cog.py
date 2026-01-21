import discord
from discord.ext import tasks, commands
import logging
import datetime
from repositories.data_repository import DataRepository
from services.counter_message_manager import CounterMessageManager
from services.counter_embed_service import CounterEmbedService
from services.audio_manager import AudioManager
from services.counter_service import CounterService
from services.voicevox_service import VoiceVoxService
from services.message_filter_service import  MessageFilterService
from ui.model_select import ModelSelectView

logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers = [
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)

class Command(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.logger = logger
        self.bot = bot
        self.message_filter = MessageFilterService(self.bot.user)
        self.repo = DataRepository()
        self.audio_manager = AudioManager(self.logger)
        self.counter = CounterService(self.repo)
        self.counter_embed = CounterEmbedService(self.counter)
        self.counter_message_manager = CounterMessageManager(self.bot, self.counter, self.counter_embed)
        self.voicevox = VoiceVoxService()
        self.reconnect_loop.start()
        self.self_disconnect.start()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.counter.is_counter_update_message(message, self.bot.user):
            await self.counter_message_manager.update(message.channel)

        if self.message_filter.is_playable_message(message):
            if self.audio_manager.is_connected_channel(message.guild.id, message.channel.id):
                buffer = await self.voicevox.synthesize(
                    message.content,
                    self.repo.get_voicevox_speaker(str(message.guild.id))
                )
                await self.audio_manager.play(
                    message.guild.id,
                    message.channel.id,
                    buffer
                )
            elif self.repo.get_active_auto_connect(str(message.guild.id)) == message.channel.id:
                existing_vc = self.audio_manager.get_connected_vc(message.guild.id)

                if existing_vc:
                    if existing_vc.channel.id == message.guild.id:
                        return
                    else:
                        return

                success = await self.audio_manager.connect_vc(message.guild.id, message.channel)

                if not success:
                    return
                
                buffer = await self.voicevox.synthesize(
                    message.content,
                    self.repo.get_voicevox_speaker(str(message.guild.id))
                )
                await self.audio_manager.play(
                    message.guild.id,
                    message.channel.id,
                    buffer
                )
                


    @discord.app_commands.command(
        description = "add to counter"
    )
    async def add(self,interaction: discord.Interaction,member: discord.Member):
        if interaction.channel_id != self.counter.get_send_channel_id(str(interaction.guild_id)):
            await interaction.response.send_message(
                "このチャンネルではサポートされていません",
                ephemeral=True
            )
            return

        self.counter.add(str(member.id), str(interaction.guild_id))
        await interaction.response.send_message(
            content=f"updated\t{member.display_name}\t{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    @discord.app_commands.command(
        description = "set auto connect voice channel"
    )
    @discord.app_commands.describe(
        channel="セットするボイスチャンネル"
    )
    async def set_auto_connect(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        self.repo.set_active_auto_connect(str(interaction.guild_id), channel.id)
        await interaction.response.send_message(
            f"自動接続ボイスチャンネル`{channel.name}`をセットしました",
            ephemeral=True
        )

    @discord.app_commands.command(
        description = "reset auto connect voice channel"
    )
    async def reset_auto_connect(self, interaction: discord.Interaction):
        channel_id = self.repo.get_active_auto_connect(str(interaction.guild_id))
        if channel_id != 0:
            if self.audio_manager.is_connected_channel(interaction.guild_id, channel_id):
                await self.audio_manager.disconnect_vc(interaction.guild_id, channel_id)
        self.repo.set_active_auto_connect(str(interaction.guild_id), 0)
        await interaction.response.send_message(
            "自動接続ボイスチャンネルをリセットしました",
            ephemeral=True
        )

    @discord.app_commands.command(
        description = "connect VV"
    )
    async def connect_vv(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.VoiceChannel):
            await interaction.response.send_message(
                "VCで実行してください",
                ephemeral=True
            )
            return

        existing_vc = self.audio_manager.get_connected_vc(interaction.guild_id)

        if existing_vc:
            if existing_vc.channel.id == interaction.channel_id:
                await interaction.response.send_message(
                    "すでにこのVCに接続しています",
                    ephemeral=True
                )
                return
            else:
                await interaction.response.send_message(
                    "すでに別のVCに接続しています。先に切断してください。",
                    ephemeral=True
                )
                return

        success = await self.audio_manager.connect_vc(interaction.guild_id, interaction.channel)

        if not success:
            await interaction.response.send_message(
                "接続に失敗しました",
                ephemeral=True
            )
            return
        await interaction.response.send_message(
            "接続しました",
            ephemeral=True
        )

    @discord.app_commands.command(
        description = "disconnect VV"
    )
    async def disconnect_vv(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.VoiceChannel):
            await interaction.response.send_message(
                "VCで実行してください",
                ephemeral=True
            )
            return
        
        guild_id = interaction.guild_id
        channel_id = interaction.channel_id
        
        existing_vc = self.audio_manager.get_connected_vc(guild_id)

        if not existing_vc:
            await interaction.response.send_message(
                "現在どのボイスチャンネルにも接続していません",
                ephemeral=True
            )
            return

        if existing_vc.channel.id != channel_id:
            await interaction.response.send_message(
                f"現在は `{existing_vc.channel.name}` に接続しています",
                ephemeral=True
            )
            return
        
        success = await self.audio_manager.disconnect_vc(guild_id, channel_id)

        if success:
            await interaction.response.send_message(
                "切断しました",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "切断に失敗しました",
                ephemeral=True
            )
    
    @discord.app_commands.command(
        description = "change model"
    )
    async def change_model(self, interaction: discord.Interaction):
        if not self.audio_manager.is_connected_channel(interaction.guild_id, interaction.channel_id):
            await interaction.response.send_message(
                "このチャンネルではサポートされていません",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            "",
            view=ModelSelectView(self.repo)
        )

    @tasks.loop(minutes=10)
    async def reconnect_loop(self):
        await self.audio_manager.update_vc(self.bot, self.voicevox)

    @tasks.loop(minutes=5)
    async def self_disconnect(self):
        await self.audio_manager.self_disconnect(self.repo)

    @reconnect_loop.before_loop
    async def before_reconnect_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Command(bot))