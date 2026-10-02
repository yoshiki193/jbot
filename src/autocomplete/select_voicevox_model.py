import logging
import discord
from services.voicevox_service import VoiceVoxService

logger = logging.getLogger(__name__)

MODEL_NAMES = ['四国めたん', 'ずんだもん', '春日部つむぎ', '冥鳴ひまり', 'ナースロボ＿タイプＴ', '中国うさぎ', '東北ずん子', '東北きりたん']
MAX_CHOICES = 25

def _to_choices(names: list[str], current: str) -> list[discord.app_commands.Choice[str]]:
    current = current.lower()
    return [
        discord.app_commands.Choice(name = name, value = name)
        for name in names if current in name.lower()
    ][:MAX_CHOICES]

class SelectVoicevoxModel:
    def __init__(self, voicevox: VoiceVoxService):
        self.voicevox = voicevox

    async def select_model(self, interaction: discord.Interaction, current: str):
        return _to_choices(MODEL_NAMES, current)

    async def select_style(self, interaction: discord.Interaction, current: str):
        vv = getattr(interaction.namespace, "vv", None)
        if not vv:
            return []
        try:
            styles = await self.voicevox.get_style_names(vv)
        except Exception:
            logger.exception("failed to fetch styles: vv=%s", vv)
            return []
        return _to_choices(styles, current)
