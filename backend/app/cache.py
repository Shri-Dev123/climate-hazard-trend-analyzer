import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from app.config import Settings


class CacheRepository(Protocol):
    async def get(self, collection: str, key: str) -> dict[str, Any] | None:
        ...

    async def set(self, collection: str, key: str, payload: dict[str, Any]) -> None:
        ...


class FileCacheRepository:
    def __init__(self, base_path: str = ".cache") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    def _path(self, collection: str, key: str) -> Path:
        safe_key = key.replace("/", "_")
        folder = self.base_path / collection
        folder.mkdir(exist_ok=True)
        return folder / f"{safe_key}.json"

    async def get(self, collection: str, key: str) -> dict[str, Any] | None:
        path = self._path(collection, key)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    async def set(self, collection: str, key: str, payload: dict[str, Any]) -> None:
        path = self._path(collection, key)
        document = {"key": key, "payload": payload, "created_at": datetime.now(UTC).isoformat()}
        with path.open("w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2)


class MongoCacheRepository:
    def __init__(self, settings: Settings) -> None:
        from motor.motor_asyncio import AsyncIOMotorClient

        if not settings.mongodb_uri:
            raise ValueError("MONGODB_URI is required for MongoCacheRepository")
        self.client = AsyncIOMotorClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db]

    async def get(self, collection: str, key: str) -> dict[str, Any] | None:
        document = await self.db[collection].find_one({"key": key}, {"_id": False})
        return document

    async def set(self, collection: str, key: str, payload: dict[str, Any]) -> None:
        await self.db[collection].update_one(
            {"key": key},
            {"$set": {"key": key, "payload": payload, "created_at": datetime.now(UTC)}},
            upsert=True,
        )


def build_cache(settings: Settings) -> CacheRepository:
    if settings.mongodb_uri:
        return MongoCacheRepository(settings)
    return FileCacheRepository()

