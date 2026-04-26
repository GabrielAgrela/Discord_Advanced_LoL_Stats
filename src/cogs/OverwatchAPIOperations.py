import asyncio
from urllib.parse import quote
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from disnake.ext import commands


class OverwatchAPIOperations(commands.Cog):
    BASE_URL = "https://overfast-api.tekrop.fr"

    def __init__(self, bot):
        self.bot = bot
        self.heroes_map: Optional[Dict[str, Dict[str, Any]]] = None

    async def _request_json(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, Optional[Any], Optional[str]]:
        url = f"{self.BASE_URL}{path}"
        timeout = aiohttp.ClientTimeout(total=15)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        payload = await response.json()
                    except Exception:
                        payload = None
                    return response.status, payload, retry_after
        except asyncio.TimeoutError:
            return 504, {"error": "Request timed out."}, None
        except aiohttp.ClientError as e:
            return 503, {"error": str(e)}, None

    async def search_players(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        status, payload, _ = await self._request_json(
            "/players",
            params={"name": query, "limit": limit}
        )
        if status != 200 or not isinstance(payload, dict):
            return []
        results = payload.get("results")
        if not isinstance(results, list):
            return []
        return results

    @staticmethod
    def _normalize_hero_key(hero_key: Any) -> str:
        return str(hero_key).strip().lower().replace(" ", "-") if hero_key is not None else ""

    async def ensure_heroes_map(self) -> None:
        """Load and cache Overwatch heroes list (key -> hero payload)."""
        if isinstance(self.heroes_map, dict) and self.heroes_map:
            return

        status, payload, _ = await self._request_json("/heroes")
        mapping: Dict[str, Dict[str, Any]] = {}
        if status == 200 and isinstance(payload, list):
            for hero in payload:
                if not isinstance(hero, dict):
                    continue
                key = self._normalize_hero_key(hero.get("key"))
                if not key:
                    continue
                mapping[key] = hero
        self.heroes_map = mapping

    def get_hero_portrait_from_cache(self, hero_key: Any) -> Optional[str]:
        """Return portrait URL for a hero key from cached map."""
        if not isinstance(self.heroes_map, dict) or not self.heroes_map:
            return None
        normalized_key = self._normalize_hero_key(hero_key)
        if not normalized_key:
            return None
        hero = self.heroes_map.get(normalized_key)
        if not isinstance(hero, dict):
            return None
        portrait = hero.get("portrait")
        return str(portrait) if portrait else None

    def _pick_best_search_result(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not results:
            return None

        query_normalized = query.strip().lower()
        normalized_results = [r for r in results if isinstance(r, dict)]

        for result in normalized_results:
            if not result.get("is_public"):
                continue
            name = str(result.get("name", "")).lower()
            player_id = str(result.get("player_id", "")).lower()
            if query_normalized in (name, player_id):
                return result

        for result in normalized_results:
            if result.get("is_public"):
                return result

        return normalized_results[0] if normalized_results else None

    @staticmethod
    def _safe_player_id(player_id: str) -> str:
        return quote(player_id, safe="-_%")

    async def get_player_summary(self, player_id: str) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
        return await self._request_json(f"/players/{self._safe_player_id(player_id)}/summary")

    async def get_player_stats_summary(
        self,
        player_id: str,
        gamemode: Optional[str] = None,
        platform: Optional[str] = None
    ) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
        params: Dict[str, str] = {}
        if gamemode:
            params["gamemode"] = gamemode
        if platform:
            params["platform"] = platform
        return await self._request_json(
            f"/players/{self._safe_player_id(player_id)}/stats/summary",
            params=params or None
        )

    async def resolve_player_and_stats(
        self,
        player_query: str,
        gamemode: Optional[str] = None,
        platform: Optional[str] = None
    ) -> Dict[str, Any]:
        normalized_query = player_query.strip().replace("#", "-")
        if not normalized_query:
            return {"error": "Player name cannot be empty."}

        # First try direct lookup, then fall back to search.
        summary_status, summary_data, retry_after = await self.get_player_summary(normalized_query)
        resolved_player_id = normalized_query
        search_match = None

        if summary_status != 200:
            if summary_status == 429:
                return {"error": f"Overwatch API rate limit reached. Try again in ~{retry_after or '?'} seconds."}
            if summary_status >= 500:
                return {"error": "Overwatch API is temporarily unavailable. Try again shortly."}

            search_results = await self.search_players(normalized_query)
            search_match = self._pick_best_search_result(normalized_query, search_results)
            if not search_match:
                return {"error": f"Could not find an Overwatch player matching `{player_query}`."}

            resolved_player_id = str(search_match.get("player_id", "")).strip()
            if not resolved_player_id:
                return {"error": f"Could not resolve a valid player id for `{player_query}`."}

            summary_status, summary_data, retry_after = await self.get_player_summary(resolved_player_id)
            if summary_status == 429:
                return {"error": f"Overwatch API rate limit reached. Try again in ~{retry_after or '?'} seconds."}
            if summary_status >= 500:
                return {"error": "Overwatch API is temporarily unavailable. Try again shortly."}
            if summary_status != 200:
                summary_data = {
                    "username": search_match.get("name"),
                    "avatar": search_match.get("avatar"),
                    "namecard": search_match.get("namecard"),
                    "title": search_match.get("title"),
                    "competitive": None,
                    "endorsement": None,
                }

        stats_status, stats_data, retry_after = await self.get_player_stats_summary(
            resolved_player_id,
            gamemode=gamemode,
            platform=platform
        )

        if stats_status == 429:
            return {"error": f"Overwatch API rate limit reached. Try again in ~{retry_after or '?'} seconds."}
        if stats_status >= 500:
            return {"error": "Overwatch API is temporarily unavailable. Try again shortly."}
        if stats_status == 404:
            return {
                "player_id": resolved_player_id,
                "summary": summary_data,
                "stats": None,
                "search_match": search_match,
            }
        if stats_status != 200:
            return {"error": "Could not retrieve Overwatch stats for that player right now."}

        return {
            "player_id": resolved_player_id,
            "summary": summary_data,
            "stats": stats_data,
            "search_match": search_match,
        }


def setup(bot):
    bot.add_cog(OverwatchAPIOperations(bot))
