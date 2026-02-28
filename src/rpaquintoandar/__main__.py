from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from rpaquintoandar.domain.value_objects import SearchCriteria
from rpaquintoandar.infrastructure.config import load_settings
from rpaquintoandar.shared.di_container import Container
from rpaquintoandar.shared.logging_config import setup_logging
from rpaquintoandar.works import (
    FullCrawlWork,
    ResumeWork,
    SingleListingTestWork,
    SinglePageTestWork,
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="rpaquintoandar",
        description="RPA bot for scraping QuintoAndar real estate listings",
    )
    parser.add_argument(
        "--mode",
        choices=["full-crawl", "resume", "test-search", "test-listing"],
        default="full-crawl",
        help="Execution mode (default: full-crawl)",
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to config file (default: config/settings.yaml)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible mode",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Override log level from config",
    )
    parser.add_argument(
        "--listing-id",
        default=None,
        help="Listing ID for test-listing mode",
    )
    parser.add_argument(
        "--city",
        default=None,
        help="City to search (overrides config)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Max pages to crawl (overrides config)",
    )
    return parser.parse_args()


def build_criteria(args: argparse.Namespace, settings: object) -> SearchCriteria:
    search = settings.search  # type: ignore[attr-defined]

    city = args.city if args.city else search.city
    state = search.state
    neighborhoods = search.neighborhoods

    return SearchCriteria(
        city=city,
        state=state,
        neighborhoods=neighborhoods,
    )


async def run(args: argparse.Namespace) -> None:
    settings = load_settings(args.config)

    log_level = args.log_level or settings.logging.level
    setup_logging(level=log_level, log_file=settings.logging.file)

    if args.no_headless:
        settings.browser.headless = False

    container = Container(settings)

    needs_db = args.mode in ("full-crawl", "resume")
    if needs_db:
        await container.initialize()

    try:
        criteria = build_criteria(args, settings)
        logger.info("Mode: %s | City: %s", args.mode, criteria.city)

        if args.mode == "test-search":
            work = SinglePageTestWork(container, criteria)
        elif args.mode == "test-listing":
            if not args.listing_id:
                print("Error: --listing-id is required for test-listing mode")
                sys.exit(1)
            work = SingleListingTestWork(container, args.listing_id)
        elif args.mode == "resume":
            work = ResumeWork(container)
        else:
            work = FullCrawlWork(container, criteria, max_pages=args.max_pages)

        await work.execute()

    finally:
        await container.shutdown()


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
