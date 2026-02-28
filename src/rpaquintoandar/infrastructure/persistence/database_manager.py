from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

MIGRATIONS = [
    # Migration 0: initial schema
    """
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT UNIQUE NOT NULL,
        source_url TEXT NOT NULL,
        property_type TEXT DEFAULT 'unknown',
        street TEXT DEFAULT '',
        number TEXT DEFAULT '',
        neighborhood TEXT DEFAULT '',
        city TEXT DEFAULT '',
        state TEXT DEFAULT '',
        zip_code TEXT DEFAULT '',
        sale_price REAL DEFAULT 0,
        condo_fee REAL DEFAULT 0,
        iptu REAL DEFAULT 0,
        area_m2 REAL DEFAULT 0,
        bedrooms INTEGER DEFAULT 0,
        bathrooms INTEGER DEFAULT 0,
        parking_spaces INTEGER DEFAULT 0,
        latitude REAL,
        longitude REAL,
        images TEXT DEFAULT '[]',
        amenities TEXT DEFAULT '[]',
        description TEXT DEFAULT '',
        building_amenities TEXT DEFAULT '[]',
        unit_amenities TEXT DEFAULT '[]',
        floor_number INTEGER,
        total_floors INTEGER,
        year_built INTEGER,
        furnished TEXT DEFAULT 'unknown',
        pet_friendly INTEGER,
        content_hash TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
    CREATE INDEX IF NOT EXISTS idx_listings_source_id ON listings(source_id);
    CREATE INDEX IF NOT EXISTS idx_listings_content_hash ON listings(content_hash);
    CREATE INDEX IF NOT EXISTS idx_listings_neighborhood ON listings(neighborhood);
    CREATE INDEX IF NOT EXISTS idx_listings_city ON listings(city);
    CREATE INDEX IF NOT EXISTS idx_listings_sale_price ON listings(sale_price);

    CREATE TABLE IF NOT EXISTS execution_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mode TEXT NOT NULL,
        status TEXT DEFAULT 'running',
        started_at TEXT NOT NULL,
        finished_at TEXT
    );

    CREATE TABLE IF NOT EXISTS step_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        execution_run_id INTEGER NOT NULL,
        step_name TEXT NOT NULL,
        status TEXT DEFAULT 'running',
        items_processed INTEGER DEFAULT 0,
        items_created INTEGER DEFAULT 0,
        items_failed INTEGER DEFAULT 0,
        error_message TEXT DEFAULT '',
        started_at TEXT NOT NULL,
        finished_at TEXT,
        FOREIGN KEY (execution_run_id) REFERENCES execution_runs(id)
    );

    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY
    );
    INSERT OR IGNORE INTO schema_version (version) VALUES (0);
    """,
]


class DatabaseManager:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA foreign_keys=ON")
        await self._run_migrations()
        logger.info("Database initialized at %s", self._db_path)

    async def _run_migrations(self) -> None:
        conn = self.connection

        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        row = await cursor.fetchone()
        current_version = -1

        if row:
            cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
            result = await cursor.fetchone()
            if result and result[0] is not None:
                current_version = result[0]

        for i, migration in enumerate(MIGRATIONS):
            if i > current_version:
                logger.info("Running migration %d", i)
                await conn.executescript(migration)
                await conn.commit()

    @property
    def connection(self) -> aiosqlite.Connection:
        assert self._connection is not None, "Database not initialized"
        return self._connection

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
