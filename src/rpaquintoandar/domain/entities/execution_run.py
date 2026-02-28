from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from rpaquintoandar.domain.enums import StepStatus


@dataclass(slots=True)
class ExecutionRun:
    mode: str
    status: StepStatus = StepStatus.RUNNING
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    id: int | None = None

    def finish(self, status: StepStatus) -> None:
        self.status = status
        self.finished_at = datetime.now()
