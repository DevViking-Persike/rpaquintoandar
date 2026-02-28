from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rpaquintoandar.infrastructure.alerting.log_alerter import LogAlerter
from rpaquintoandar.infrastructure.api.coordinates_collector import CoordinatesCollector
from rpaquintoandar.infrastructure.api.quintoandar_api_client import QuintoAndarApiClient
from rpaquintoandar.infrastructure.browser.detail_extractor.playwright_detail_extractor import (
    PlaywrightDetailExtractor,
)
from rpaquintoandar.infrastructure.browser.playwright_manager import PlaywrightBrowserManager
from rpaquintoandar.infrastructure.config.settings_loader import Settings
from rpaquintoandar.infrastructure.persistence.database_manager import DatabaseManager
from rpaquintoandar.infrastructure.persistence.sqlite_execution_repo import SqliteExecutionRepo
from rpaquintoandar.infrastructure.persistence.sqlite_listing_repo import SqliteListingRepo

if TYPE_CHECKING:
    from rpaquintoandar.domain.interfaces import (
        IAlerter,
        IBrowserManager,
        IDetailExtractor,
        IExecutionRepository,
        IListingRepository,
        ISearchApiClient,
    )

logger = logging.getLogger(__name__)


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._db_manager: DatabaseManager | None = None
        self._browser_manager: PlaywrightBrowserManager | None = None
        self._api_client: QuintoAndarApiClient | None = None
        self._coordinates_collector: CoordinatesCollector | None = None

    async def initialize(self) -> None:
        self._db_manager = DatabaseManager(self.settings.persistence.database_path)
        await self._db_manager.initialize()
        logger.info("Container initialized")

    async def shutdown(self) -> None:
        if self._browser_manager:
            await self._browser_manager.stop()
        if self._api_client:
            await self._api_client.close()
        if self._db_manager:
            await self._db_manager.close()
        logger.info("Container shut down")

    @property
    def db_manager(self) -> DatabaseManager:
        assert self._db_manager is not None, "Container not initialized"
        return self._db_manager

    def listing_repo(self) -> IListingRepository:
        return SqliteListingRepo(self.db_manager)

    def execution_repo(self) -> IExecutionRepository:
        return SqliteExecutionRepo(self.db_manager)

    async def api_client(self) -> ISearchApiClient:
        if self._api_client is None:
            bm = await self.browser_manager()
            self._api_client = QuintoAndarApiClient(self.settings.api, bm)
        return self._api_client

    async def browser_manager(self) -> IBrowserManager:
        if self._browser_manager is None:
            self._browser_manager = PlaywrightBrowserManager(self.settings.browser)
            await self._browser_manager.start()
        return self._browser_manager

    async def coordinates_collector(self) -> CoordinatesCollector:
        if self._coordinates_collector is None:
            bm = await self.browser_manager()
            self._coordinates_collector = CoordinatesCollector(bm, self.settings.api)
        return self._coordinates_collector

    async def detail_extractor(self) -> IDetailExtractor:
        bm = await self.browser_manager()
        return PlaywrightDetailExtractor(bm, self.settings.scraping)

    def alerter(self) -> IAlerter:
        return LogAlerter()
