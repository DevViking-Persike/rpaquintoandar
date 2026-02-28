from __future__ import annotations

import logging

from rpaquintoandar.domain.value_objects import ErrorInfo

logger = logging.getLogger(__name__)


class LogAlerter:
    async def alert(self, error: ErrorInfo) -> None:
        logger.warning(
            "ALERT [%s]: %s (detail: %s)",
            error.category.value,
            error.message,
            error.detail,
        )
