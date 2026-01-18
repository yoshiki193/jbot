import aiohttp
import io

VOICEVOX_URL = "http://192.168.0.71:50021"

class VoiceVoxService:
    async def synthesize(self, text: str, speaker: int):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{VOICEVOX_URL}/audio_query",
                params = {"text": text, "speaker": speaker}
            ) as resp:
                resp.raise_for_status()
                query_json = await resp.json()

            async with session.post(
                f"{VOICEVOX_URL}/synthesis",
                params = {"speaker": speaker},
                json = query_json
            ) as resp:
                resp.raise_for_status()
                wav_bytes = await resp.read()

        buffer = io.BytesIO(wav_bytes)
        buffer.seek(0)
        return buffer