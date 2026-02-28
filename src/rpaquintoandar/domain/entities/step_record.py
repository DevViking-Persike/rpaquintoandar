from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from rpaquintoandar.domain.enums import StepStatus


@dataclass(slots=True)
class StepRecord:
    execution_run_id: int
    step_name: str
    status: StepStatus = StepStatus.RUNNING
    items_processed: int = 0
    items_created: int = 0
    items_failed: int = 0
    error_message: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    id: int | None = None

    def finish(self, status: StepStatus) -> None:
        self.status = status
        self.finished_at = datetime.now()
