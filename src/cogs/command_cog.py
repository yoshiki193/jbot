import discord
from discord.ext import tasks, commands
import logging
import datetime
from repositories.data_repository import DataRepository
from services.counter_message_manager import CounterMessageManager
from services.counter_embed_service import CounterEmbedService
from services.audio_manager import AudioManager
from services.voicevox_service import VoiceVoxService
from services.message_filter_service import  MessageFilterService
from services.fix_message import FixMessage
from autocomplete.select_voicevox_model import SelectVoicevoxModel

logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers = [
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)

DATA_PATH = "/root/opt/data.json"

class Command(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.logger = logger
        self.bot = bot
        self.message_filter = MessageFilterService(self.bot)
        self.repo = DataRepository(DATA_PATH)
        self.counter_embed = CounterEmbedService(self.repo)
        self.counter_message_manager = CounterMessageManager(self.bot, self.repo, self.counter_embed)
        self.voicevox = VoiceVoxService(self.repo)
        self.select_voicevox_model = SelectVoicevoxModel(self.repo)
        self.audio_manager = AudioManager(self.repo, self.voicevox, self.logger)
        self.fix_message = FixMessage(self.repo, self.bot)
        self.reconnect_loop.start()
        self.self_disconnect.start()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.fix_message.filter_fix_msg(message):
            await self.fix_message.update(message)

        if self.counter_message_manager.is_counter_update_message(message):
            await self.counter_message_manager.update(message.channel)

        if self.message_filter.is_playable_message(message):
            if not self.audio_manager.is_connected_channel(message.guild.id, message.channel.id) and self.repo.get_active_auto_connect(message.guild.id):
                if self.audio_manager.get_connected_vc(message.guild.id) is None:
                    success = await self.audio_manager.connect_vc(message.guild.id, message.channel)
                else:
                    success = await self.audio_manager.move_vc(message.guild.id, message.channel)

                if not success:
                    return

            await self.audio_manager.play(
                guild_id = message.guild.id,
                channel_id = message.channel.id,
                content = message.clean_content,
                member_id = message.author.id
            )

    @discord.app_commands.command(
        description = "fix message"
    )
    async def fix_msg(self, interaction: discord.Interaction, content: str):
        await self.fix_message.send_fix_msg(interaction, content)
    
    @discord.app_commands.command(
        description = "debug"
    )
    async def delete_msg(self, interaction: discord.Interaction, msg_id: str):
        msg = await interaction.channel.fetch_message(int(msg_id))
        await msg.delete()
        await interaction.response.send_message(
            "メッセージを削除しました",
            ephemeral=True
        )
    
    @discord.app_commands.command(
        description = "delete fix message"
    )
    async def delete_fix_msg(self, interaction: discord.Interaction):
        await self.fix_message.delete_fix_msg(interaction.guild_id, interaction.channel_id)
        await interaction.response.send_message(
            "固定メッセージを削除しました",
            ephemeral=True
        )

    @discord.app_commands.command(
        description = "add to counter"
    )
    async def add(self, interaction: discord.Interaction, member: discord.Member):
        if interaction.channel_id != self.repo.get_send_channel_id(interaction.guild_id) or interaction.user.id in self.repo.get_ban_users(interaction.guild_id):
            await interaction.response.send_message(
                "このチャンネルではサポートされていません",
                ephemeral=True
            )
            return

        self.counter_message_manager.add(interaction.guild_id, member.id)
        await interaction.response.send_message(
            content=f"updated\t{member.display_name}\t{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    @discord.app_commands.command(
        description = "set auto connect voice channel"
    )
    async def set_auto_connect(self, interaction: discord.Interaction):
        self.repo.set_active_auto_connect(interaction.guild_id, True)
        await interaction.response.send_message(
            f"自動接続機能を有効化しました",
            ephemeral=True
        )

    @discord.app_commands.command(
        description = "reset auto connect voice channel"
    )
    async def reset_auto_connect(self, interaction: discord.Interaction):
        self.repo.set_active_auto_connect(interaction.guild_id, False)
        await interaction.response.send_message(
            "自動接続機能を無効化しました",
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

    async def vv_autocomplete(self, interaction, current):
        return await self.select_voicevox_model.select_model(interaction, current)
    
    async def style_autocomplete(self, interaction, current):
        return await self.select_voicevox_model.select_style(interaction, current)
    
    @discord.app_commands.command(
        description = "change model"
    )
    @discord.app_commands.autocomplete(
        vv = vv_autocomplete,
        style = style_autocomplete
    )
    async def change_model(self, interaction: discord.Interaction, vv: str, style: str):
        self.audio_manager.clear_player(interaction.guild_id, interaction.channel_id)
        speaker = self.select_voicevox_model.convert_speaker_id(vv, style)

        if speaker == -1:
            await interaction.response.send_message(
                "モデル変更に失敗しました",
                ephemeral=True
            )
            return
        
        self.repo.set_voicevox_speaker(interaction.guild_id, speaker, interaction.user.id)
        
        await interaction.response.send_message(
            f"あなたのモデルを{vv}の{style}に変更しました",
            ephemeral=True
        )
    
    @discord.app_commands.command(
        description = "subscribe user dict"
    )
    async def subscribe_user_dict(self, interaction: discord.Interaction, surface: str, pronunciation: str):
        res = self.voicevox.subscribe_user_dict(surface, pronunciation)
        if res:
            embed = {
                "title":"ユーザー辞書登録",
                "description":"以下の単語が登録されました",
                "fields":[{
                    "name":"surface",
                    "value":f"{surface}"
                },{
                    "name":"pronunciation",
                    "value":f"{pronunciation}"
                }]
            }
            await interaction.response.send_message(
                embed = discord.Embed.from_dict(embed)
            )
        else:
            await interaction.response.send_message(
                "登録に失敗しました",
                ephemeral=True
            )

    @tasks.loop(minutes = 1)
    async def self_disconnect(self):
        await self.audio_manager.self_disconnect()

    @tasks.loop(minutes = 10)
    async def reconnect_loop(self):
        await self.audio_manager.update_vc(self.bot)

    @reconnect_loop.before_loop
    async def before_reconnect_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Command(bot))