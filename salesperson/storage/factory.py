from __future__ import annotations

from salesperson.config import DB_PATH
from salesperson.storage.base import PlatformRepository
from salesperson.storage.memory import MemoryRepository


def create_repository() -> PlatformRepository:
    if DB_PATH.strip():
        from salesperson.storage.sqlite import SqliteRepository

        return SqliteRepository(DB_PATH.strip())
    return MemoryRepository()
