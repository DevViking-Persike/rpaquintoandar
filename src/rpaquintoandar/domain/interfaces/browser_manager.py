from __future__ import annotations

from typing import Protocol

from playwright.async_api import Page


class IBrowserManager(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def new_page(self) -> Page: ...
