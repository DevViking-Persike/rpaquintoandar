import asyncio
import tempfile
from pathlib import Path

import pytest

from rpaquintoandar.infrastructure.config.settings_loader import Settings
from rpaquintoandar.infrastructure.persistence.database_manager import DatabaseManager


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test.db")


@pytest.fixture
async def db_manager(tmp_db_path: str) -> DatabaseManager:
    manager = DatabaseManager(tmp_db_path)
    await manager.initialize()
    yield manager  # type: ignore[misc]
    await manager.close()


@pytest.fixture
def settings() -> Settings:
    return Settings()
