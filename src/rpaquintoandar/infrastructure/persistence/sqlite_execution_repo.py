from __future__ import annotations

import logging
from datetime import datetime

from rpaquintoandar.domain.entities import ExecutionRun, StepRecord
from rpaquintoandar.domain.enums import StepStatus
from rpaquintoandar.infrastructure.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class SqliteExecutionRepo:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager

    async def create_run(self, run: ExecutionRun) -> ExecutionRun:
        conn = self._db.connection
        cursor = await conn.execute(
            """
            INSERT INTO execution_runs (mode, status, started_at, finished_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                run.mode,
                run.status.value,
                run.started_at.isoformat(),
                run.finished_at.isoformat() if run.finished_at else None,
            ),
        )
        await conn.commit()
        run.id = cursor.lastrowid
        logger.info("Created execution run #%d mode=%s", run.id, run.mode)
        return run

    async def update_run(self, run: ExecutionRun) -> None:
        conn = self._db.connection
        await conn.execute(
            """
            UPDATE execution_runs SET status=?, finished_at=? WHERE id=?
            """,
            (
                run.status.value,
                run.finished_at.isoformat() if run.finished_at else None,
                run.id,
            ),
        )
        await conn.commit()

    async def create_step(self, step: StepRecord) -> StepRecord:
        conn = self._db.connection
        cursor = await conn.execute(
            """
            INSERT INTO step_records
            (execution_run_id, step_name, status, items_processed, items_created,
             items_failed, error_message, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                step.execution_run_id,
                step.step_name,
                step.status.value,
                step.items_processed,
                step.items_created,
                step.items_failed,
                step.error_message,
                step.started_at.isoformat(),
                step.finished_at.isoformat() if step.finished_at else None,
            ),
        )
        await conn.commit()
        step.id = cursor.lastrowid
        return step

    async def update_step(self, step: StepRecord) -> None:
        conn = self._db.connection
        await conn.execute(
            """
            UPDATE step_records
            SET status=?, items_processed=?, items_created=?, items_failed=?,
                error_message=?, finished_at=?
            WHERE id=?
            """,
            (
                step.status.value,
                step.items_processed,
                step.items_created,
                step.items_failed,
                step.error_message,
                step.finished_at.isoformat() if step.finished_at else None,
                step.id,
            ),
        )
        await conn.commit()
