from __future__ import annotations

import logging
from typing import Any

from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.enums import PropertyType
from rpaquintoandar.domain.value_objects import Address, Coordinates, PriceInfo

logger = logging.getLogger(__name__)

# Mapping for SSR property types (Portuguese)
SSR_TYPE_MAP = {
    "apartamento": PropertyType.APARTMENT,
    "casa": PropertyType.HOUSE,
    "casa de condomínio": PropertyType.CONDO,
    "studio": PropertyType.STUDIO,
    "kitnet": PropertyType.STUDIO,
}


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
    # Try direct mapping first (SSR uses Portuguese names)
    result = SSR_TYPE_MAP.get(raw.lower())
    if result:
        return result
    # Fallback to uppercase API format
    mapping = {
        "APARTMENT": PropertyType.APARTMENT,
        "HOUSE": PropertyType.HOUSE,
        "CONDOMINIUM": PropertyType.CONDO,
        "STUDIO": PropertyType.STUDIO,
    }
    return mapping.get(raw.upper(), PropertyType.UNKNOWN)


def _parse_photos(photos: Any) -> list[str]:
    if not photos or not isinstance(photos, list):
        return []
    urls = []
    for photo in photos:
        if isinstance(photo, str):
            urls.append(photo)
        elif isinstance(photo, dict):
            url = photo.get("url") or photo.get("original") or photo.get("src", "")
            if url:
                urls.append(url)
    return urls


def _parse_condo_iptu(condo_iptu: Any) -> tuple[float, float]:
    """Parse condoIptu field which may be a formatted string like 'R$ 800 + R$ 200'."""
    if not condo_iptu:
        return 0.0, 0.0
    if isinstance(condo_iptu, (int, float)):
        return float(condo_iptu), 0.0
    if isinstance(condo_iptu, str):
        parts = condo_iptu.replace("R$", "").replace(".", "").replace(",", ".").split("+")
        try:
            condo = float(parts[0].strip()) if len(parts) > 0 else 0.0
            iptu = float(parts[1].strip()) if len(parts) > 1 else 0.0
            return condo, iptu
        except (ValueError, IndexError):
            return 0.0, 0.0
    return 0.0, 0.0


def parse_ssr_house(house: dict[str, Any]) -> Listing:
    """Parse a house object from SSR __NEXT_DATA__ initialState.houses."""
    source_id = str(house.get("id", ""))
    source_url = f"https://www.quintoandar.com.br/imovel/{source_id}"

    # Address from SSR may be a string or dict
    neighborhood = (
        house.get("neighbourhood", "")
        or house.get("regionName", "")
        or ""
    )
    address_raw = house.get("address", "")
    if isinstance(address_raw, dict):
        address = Address(
            street=address_raw.get("street", "") or "",
            number=address_raw.get("number", "") or "",
            neighborhood=address_raw.get("neighbourhood", "") or neighborhood,
            city=address_raw.get("city", "") or "",
            state=address_raw.get("state", "") or "",
            zip_code=address_raw.get("zipCode", "") or "",
        )
    else:
        address = Address(neighborhood=neighborhood)

    # Parse condoIptu field
    condo_fee, iptu = _parse_condo_iptu(house.get("condoIptu"))

    # Coordinates
    lat = house.get("latitude")
    lon = house.get("longitude")
    coordinates = Coordinates(latitude=float(lat), longitude=float(lon)) if lat and lon else None

    # Photos/images
    images = _parse_photos(house.get("photos"))

    # Amenities
    amenities_raw = house.get("amenities", []) or []
    amenities = [str(a) for a in amenities_raw] if isinstance(amenities_raw, list) else []

    return Listing(
        source_id=source_id,
        source_url=source_url,
        property_type=_parse_property_type(house.get("type")),
        address=address,
        price=PriceInfo(
            sale_price=_safe_float(house.get("salePrice")),
            condo_fee=condo_fee,
            iptu=iptu,
        ),
        area_m2=_safe_float(house.get("area")),
        bedrooms=_safe_int(house.get("bedrooms")),
        bathrooms=_safe_int(house.get("bathrooms")),
        parking_spaces=_safe_int(house.get("parkingSpots") or house.get("parkingSpaces")),
        coordinates=coordinates,
        images=images,
        amenities=amenities,
    )


def parse_ssr_houses(houses: dict[str, Any]) -> list[Listing]:
    """Parse the houses dict from SSR __NEXT_DATA__ initialState."""
    listings: list[Listing] = []
    for key, house in houses.items():
        if not isinstance(house, dict):
            continue
        if not house.get("id"):
            continue
        try:
            listing = parse_ssr_house(house)
            if listing.source_id:
                listings.append(listing)
        except Exception:
            logger.exception("Failed to parse SSR house: %s", key)
    return listings


def parse_search_response(data: dict[str, Any]) -> tuple[list[Listing], int]:
    """Parse response from count/search API (kept for compatibility)."""
    hits = data.get("hits", {})
    total = hits.get("total", {})
    total_count = total.get("value", 0) if isinstance(total, dict) else int(total or 0)

    listings: list[Listing] = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        if not source:
            continue
        try:
            listing = parse_ssr_house(source)
            if listing.source_id:
                listings.append(listing)
        except Exception:
            logger.exception("Failed to parse search hit: %s", hit.get("_id", "unknown"))

    return listings, total_count
