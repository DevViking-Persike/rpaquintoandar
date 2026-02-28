from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

import httpx

from rpaquintoandar.domain.interfaces import IBrowserManager
from rpaquintoandar.domain.value_objects import Coordinates
from rpaquintoandar.infrastructure.config.settings_loader import ApiSettings

logger = logging.getLogger(__name__)

DETAIL_BASE_URL = "https://www.quintoandar.com.br/imovel"
SEARCH_PAGE_URL = "https://www.quintoandar.com.br/comprar/imovel"


class CoordinatesCollector:
    """Collects listing IDs in bulk via QuintoAndar's coordinates API.

    The coordinates API returns up to 10,000 listing IDs per request
    for a given map viewport. This is much more efficient than SSR
    pagination which cycles through ~12 listings per neighborhood.

    Flow:
    1. Load a search page in Playwright to capture the coordinates API URL
    2. Replay that URL (and variants) via httpx to collect IDs
    3. Return list of (source_id, lat, lon) tuples
    """

    def __init__(
        self,
        browser_manager: IBrowserManager,
        settings: ApiSettings,
    ) -> None:
        self._browser = browser_manager
        self._settings = settings

    async def collect_ids(
        self,
        city_slug: str,
        property_type: str = "apartamento",
        target_count: int = 1000,
    ) -> list[tuple[str, float, float]]:
        """Collect listing IDs by intercepting the coordinates API.

        Returns list of (source_id, latitude, longitude) tuples.
        """
        # Step 1: Load search page and capture coordinates API URL + headers
        coord_url, coord_headers = await self._capture_coordinates_request(
            city_slug, property_type
        )

        if not coord_url:
            logger.warning("Failed to capture coordinates API URL")
            return []

        # Step 2: Fetch IDs via httpx (reusing the captured URL)
        all_ids = await self._fetch_ids_from_coordinates(
            coord_url, coord_headers, target_count
        )

        logger.info("Collected %d unique listing IDs", len(all_ids))
        return all_ids[:target_count]

    async def _capture_coordinates_request(
        self, city_slug: str, property_type: str
    ) -> tuple[str | None, dict[str, str]]:
        """Load a search page and capture the coordinates API request."""
        url = f"{SEARCH_PAGE_URL}/{city_slug}/{property_type}"
        captured_url: str | None = None
        captured_headers: dict[str, str] = {}

        page = await self._browser.new_page()

        async def on_request(request):
            nonlocal captured_url, captured_headers
            if "search/coordinates" in request.url:
                captured_url = request.url
                captured_headers = dict(request.headers)

        page.on("request", on_request)

        try:
            logger.info("Loading search page to capture coordinates API: %s", url)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
        finally:
            await page.close()

        return captured_url, captured_headers

    async def _fetch_ids_from_coordinates(
        self,
        base_url: str,
        browser_headers: dict[str, str],
        target_count: int,
    ) -> list[tuple[str, float, float]]:
        """Fetch listing IDs from coordinates API via httpx."""
        headers = {
            "accept": browser_headers.get("accept", "application/json"),
            "user-agent": browser_headers.get("user-agent", ""),
        }
        if "x-ab-test" in browser_headers:
            headers["x-ab-test"] = browser_headers["x-ab-test"]

        seen_ids: dict[str, tuple[float, float]] = {}

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            # First call: use exact captured URL
            ids = await self._single_fetch(client, base_url, headers)
            for source_id, lat, lon in ids:
                if source_id not in seen_ids:
                    seen_ids[source_id] = (lat, lon)

            logger.info(
                "Coordinates API: %d IDs from initial viewport (target: %d)",
                len(seen_ids),
                target_count,
            )

            # If we need more and have less than target, shift viewport
            if len(seen_ids) < target_count:
                for viewport in self._generate_viewports():
                    if len(seen_ids) >= target_count:
                        break
                    shifted_url = self._apply_viewport(base_url, viewport)
                    ids = await self._single_fetch(client, shifted_url, headers)
                    new_count = 0
                    for source_id, lat, lon in ids:
                        if source_id not in seen_ids:
                            seen_ids[source_id] = (lat, lon)
                            new_count += 1
                    logger.info(
                        "Viewport shift: +%d new IDs (total: %d)", new_count, len(seen_ids)
                    )

        result = [(sid, lat, lon) for sid, (lat, lon) in seen_ids.items()]
        return result

    @staticmethod
    async def _single_fetch(
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
    ) -> list[tuple[str, float, float]]:
        """Execute a single coordinates API call and return IDs."""
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning("Coordinates API returned %d", resp.status_code)
                return []

            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            result = []
            for hit in hits:
                source_id = str(hit.get("_id", ""))
                source = hit.get("_source", {})
                location = source.get("location", {})
                lat = location.get("lat", 0.0)
                lon = location.get("lon", 0.0)
                if source_id:
                    result.append((source_id, lat, lon))
            return result

        except Exception:
            logger.exception("Failed to fetch coordinates API")
            return []

    @staticmethod
    def _generate_viewports() -> list[dict[str, float]]:
        """Generate shifted viewports to cover more area around São Paulo."""
        # São Paulo center: -23.55, -46.63
        # Each viewport covers ~0.15 degrees (~15km)
        base_lat, base_lng = -23.55, -46.63
        offsets = [
            (0.0, 0.15),  # east
            (0.0, -0.15),  # west
            (0.15, 0.0),  # south
            (-0.15, 0.0),  # north
            (0.15, 0.15),  # southeast
            (-0.15, 0.15),  # northeast
            (0.15, -0.15),  # southwest
            (-0.15, -0.15),  # northwest
        ]
        viewports = []
        for dlat, dlng in offsets:
            clat = base_lat + dlat
            clng = base_lng + dlng
            viewports.append({
                "north": clat + 0.08,
                "south": clat - 0.08,
                "east": clng + 0.08,
                "west": clng - 0.08,
            })
        return viewports

    @staticmethod
    def _apply_viewport(url: str, viewport: dict[str, float]) -> str:
        """Replace viewport parameters in the coordinates URL."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)

        params["filters.location.viewport.north"] = [str(viewport["north"])]
        params["filters.location.viewport.south"] = [str(viewport["south"])]
        params["filters.location.viewport.east"] = [str(viewport["east"])]
        params["filters.location.viewport.west"] = [str(viewport["west"])]

        # Rebuild query string
        flat_params = []
        for k, v_list in params.items():
            for v in v_list:
                flat_params.append((k, v))
        new_query = urlencode(flat_params)
        return urlunparse(parsed._replace(query=new_query))
