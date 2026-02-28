from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    city: str = "São Paulo"
    state: str = "SP"
    neighborhoods: list[str] = field(default_factory=list)
    price_min: float | None = None
    price_max: float | None = None
    bedrooms_min: int | None = None
    bedrooms_max: int | None = None
    area_min: float | None = None
    area_max: float | None = None
