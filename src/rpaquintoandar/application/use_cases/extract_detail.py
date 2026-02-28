from __future__ import annotations

import json
import logging

from rpaquintoandar.application.dtos import ExtractResult
from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.enums import FurnishedStatus, ProcessingStatus
from rpaquintoandar.domain.interfaces import IDetailExtractor, IListingRepository
from rpaquintoandar.domain.value_objects import Address, ContentHash, Coordinates, PriceInfo

logger = logging.getLogger(__name__)


class ExtractDetailUseCase:
    def __init__(
        self,
        detail_extractor: IDetailExtractor,
        listing_repo: IListingRepository,
    ) -> None:
        self._extractor = detail_extractor
        self._repo = listing_repo

    async def execute(self) -> ExtractResult:
        pending = await self._repo.get_by_status(ProcessingStatus.PENDING)
        logger.info("Found %d pending listings to enrich", len(pending))

        result = ExtractResult(total_processed=len(pending))

        for listing in pending:
            try:
                json_str = await self._extractor.extract_detail(listing)
                if not json_str:
                    listing.mark_failed()
                    await self._repo.upsert(listing)
                    result.failed += 1
                    continue

                self._enrich_from_next_data(listing, json_str)

                content_hash = ContentHash.from_text(json_str)

                if await self._repo.exists_by_hash(content_hash):
                    listing.mark_duplicate()
                    await self._repo.upsert(listing)
                    result.duplicates += 1
                    logger.debug("Duplicate: %s", listing.source_id)
                    continue

                listing.mark_enriched(content_hash)
                await self._repo.upsert(listing)
                result.enriched += 1
                logger.debug("Enriched: %s", listing.source_id)

            except Exception:
                listing.mark_failed()
                await self._repo.upsert(listing)
                result.failed += 1
                logger.exception("Failed to enrich: %s", listing.source_id)

        logger.info(
            "Enrichment completed: processed=%d enriched=%d duplicates=%d failed=%d",
            result.total_processed,
            result.enriched,
            result.duplicates,
            result.failed,
        )
        return result

    @staticmethod
    def _enrich_from_next_data(listing: Listing, json_str: str) -> None:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in __NEXT_DATA__ for %s", listing.source_id)
            return

        initial = data.get("props", {}).get("pageProps", {}).get("initialState", {})
        house = initial.get("house", {}).get("houseInfo", {})
        if not house:
            logger.warning("No houseInfo in __NEXT_DATA__ for %s", listing.source_id)
            return

        # Description
        if desc := house.get("remarks", ""):
            listing.description = desc

        # Building amenities (installations = condominium features)
        installations = house.get("installations", [])
        if isinstance(installations, list):
            listing.building_amenities = [
                inst.get("text", inst.get("key", ""))
                for inst in installations
                if isinstance(inst, dict) and inst.get("value") == "SIM"
            ]

        # Unit amenities (comfort + practicality commodities)
        unit_items: list[str] = []
        for field in ("comfortCommodities", "practicalityCommodities"):
            items = house.get(field, [])
            if isinstance(items, list):
                unit_items.extend(
                    item.get("text", item.get("key", ""))
                    for item in items
                    if isinstance(item, dict) and item.get("value") == "SIM"
                )
        if unit_items:
            listing.unit_amenities = unit_items

        # Floor range
        range_floor = house.get("rangeFloor")
        if isinstance(range_floor, dict):
            floor_min = range_floor.get("min")
            if floor_min is not None:
                try:
                    listing.floor_number = int(floor_min)
                except (ValueError, TypeError):
                    pass

        # Construction year
        if (year := house.get("constructionYear")) is not None:
            try:
                listing.year_built = int(year)
            except (ValueError, TypeError):
                pass

        # Furnished
        has_furniture = house.get("hasFurniture")
        if has_furniture is True:
            listing.furnished = FurnishedStatus.FURNISHED
        elif has_furniture is False:
            listing.furnished = FurnishedStatus.UNFURNISHED

        # Pet friendly
        if (pet := house.get("acceptsPets")) is not None:
            listing.pet_friendly = bool(pet)

        # Enrich address
        addr_data = house.get("address")
        if isinstance(addr_data, dict):
            listing.address = Address(
                street=addr_data.get("street", listing.address.street) or "",
                number=addr_data.get("number", listing.address.number) or "",
                neighborhood=addr_data.get("neighborhood", listing.address.neighborhood) or "",
                city=addr_data.get("city", listing.address.city) or "",
                state=addr_data.get("stateAcronym", listing.address.state) or "",
                zip_code=addr_data.get("zipCode", listing.address.zip_code) or "",
            )
            # Coordinates from address
            lat = addr_data.get("lat")
            lng = addr_data.get("lng")
            if lat and lng:
                try:
                    listing.coordinates = Coordinates(
                        latitude=float(lat), longitude=float(lng)
                    )
                except (ValueError, TypeError):
                    pass

        # Enrich price with precise values
        sale_price = house.get("salePrice")
        condo = house.get("condoPrice")
        iptu = house.get("iptu")
        if sale_price is not None:
            listing.price = PriceInfo(
                sale_price=float(sale_price) if sale_price else listing.price.sale_price,
                condo_fee=float(condo) if condo else listing.price.condo_fee,
                iptu=float(iptu) if iptu else listing.price.iptu,
            )

        # Enrich photos with full URLs
        photos = house.get("photos", [])
        if isinstance(photos, list) and photos:
            photo_base = "https://www.quintoandar.com.br/img/med/"
            listing.images = [
                f"{photo_base}{p['url']}" if isinstance(p, dict) and not p.get("url", "").startswith("http")
                else (p.get("url", "") if isinstance(p, dict) else str(p))
                for p in photos
                if isinstance(p, dict) and p.get("url")
            ]
