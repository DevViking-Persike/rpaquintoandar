from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class ApiSettings:
    count_url: str = (
        "https://apigw.prod.quintoandar.com.br/house-listing-search/v2/search/count"
    )
    timeout_seconds: float = 30.0
    delay_between_requests_ms: int = 1500


@dataclass(slots=True)
class BrowserSettings:
    headless: bool = True
    timeout_ms: int = 30000
    slow_mo_ms: int = 100
    viewport_width: int = 1280
    viewport_height: int = 720


@dataclass(slots=True)
class ScrapingSettings:
    detail_base_url: str = "https://www.quintoandar.com.br/imovel"
    max_pages: int = 50
    retry_attempts: int = 3
    retry_delay_ms: int = 3000


@dataclass(slots=True)
class SearchSettings:
    city: str = "São Paulo"
    state: str = "SP"
    neighborhoods: list[str] = field(default_factory=list)
    target_count: int = 0
    apartment_only: bool = True
    price_ranges: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class PersistenceSettings:
    database_path: str = "data/rpaquintoandar.db"


@dataclass(slots=True)
class ExportSettings:
    output_dir: str = "data/export"
    formats: list[str] = field(default_factory=lambda: ["json"])


@dataclass(slots=True)
class LoggingSettings:
    level: str = "INFO"
    file: str = "data/rpaquintoandar.log"


@dataclass(slots=True)
class Settings:
    api: ApiSettings = field(default_factory=ApiSettings)
    browser: BrowserSettings = field(default_factory=BrowserSettings)
    scraping: ScrapingSettings = field(default_factory=ScrapingSettings)
    search: SearchSettings = field(default_factory=SearchSettings)
    persistence: PersistenceSettings = field(default_factory=PersistenceSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)


def load_settings(config_path: str | Path = "config/settings.yaml") -> Settings:
    path = Path(config_path)
    if not path.exists():
        return Settings()

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    settings = Settings()

    if api := raw.get("api"):
        settings.api = ApiSettings(
            count_url=api.get("count_url", settings.api.count_url),
            timeout_seconds=api.get("timeout_seconds", 30.0),
            delay_between_requests_ms=api.get("delay_between_requests_ms", 1500),
        )

    if browser := raw.get("browser"):
        settings.browser = BrowserSettings(
            headless=browser.get("headless", True),
            timeout_ms=browser.get("timeout_ms", 30000),
            slow_mo_ms=browser.get("slow_mo_ms", 100),
            viewport_width=browser.get("viewport", {}).get("width", 1280),
            viewport_height=browser.get("viewport", {}).get("height", 720),
        )

    if scraping := raw.get("scraping"):
        settings.scraping = ScrapingSettings(
            detail_base_url=scraping.get("detail_base_url", settings.scraping.detail_base_url),
            max_pages=scraping.get("max_pages", 50),
            retry_attempts=scraping.get("retry_attempts", 3),
            retry_delay_ms=scraping.get("retry_delay_ms", 3000),
        )

    if search := raw.get("search"):
        settings.search = SearchSettings(
            city=search.get("city", "São Paulo"),
            state=search.get("state", "SP"),
            neighborhoods=search.get("neighborhoods", []),
            target_count=search.get("target_count", 0),
            apartment_only=search.get("apartment_only", True),
            price_ranges=search.get("price_ranges", []),
        )

    if persistence := raw.get("persistence"):
        settings.persistence = PersistenceSettings(
            database_path=persistence.get("database_path", "data/rpaquintoandar.db"),
        )

    if export_cfg := raw.get("export"):
        settings.export = ExportSettings(
            output_dir=export_cfg.get("output_dir", "data/export"),
            formats=export_cfg.get("formats", ["json"]),
        )

    if logging_cfg := raw.get("logging"):
        settings.logging = LoggingSettings(
            level=logging_cfg.get("level", "INFO"),
            file=logging_cfg.get("file", "data/rpaquintoandar.log"),
        )

    return settings
