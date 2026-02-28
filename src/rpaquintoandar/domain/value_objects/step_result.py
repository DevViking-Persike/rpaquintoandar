from __future__ import annotations

from dataclasses import dataclass, field

from rpaquintoandar.domain.enums import StepStatus
from rpaquintoandar.domain.value_objects.error_info import ErrorInfo


@dataclass(slots=True)
class StepResult:
    status: StepStatus = StepStatus.SUCCEEDED
    items_processed: int = 0
    items_created: int = 0
    items_failed: int = 0
    errors: list[ErrorInfo] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
