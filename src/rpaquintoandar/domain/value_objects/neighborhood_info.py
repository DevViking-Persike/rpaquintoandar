from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NeighborhoodInfo:
    name: str
    slug: str  # e.g. "mooca-sao-paulo-sp-brasil"
    estimated_count: int = 0
