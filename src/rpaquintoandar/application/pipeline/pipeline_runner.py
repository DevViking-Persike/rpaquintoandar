from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rpaquintoandar.domain.entities import ExecutionRun, StepRecord
from rpaquintoandar.domain.enums import StepStatus

if TYPE_CHECKING:
    from rpaquintoandar.application.pipeline.pipeline_context import PipelineContext
    from rpaquintoandar.application.pipeline.step_protocol import IStep

logger = logging.getLogger(__name__)


class PipelineRunner:
    def __init__(self, steps: list[IStep]) -> None:
        self._steps = steps

    async def run(self, context: PipelineContext) -> None:
        execution_repo = context.container.execution_repo()
        run = ExecutionRun(mode=context.metadata.get("mode", "pipeline"))
        run = await execution_repo.create_run(run)
        assert run.id is not None

        overall_status = StepStatus.SUCCEEDED

        for step in self._steps:
            logger.info("Starting step: %s", step.name)
            step_record = StepRecord(
                execution_run_id=run.id,
                step_name=step.name,
            )
            step_record = await execution_repo.create_step(step_record)

            try:
                result = await step.execute(context)
                context.add_result(step.name, result)

                step_record.items_processed = result.items_processed
                step_record.items_created = result.items_created
                step_record.items_failed = result.items_failed

                if result.has_errors:
                    step_record.error_message = "; ".join(
                        e.message for e in result.errors
                    )
                    step_record.finish(StepStatus.FAILED)
                    overall_status = StepStatus.FAILED
                    logger.error(
                        "Step %s failed: %s", step.name, step_record.error_message
                    )
                else:
                    step_record.finish(StepStatus.SUCCEEDED)
                    logger.info(
                        "Step %s completed: processed=%d created=%d",
                        step.name,
                        result.items_processed,
                        result.items_created,
                    )

            except Exception as exc:
                step_record.error_message = str(exc)
                step_record.finish(StepStatus.FAILED)
                overall_status = StepStatus.FAILED
                logger.exception("Step %s raised an exception", step.name)

            await execution_repo.update_step(step_record)

            if step_record.status == StepStatus.FAILED:
                break

        run.finish(overall_status)
        await execution_repo.update_run(run)
        logger.info("Pipeline finished with status: %s", overall_status)
