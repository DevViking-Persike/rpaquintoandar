from __future__ import annotations

import logging

from rpaquintoandar.application.pipeline import PipelineContext
from rpaquintoandar.application.use_cases import SearchListingsUseCase, SegmentedSearchUseCase
from rpaquintoandar.domain.enums import ErrorCategory, StepStatus
from rpaquintoandar.domain.value_objects import ErrorInfo, StepResult

logger = logging.getLogger(__name__)


class SearchStep:
    @property
    def name(self) -> str:
        return "search"

    async def execute(self, context: PipelineContext) -> StepResult:
        result = StepResult()
        try:
            segmented = context.metadata.get("segmented", False)

            if segmented:
                search_result = await self._run_segmented(context)
            else:
                search_result = await self._run_simple(context)

            result.items_processed = search_result.total_found
            result.items_created = search_result.new_listings

        except Exception as exc:
            result.status = StepStatus.FAILED
            result.errors.append(ErrorInfo.from_exception(exc, ErrorCategory.API))
            logger.exception("SearchStep failed")

        return result

    @staticmethod
    async def _run_simple(context: PipelineContext):
        from rpaquintoandar.application.dtos import SearchResult

        api_client = await context.container.api_client()
        repo = context.container.listing_repo()
        max_pages = context.metadata.get(
            "max_pages", context.container.settings.scraping.max_pages
        )
        use_case = SearchListingsUseCase(api_client, repo, max_pages=max_pages)
        return await use_case.execute(context.criteria)

    @staticmethod
    async def _run_segmented(context: PipelineContext):
        api_client = await context.container.api_client()
        repo = context.container.listing_repo()
        collector = await context.container.coordinates_collector()
        max_pages = context.metadata.get(
            "max_pages", context.container.settings.scraping.max_pages
        )
        target_count = context.metadata.get(
            "target_count", context.container.settings.search.target_count
        )

        use_case = SegmentedSearchUseCase(
            api_client, repo, collector, max_pages_per_segment=max_pages
        )
        return await use_case.execute(
            context.criteria,
            target_count=target_count,
            property_type="apartamento" if context.container.settings.search.apartment_only else None,
        )
