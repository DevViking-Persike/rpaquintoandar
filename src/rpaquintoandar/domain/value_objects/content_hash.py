from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContentHash:
    value: str

    @classmethod
    def from_text(cls, text: str) -> ContentHash:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return cls(value=digest)

    def __str__(self) -> str:
        return self.value
