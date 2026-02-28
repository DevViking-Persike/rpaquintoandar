from __future__ import annotations

import logging

from rpaquintoandar.application.pipeline import PipelineContext
from rpaquintoandar.application.use_cases import SearchListingsUseCase
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
            api_client = context.container.api_client()
            repo = context.container.listing_repo()
            max_pages = context.metadata.get(
                "max_pages", context.container.settings.scraping.max_pages
            )
            use_case = SearchListingsUseCase(api_client, repo, max_pages=max_pages)
            search_result = await use_case.execute(context.criteria)

            result.items_processed = search_result.total_found
            result.items_created = search_result.new_listings

        except Exception as exc:
            result.status = StepStatus.FAILED
            result.errors.append(ErrorInfo.from_exception(exc, ErrorCategory.API))
            logger.exception("SearchStep failed")

        return result
