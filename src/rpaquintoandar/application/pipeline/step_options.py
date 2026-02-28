from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StepOptions:
    continue_on_error: bool = True
    max_retries: int = 3
    retry_delay_ms: int = 2000
