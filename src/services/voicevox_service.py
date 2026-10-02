import asyncio
import logging
import time
import aiohttp

logger = logging.getLogger(__name__)

class VoiceVoxService:
    SPEAKERS_CACHE_TTL = 600

    def __init__(self, base_url: str, timeout: float = 30):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total = timeout)
        self.session: aiohttp.ClientSession | None = None
        self._speakers: list[dict] | None = None
        self._speakers_fetched_at = 0.0

    async def start(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout = self.timeout)

    async def close(self):
        if self.session is not None:
            await self.session.close()
            self.session = None

    async def _audio_query(self, text: str, speaker: int) -> dict:
        async with self.session.post(
            f"{self.base_url}/audio_query",
            params = {"text": text, "speaker": speaker}
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def synthesize(self, text: str, speaker: int) -> bytes:
        query = await self._audio_query(text, speaker)
        async with self.session.post(
            f"{self.base_url}/synthesis",
            params = {"speaker": speaker},
            json = query
        ) as resp:
            resp.raise_for_status()
            return await resp.read()

    async def get_speakers(self) -> list[dict]:
        now = time.monotonic()
        if self._speakers is None or now - self._speakers_fetched_at > self.SPEAKERS_CACHE_TTL:
            async with self.session.get(f"{self.base_url}/speakers") as resp:
                resp.raise_for_status()
                self._speakers = await resp.json()
            self._speakers_fetched_at = now
        return self._speakers

    async def get_style_names(self, speaker_name: str) -> list[str]:
        for speaker in await self.get_speakers():
            if speaker["name"] == speaker_name:
                return [style["name"] for style in speaker["styles"]]
        return []

    async def find_style_id(self, speaker_name: str, style_name: str) -> int | None:
        for speaker in await self.get_speakers():
            if speaker["name"] == speaker_name:
                for style in speaker["styles"]:
                    if style["name"] == style_name:
                        return style["id"]
        return None

    async def add_user_dict_word(self, surface: str, pronunciation: str) -> bool:
        try:
            query = await self._audio_query(surface, 0)
            accent_phrases = query.get("accent_phrases") or []
            if not accent_phrases:
                return False

            payload = {
                "surface": surface,
                "pronunciation": pronunciation,
                "accent_type": accent_phrases[0]["accent"]
            }
            async with self.session.post(f"{self.base_url}/user_dict_word", params = payload) as resp:
                if resp.status != 200:
                    logger.warning("user dict registration failed: status=%s body=%s", resp.status, await resp.text())
                    return False
            return True
        except (aiohttp.ClientError, asyncio.TimeoutError):
            logger.exception("user dict registration failed: surface=%s", surface)
            return False
