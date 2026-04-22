import aiohttp
import io
import requests
from repositories.data_repository import DataRepository

class VoiceVoxService:
    def __init__(self, repo: DataRepository):
        self.session = aiohttp.ClientSession()
        self.repo = repo

    async def synthesize(self, text: str, speaker: int):
        async with self.session.post(
            f"{self.repo.get_voicevox_url()}/audio_query",
            params = {"text": text, "speaker": speaker}
        ) as resp:
            resp.raise_for_status()
            query_json = await resp.json()

        async with self.session.post(
            f"{self.repo.get_voicevox_url()}/synthesis",
            params = {"speaker": speaker},
            json = query_json
        ) as resp:
            resp.raise_for_status()
            wav_bytes = await resp.read()

        buffer = io.BytesIO(wav_bytes)
        buffer.seek(0)
        return buffer

    def subscribe_user_dict(self, surface: str, pronunciation: str):
        res = requests.post(
            f"{self.repo.get_voicevox_url()}/audio_query",
            params = {"text": surface, "speaker": 0}
        )

        if res.status_code != 200:
            return False

        query = res.json()

        accent_type = query["accent_phrases"][0]["accent"]

        payload = {
            "surface": surface,
            "pronunciation": pronunciation,
            "accent_type": accent_type
        }

        res = requests.post(f"{self.repo.get_voicevox_url()}/user_dict_word", params = payload)

        if res.status_code == 200:
            return True
        else:
            print(res.text)
            return False