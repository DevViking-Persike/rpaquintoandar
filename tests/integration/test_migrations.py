from __future__ import annotations

import pytest

from rpaquintoandar.infrastructure.persistence.database_manager import DatabaseManager


@pytest.mark.asyncio
async def test_database_initializes(tmp_db_path: str):
    manager = DatabaseManager(tmp_db_path)
    await manager.initialize()

    conn = manager.connection

    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in await cursor.fetchall()}

    assert "listings" in tables
    assert "execution_runs" in tables
    assert "step_records" in tables
    assert "schema_version" in tables

    cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 0

    await manager.close()


@pytest.mark.asyncio
async def test_double_initialization_is_safe(tmp_db_path: str):
    manager = DatabaseManager(tmp_db_path)
    await manager.initialize()
    await manager.close()

    manager2 = DatabaseManager(tmp_db_path)
    await manager2.initialize()
    await manager2.close()
