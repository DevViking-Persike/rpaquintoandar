from __future__ import annotations

from dataclasses import dataclass

from rpaquintoandar.domain.enums import ErrorCategory


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    category: ErrorCategory
    message: str
    detail: str = ""

    @classmethod
    def from_exception(
        cls, exc: Exception, category: ErrorCategory = ErrorCategory.UNKNOWN
    ) -> ErrorInfo:
        return cls(
            category=category,
            message=str(exc),
            detail=type(exc).__name__,
        )
