from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from rpaquintoandar.application.pipeline.pipeline_context import PipelineContext
    from rpaquintoandar.domain.value_objects import StepResult


class IStep(Protocol):
    @property
    def name(self) -> str: ...

    async def execute(self, context: PipelineContext) -> StepResult: ...
