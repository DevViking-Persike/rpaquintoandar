from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriceInfo:
    sale_price: float = 0.0
    condo_fee: float = 0.0
    iptu: float = 0.0
