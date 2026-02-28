from __future__ import annotations

from typing import Protocol

from rpaquintoandar.domain.entities import ExecutionRun, StepRecord


class IExecutionRepository(Protocol):
    async def create_run(self, run: ExecutionRun) -> ExecutionRun: ...

    async def update_run(self, run: ExecutionRun) -> None: ...

    async def create_step(self, step: StepRecord) -> StepRecord: ...

    async def update_step(self, step: StepRecord) -> None: ...
