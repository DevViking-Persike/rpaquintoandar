from __future__ import annotations

import logging
from typing import Any

from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.enums import PropertyType
from rpaquintoandar.domain.value_objects import Address, Coordinates, PriceInfo

logger = logging.getLogger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _parse_property_type(raw: str | None) -> PropertyType:
    if not raw:
        return PropertyType.UNKNOWN
    mapping = {
        "APARTMENT": PropertyType.APARTMENT,
        "HOUSE": PropertyType.HOUSE,
        "CONDOMINIUM": PropertyType.CONDO,
        "STUDIO": PropertyType.STUDIO,
    }
    return mapping.get(raw.upper(), PropertyType.UNKNOWN)


def parse_search_hit(source: dict[str, Any]) -> Listing:
    source_id = str(source.get("id", ""))
    source_url = f"https://www.quintoandar.com.br/imovel/{source_id}"

    lat = source.get("latitude")
    lon = source.get("longitude")
    coordinates = Coordinates(latitude=float(lat), longitude=float(lon)) if lat and lon else None

    images = source.get("imageList", []) or source.get("images", []) or []
    if isinstance(images, list):
        images = [img if isinstance(img, str) else img.get("url", "") for img in images]

    amenities_raw = source.get("amenities", []) or []
    amenities = [str(a) for a in amenities_raw] if isinstance(amenities_raw, list) else []

    return Listing(
        source_id=source_id,
        source_url=source_url,
        property_type=_parse_property_type(source.get("type")),
        address=Address(
            street=source.get("street", "") or "",
            number=source.get("streetNumber", "") or "",
            neighborhood=source.get("neighbourhood", "") or source.get("neighborhood", "") or "",
            city=source.get("city", "") or "",
            state=source.get("state", "") or "",
            zip_code=source.get("zipCode", "") or source.get("cep", "") or "",
        ),
        price=PriceInfo(
            sale_price=_safe_float(source.get("salePrice") or source.get("sale_price")),
            condo_fee=_safe_float(source.get("condoFee") or source.get("condo_fee")),
            iptu=_safe_float(source.get("iptuPlusCondominium") or source.get("iptu")),
        ),
        area_m2=_safe_float(source.get("area") or source.get("areaM2")),
        bedrooms=_safe_int(source.get("bedrooms") or source.get("dorms")),
        bathrooms=_safe_int(source.get("bathrooms")),
        parking_spaces=_safe_int(source.get("parkingSpaces") or source.get("parking")),
        coordinates=coordinates,
        images=images,
        amenities=amenities,
    )


def parse_search_response(data: dict[str, Any]) -> tuple[list[Listing], int]:
    hits = data.get("hits", {})
    total = hits.get("total", {})
    total_count = total.get("value", 0) if isinstance(total, dict) else int(total or 0)

    listings: list[Listing] = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        if not source:
            continue
        try:
            listing = parse_search_hit(source)
            if listing.source_id:
                listings.append(listing)
        except Exception:
            logger.exception("Failed to parse search hit: %s", hit.get("_id", "unknown"))

    return listings, total_count
