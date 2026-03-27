import aiohttp
import io
import asyncio
import requests

class VoiceVoxService:
    def __init__(self, max_concurrent=2):
        self.session = aiohttp.ClientSession()
        self.sem = asyncio.Semaphore(max_concurrent)

    async def synthesize(self, text: str, speaker: int, voicevox_url: str):
        async with self.sem:
            async with self.session.post(
                f"{voicevox_url}/audio_query",
                params={"text": text, "speaker": speaker}
            ) as resp:
                resp.raise_for_status()
                query_json = await resp.json()

            async with self.session.post(
                f"{voicevox_url}/synthesis",
                params={"speaker": speaker},
                json=query_json
            ) as resp:
                resp.raise_for_status()
                wav_bytes = await resp.read()

        buffer = io.BytesIO(wav_bytes)
        buffer.seek(0)
        return buffer

    def subscribe_user_dict(self, surface: str, pronunciation: str, voicevox_url: str):
        res = requests.post(
            f"{voicevox_url}/audio_query",
            params={"text": surface, "speaker": 0}
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

        res2 = requests.post(f"{voicevox_url}/user_dict_word", params=payload)

        if res2.status_code == 200:
            return True
        else:
            print(res2.text)
            return False