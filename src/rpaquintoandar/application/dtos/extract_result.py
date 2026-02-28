from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExtractResult:
    total_processed: int = 0
    enriched: int = 0
    duplicates: int = 0
    failed: int = 0
