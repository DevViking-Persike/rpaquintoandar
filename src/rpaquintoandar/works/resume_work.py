from __future__ import annotations

import logging

from rpaquintoandar.application.pipeline import PipelineContext, PipelineRunner
from rpaquintoandar.application.steps import ExportStep, ExtractStep
from rpaquintoandar.domain.value_objects import SearchCriteria
from rpaquintoandar.shared.di_container import Container

logger = logging.getLogger(__name__)


class ResumeWork:
    def __init__(self, container: Container) -> None:
        self._container = container

    async def execute(self) -> None:
        logger.info("Starting ResumeWork")
        context = PipelineContext(
            container=self._container,
            criteria=SearchCriteria(),
            metadata={"mode": "resume"},
        )
        runner = PipelineRunner(steps=[ExtractStep(), ExportStep()])
        await runner.run(context)
        logger.info("ResumeWork finished")
