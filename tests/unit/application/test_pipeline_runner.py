from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rpaquintoandar.application.pipeline import PipelineContext, PipelineRunner
from rpaquintoandar.domain.value_objects import SearchCriteria, StepResult


def make_mock_container():
    container = MagicMock()
    execution_repo = AsyncMock()
    execution_repo.create_run = AsyncMock(
        side_effect=lambda r: setattr(r, "id", 1) or r
    )
    execution_repo.update_run = AsyncMock()
    execution_repo.create_step = AsyncMock(
        side_effect=lambda s: setattr(s, "id", 1) or s
    )
    execution_repo.update_step = AsyncMock()
    container.execution_repo.return_value = execution_repo
    return container


class FakeStep:
    def __init__(self, name: str, result: StepResult | None = None):
        self._name = name
        self._result = result or StepResult()

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, context: PipelineContext) -> StepResult:
        return self._result


class FailingStep:
    @property
    def name(self) -> str:
        return "failing"

    async def execute(self, context: PipelineContext) -> StepResult:
        raise RuntimeError("Step exploded")


@pytest.mark.asyncio
async def test_runner_executes_all_steps():
    container = make_mock_container()
    context = PipelineContext(
        container=container,
        criteria=SearchCriteria(),
    )
    step1 = FakeStep("step1")
    step2 = FakeStep("step2")

    runner = PipelineRunner(steps=[step1, step2])
    await runner.run(context)

    assert "step1" in context.step_results
    assert "step2" in context.step_results


@pytest.mark.asyncio
async def test_runner_stops_on_failure():
    container = make_mock_container()
    context = PipelineContext(
        container=container,
        criteria=SearchCriteria(),
    )
    runner = PipelineRunner(steps=[FailingStep(), FakeStep("after_fail")])
    await runner.run(context)

    assert "after_fail" not in context.step_results
