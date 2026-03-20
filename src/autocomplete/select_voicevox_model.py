import discord
import requests


async def select_model(
        interaction: discord.Interaction,
        current: str,
    ):
        vvs = ['四国めたん', 'ずんだもん', '春日部つむぎ', '冥鳴ひまり', 'ナースロボ＿タイプＴ', '中国うさぎ', '東北ずん子', '東北きりたん']
        return [
            discord.app_commands.Choice(name=vv, value=vv)
            for vv in vvs if current.lower() in vv.lower()
        ]

async def select_style(
        interaction: discord.Interaction,
        current: str,
    ):
        vv = interaction.namespace.vv
        cog = interaction.client.get_cog("Command")
        styles = []
        response = requests.get(f"{cog.voicevox_url}/speakers")
        data = response.json()

        for speaker in data:
            if speaker["name"] == vv:
                for style in speaker["styles"]:
                    styles.append(style["name"])

        return [
            discord.app_commands.Choice(name=style, value=style)
            for style in styles if current.lower() in style.lower()
        ]

def convert_speaker_id(vv: str, style: str, voicevox_url):
        response = requests.get(f"{voicevox_url}/speakers")
        data = response.json()

        for speaker in data:
            if speaker["name"] == vv:
                for styles in speaker["styles"]:
                    if styles["name"] == style:
                        print(styles["id"])
                        return styles["id"]
        
        return 0

