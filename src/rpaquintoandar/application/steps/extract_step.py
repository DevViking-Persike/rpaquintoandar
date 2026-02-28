from __future__ import annotations

import logging

from rpaquintoandar.application.pipeline import PipelineContext
from rpaquintoandar.application.use_cases import ExtractDetailUseCase
from rpaquintoandar.domain.enums import ErrorCategory, StepStatus
from rpaquintoandar.domain.value_objects import ErrorInfo, StepResult

logger = logging.getLogger(__name__)


class ExtractStep:
    @property
    def name(self) -> str:
        return "extract"

    async def execute(self, context: PipelineContext) -> StepResult:
        result = StepResult()
        try:
            detail_extractor = await context.container.detail_extractor()
            repo = context.container.listing_repo()
            use_case = ExtractDetailUseCase(detail_extractor, repo)
            extract_result = await use_case.execute()

            result.items_processed = extract_result.total_processed
            result.items_created = extract_result.enriched
            result.items_failed = extract_result.failed

        except Exception as exc:
            result.status = StepStatus.FAILED
            result.errors.append(ErrorInfo.from_exception(exc, ErrorCategory.UNKNOWN))
            logger.exception("ExtractStep failed")

        return result
