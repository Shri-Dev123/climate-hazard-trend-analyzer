import hashlib
import json
from datetime import date
from typing import Any

import httpx
from fastapi import HTTPException

from app.cache import CacheRepository
from app.config import Settings
from app.models import RegionSearchResult


def stable_key(prefix: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


class WeatherService:
    def __init__(self, settings: Settings, cache: CacheRepository) -> None:
        self.settings = settings
        self.cache = cache

    async def search_regions(self, query: str) -> list[RegionSearchResult]:
        cache_key = stable_key("region-search", {"query": query.lower().strip()})
        cached = await self.cache.get("region_search", cache_key)
        if cached:
            return [RegionSearchResult(**item) for item in cached["payload"]["results"]]

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                self.settings.open_meteo_geocode_url,
                params={"name": query, "count": 8, "language": "en", "format": "json"},
            )
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail="Region search provider failed")

        payload = response.json()
        results = [
            RegionSearchResult(
                id=item["id"],
                name=item["name"],
                country=item.get("country"),
                admin1=item.get("admin1"),
                latitude=item["latitude"],
                longitude=item["longitude"],
            )
            for item in payload.get("results", [])
        ]
        await self.cache.set("region_search", cache_key, {"results": [item.model_dump() for item in results]})
        return results

    async def daily_max_temperatures(
        self,
        latitude: float,
        longitude: float,
        start_year: int,
        end_year: int,
    ) -> tuple[list[dict[str, Any]], bool]:
        request_payload = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "start_year": start_year,
            "end_year": end_year,
        }
        cache_key = stable_key("weather", request_payload)
        cached = await self.cache.get("weather_daily", cache_key)
        if cached:
            return cached["payload"]["daily"], True

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": date(start_year, 1, 1).isoformat(),
            "end_date": date(end_year, 12, 31).isoformat(),
            "daily": "temperature_2m_max",
            "timezone": "auto",
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.get(self.settings.open_meteo_archive_url, params=params)
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail="Historical weather provider failed")

        payload = response.json()
        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        temperatures = daily.get("temperature_2m_max") or []
        records = [
            {"date": day, "temperature_2m_max": temp}
            for day, temp in zip(dates, temperatures, strict=False)
            if temp is not None
        ]
        if not records:
            raise HTTPException(status_code=422, detail="No historical temperature data found")

        await self.cache.set("weather_daily", cache_key, {"daily": records, "source": "Open-Meteo Archive API"})
        return records, False

