from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.value_objects import SearchCriteria, StepResult
from rpaquintoandar.shared.di_container import Container


@dataclass(slots=True)
class PipelineContext:
    container: Container
    criteria: SearchCriteria
    listings: list[Listing] = field(default_factory=list)
    step_results: dict[str, StepResult] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_result(self, step_name: str, result: StepResult) -> None:
        self.step_results[step_name] = result
