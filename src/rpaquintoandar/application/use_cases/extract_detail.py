from __future__ import annotations

import json
import logging

from rpaquintoandar.application.dtos import ExtractResult
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

        props = data.get("props", {}).get("pageProps", {})
        house = props.get("house", {}) or props.get("listing", {}) or {}

        if desc := house.get("description", ""):
            listing.description = desc

        if building := house.get("buildingAmenities", []):
            listing.building_amenities = [str(a) for a in building]

        if unit := house.get("unitAmenities", []):
            listing.unit_amenities = [str(a) for a in unit]

        if (floor := house.get("floorNumber")) is not None:
            try:
                listing.floor_number = int(floor)
            except (ValueError, TypeError):
                pass

        if (total_floors := house.get("totalFloors")) is not None:
            try:
                listing.total_floors = int(total_floors)
            except (ValueError, TypeError):
                pass

        if (year := house.get("yearBuilt")) is not None:
            try:
                listing.year_built = int(year)
            except (ValueError, TypeError):
                pass

        furnished_raw = house.get("furnished", "")
        if furnished_raw:
            mapping = {
                "FURNISHED": FurnishedStatus.FURNISHED,
                "SEMI_FURNISHED": FurnishedStatus.SEMI_FURNISHED,
                "UNFURNISHED": FurnishedStatus.UNFURNISHED,
            }
            listing.furnished = mapping.get(
                str(furnished_raw).upper(), FurnishedStatus.UNKNOWN
            )

        if (pet := house.get("petFriendly")) is not None:
            listing.pet_friendly = bool(pet)

        # Enrich address if data available
        if addr_data := house.get("address", {}):
            listing.address = Address(
                street=addr_data.get("street", listing.address.street),
                number=addr_data.get("number", listing.address.number),
                neighborhood=addr_data.get("neighbourhood", listing.address.neighborhood),
                city=addr_data.get("city", listing.address.city),
                state=addr_data.get("state", listing.address.state),
                zip_code=addr_data.get("zipCode", listing.address.zip_code),
            )

        # Enrich coordinates
        lat = house.get("latitude")
        lon = house.get("longitude")
        if lat and lon:
            try:
                listing.coordinates = Coordinates(
                    latitude=float(lat), longitude=float(lon)
                )
            except (ValueError, TypeError):
                pass

        # Enrich price
        sale_price = house.get("salePrice") or house.get("sale_price")
        condo = house.get("condoFee") or house.get("condo_fee")
        iptu = house.get("iptu")
        if sale_price is not None:
            listing.price = PriceInfo(
                sale_price=float(sale_price) if sale_price else listing.price.sale_price,
                condo_fee=float(condo) if condo else listing.price.condo_fee,
                iptu=float(iptu) if iptu else listing.price.iptu,
            )

        # Enrich images
        if images := house.get("imageList", []) or house.get("images", []):
            if isinstance(images, list):
                listing.images = [
                    img if isinstance(img, str) else img.get("url", "")
                    for img in images
                ]
