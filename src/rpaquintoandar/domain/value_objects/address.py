from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Address:
    street: str = ""
    number: str = ""
    neighborhood: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
