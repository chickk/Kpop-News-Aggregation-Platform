import asyncio
import json
import os
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class WikidataClient:
    API_URL = "https://www.wikidata.org/w/api.php"
    _request_lock = asyncio.Lock()
    _last_request_at = 0.0

    def __init__(
        self,
        *,
        user_agent: str | None = None,
        timeout_seconds: float | None = None,
        min_interval_seconds: float | None = None,
        max_retries: int | None = None,
    ):
        self.user_agent = user_agent or os.getenv(
            "WIKIMEDIA_USER_AGENT",
            "IdolTracker/0.1 (local development)",
        )
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else float(os.getenv("WIKI_REQUEST_TIMEOUT_SECONDS", "4"))
        )
        self.min_interval_seconds = (
            min_interval_seconds
            if min_interval_seconds is not None
            else float(os.getenv("WIKI_REQUEST_MIN_INTERVAL_SECONDS", "0.5"))
        )
        self.max_retries = (
            max_retries
            if max_retries is not None
            else int(os.getenv("WIKI_REQUEST_MAX_RETRIES", "3"))
        )

    async def search_entities(
        self,
        query: str,
        *,
        language: str = "en",
        limit: int = 5,
    ) -> list[dict]:
        payload = await self._get_json(
            {
                "action": "wbsearchentities",
                "search": query,
                "language": language,
                "uselang": language,
                "type": "item",
                "limit": str(limit),
                "format": "json",
            }
        )
        return payload.get("search", [])

    async def get_entities(
        self,
        ids: list[str],
        *,
        languages: str = "en|ko|zh",
    ) -> dict[str, dict]:
        if not ids:
            return {}
        payload = await self._get_json(
            {
                "action": "wbgetentities",
                "ids": "|".join(ids),
                "props": "labels|aliases|descriptions|claims|sitelinks",
                "languages": languages,
                "format": "json",
            }
        )
        return payload.get("entities", {})

    async def _get_json(self, params: dict[str, str]) -> dict:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with self._request_lock:
                    elapsed = time.monotonic() - self._last_request_at
                    if elapsed < self.min_interval_seconds:
                        await asyncio.sleep(self.min_interval_seconds - elapsed)
                    self.__class__._last_request_at = time.monotonic()
                    return await asyncio.to_thread(self._get_json_sync, params)
            except HTTPError as exc:
                last_error = exc
                if exc.code != 429 or attempt >= self.max_retries:
                    raise
                retry_after = exc.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(2**attempt, 8)
                await asyncio.sleep(delay)
        if last_error:
            raise last_error
        raise RuntimeError("Wikidata request failed without an exception")

    def _get_json_sync(self, params: dict[str, str]) -> dict:
        url = f"{self.API_URL}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
