import aiohttp
import io

class VoiceVoxService:
    async def synthesize(self, text: str, speaker: int, voicevox_url: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{voicevox_url}/audio_query",
                params = {"text": text, "speaker": speaker}
            ) as resp:
                resp.raise_for_status()
                query_json = await resp.json()

            async with session.post(
                f"{voicevox_url}/synthesis",
                params = {"speaker": speaker},
                json = query_json
            ) as resp:
                resp.raise_for_status()
                wav_bytes = await resp.read()

        buffer = io.BytesIO(wav_bytes)
        buffer.seek(0)
        return buffer