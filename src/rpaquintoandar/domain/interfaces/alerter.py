from __future__ import annotations

from typing import Protocol

from rpaquintoandar.domain.value_objects import ErrorInfo


class IAlerter(Protocol):
    async def alert(self, error: ErrorInfo) -> None: ...
