from __future__ import annotations

import logging

from rpaquintoandar.application.pipeline import PipelineContext, PipelineRunner
from rpaquintoandar.application.steps import ExportStep, ExtractStep, SearchStep
from rpaquintoandar.domain.value_objects import SearchCriteria
from rpaquintoandar.shared.di_container import Container

logger = logging.getLogger(__name__)


class FullCrawlWork:
    def __init__(
        self,
        container: Container,
        criteria: SearchCriteria,
        max_pages: int | None = None,
    ) -> None:
        self._container = container
        self._criteria = criteria
        self._max_pages = max_pages

    async def execute(self) -> None:
        logger.info("Starting FullCrawlWork")
        metadata: dict = {"mode": "full-crawl"}
        if self._max_pages is not None:
            metadata["max_pages"] = self._max_pages

        context = PipelineContext(
            container=self._container,
            criteria=self._criteria,
            metadata=metadata,
        )
        runner = PipelineRunner(
            steps=[SearchStep(), ExtractStep(), ExportStep()],
        )
        await runner.run(context)
        logger.info("FullCrawlWork finished")
