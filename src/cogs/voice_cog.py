import logging
import discord
from discord import app_commands
from discord.ext import tasks, commands
from read_bot import ReadBot
from services.audio_manager import AudioManager, has_listeners
from services.message_filter import is_readable_message
from autocomplete.select_voicevox_model import SelectVoicevoxModel

logger = logging.getLogger(__name__)

class VoiceCog(commands.Cog):
    """VC テキストチャットの読み上げと VC 接続管理。"""

    def __init__(self, bot: ReadBot):
        self.bot = bot
        self.repo = bot.repo
        self.voicevox = bot.voicevox
        self.audio = AudioManager(self.repo, self.voicevox)
        self.select_voicevox_model = SelectVoicevoxModel(self.voicevox)

    async def cog_load(self):
        self.reconnect_loop.start()
        self.idle_disconnect_loop.start()

    async def cog_unload(self):
        self.reconnect_loop.cancel()
        self.idle_disconnect_loop.cancel()
        await self.audio.close_all()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not is_readable_message(message, self.bot.user):
            return

        guild_id = message.guild.id
        if not self.audio.is_connected_channel(guild_id, message.channel.id):
            if not self._can_auto_connect(message):
                return
            if not await self.audio.ensure_connected(message.channel):
                return

        self.audio.speak(guild_id, message.clean_content, message.author.id)

    def _can_auto_connect(self, message: discord.Message) -> bool:
        if not self.repo.get_active_auto_connect(message.guild.id):
            return False

        # 発言者がその VC に参加していること
        voice = getattr(message.author, "voice", None)
        if voice is None or voice.channel is None or voice.channel.id != message.channel.id:
            return False

        # 別 VC で聞いている人がいる間は移動しない（読み上げの横取り防止）
        current = self.audio.get_vc(message.guild.id)
        return current is None or not has_listeners(current.channel)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild_id = member.guild.id

        if self.bot.user is not None and member.id == self.bot.user.id:
            if after.channel is None:
                await self.audio.handle_bot_left(guild_id)
            return

        vc = self.audio.get_vc(guild_id)
        if vc is None or before.channel is None or before.channel.id != vc.channel.id:
            return
        if after.channel is not None and after.channel.id == before.channel.id:
            return
        if not has_listeners(vc.channel):
            await self.audio.disconnect(guild_id)

    @app_commands.command(description = "set auto connect voice channel")
    @app_commands.guild_only()
    async def set_auto_connect(self, interaction: discord.Interaction):
        self.repo.set_active_auto_connect(interaction.guild_id, True)
        await interaction.response.send_message("自動接続機能を有効化しました", ephemeral = True)

    @app_commands.command(description = "reset auto connect voice channel")
    @app_commands.guild_only()
    async def reset_auto_connect(self, interaction: discord.Interaction):
        self.repo.set_active_auto_connect(interaction.guild_id, False)
        await interaction.response.send_message("自動接続機能を無効化しました", ephemeral = True)

    @app_commands.command(description = "connect VV")
    @app_commands.guild_only()
    async def connect_vv(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.VoiceChannel):
            await interaction.response.send_message("VCで実行してください", ephemeral = True)
            return

        existing_vc = self.audio.get_vc(interaction.guild_id)
        if existing_vc is not None:
            if existing_vc.channel.id == interaction.channel_id:
                await interaction.response.send_message("すでにこのVCに接続しています", ephemeral = True)
            else:
                await interaction.response.send_message("すでに別のVCに接続しています。先に切断してください。", ephemeral = True)
            return

        # VC 接続は 3 秒を超えることがあるため先に応答を保留する
        await interaction.response.defer(ephemeral = True, thinking = True)
        success = await self.audio.connect(interaction.channel)
        await interaction.followup.send("接続しました" if success else "接続に失敗しました", ephemeral = True)

    @app_commands.command(description = "disconnect VV")
    @app_commands.guild_only()
    async def disconnect_vv(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.VoiceChannel):
            await interaction.response.send_message("VCで実行してください", ephemeral = True)
            return

        existing_vc = self.audio.get_vc(interaction.guild_id)
        if existing_vc is None:
            await interaction.response.send_message("現在どのボイスチャンネルにも接続していません", ephemeral = True)
            return
        if existing_vc.channel.id != interaction.channel_id:
            await interaction.response.send_message(f"現在は `{existing_vc.channel.name}` に接続しています", ephemeral = True)
            return

        await interaction.response.defer(ephemeral = True, thinking = True)
        success = await self.audio.disconnect(interaction.guild_id)
        await interaction.followup.send("切断しました" if success else "切断に失敗しました", ephemeral = True)

    async def vv_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.select_voicevox_model.select_model(interaction, current)

    async def style_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.select_voicevox_model.select_style(interaction, current)

    @app_commands.command(description = "change model")
    @app_commands.guild_only()
    @app_commands.autocomplete(vv = vv_autocomplete, style = style_autocomplete)
    async def change_model(self, interaction: discord.Interaction, vv: str, style: str):
        await interaction.response.defer(ephemeral = True, thinking = True)
        try:
            speaker = await self.voicevox.find_style_id(vv, style)
        except Exception:
            logger.exception("failed to resolve speaker: vv=%s style=%s", vv, style)
            speaker = None

        if speaker is None:
            await interaction.followup.send("モデル変更に失敗しました", ephemeral = True)
            return

        self.repo.set_voicevox_speaker(interaction.guild_id, speaker, interaction.user.id)
        await interaction.followup.send(f"あなたのモデルを{vv}の{style}に変更しました", ephemeral = True)

    @app_commands.command(description = "subscribe user dict")
    async def subscribe_user_dict(self, interaction: discord.Interaction, surface: str, pronunciation: str):
        await interaction.response.defer(thinking = True)
        if not await self.voicevox.add_user_dict_word(surface, pronunciation):
            await interaction.followup.send("登録に失敗しました")
            return

        embed = discord.Embed(title = "ユーザー辞書登録", description = "以下の単語が登録されました")
        embed.add_field(name = "surface", value = surface, inline = False)
        embed.add_field(name = "pronunciation", value = pronunciation, inline = False)
        await interaction.followup.send(embed = embed)

    # tasks.loop は未処理例外でループ自体が停止するため、本体で例外を握って継続させる
    @tasks.loop(minutes = 1)
    async def idle_disconnect_loop(self):
        try:
            await self.audio.disconnect_idle()
        except Exception:
            logger.exception("idle disconnect failed")

    @tasks.loop(minutes = 10)
    async def reconnect_loop(self):
        try:
            await self.audio.reconnect_long_lived()
        except Exception:
            logger.exception("reconnect failed")

    @idle_disconnect_loop.before_loop
    @reconnect_loop.before_loop
    async def before_loops(self):
        await self.bot.wait_until_ready()

async def setup(bot: ReadBot):
    await bot.add_cog(VoiceCog(bot))
