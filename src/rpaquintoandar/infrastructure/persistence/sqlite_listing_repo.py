from __future__ import annotations

import json
import logging
from datetime import datetime

from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.enums import FurnishedStatus, ProcessingStatus, PropertyType
from rpaquintoandar.domain.value_objects import Address, ContentHash, Coordinates, PriceInfo
from rpaquintoandar.infrastructure.persistence.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class SqliteListingRepo:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager

    async def upsert(self, listing: Listing) -> Listing:
        conn = self._db.connection
        existing = await self.get_by_source_id(listing.source_id)

        if existing:
            await conn.execute(
                """
                UPDATE listings
                SET property_type=?, street=?, number=?, neighborhood=?, city=?, state=?,
                    zip_code=?, sale_price=?, condo_fee=?, iptu=?,
                    area_m2=?, bedrooms=?, bathrooms=?, parking_spaces=?,
                    latitude=?, longitude=?, images=?, amenities=?,
                    description=?, building_amenities=?, unit_amenities=?,
                    floor_number=?, total_floors=?, year_built=?, furnished=?,
                    pet_friendly=?, content_hash=?, status=?, updated_at=?
                WHERE source_id=?
                """,
                (
                    listing.property_type.value,
                    listing.address.street,
                    listing.address.number,
                    listing.address.neighborhood,
                    listing.address.city,
                    listing.address.state,
                    listing.address.zip_code,
                    listing.price.sale_price,
                    listing.price.condo_fee,
                    listing.price.iptu,
                    listing.area_m2,
                    listing.bedrooms,
                    listing.bathrooms,
                    listing.parking_spaces,
                    listing.coordinates.latitude if listing.coordinates else None,
                    listing.coordinates.longitude if listing.coordinates else None,
                    json.dumps(listing.images),
                    json.dumps(listing.amenities),
                    listing.description,
                    json.dumps(listing.building_amenities),
                    json.dumps(listing.unit_amenities),
                    listing.floor_number,
                    listing.total_floors,
                    listing.year_built,
                    listing.furnished.value,
                    1 if listing.pet_friendly else (0 if listing.pet_friendly is False else None),
                    str(listing.content_hash) if listing.content_hash else "",
                    listing.status.value,
                    datetime.now().isoformat(),
                    listing.source_id,
                ),
            )
            await conn.commit()
            listing.id = existing.id
        else:
            now = datetime.now().isoformat()
            cursor = await conn.execute(
                """
                INSERT INTO listings
                (source_id, source_url, property_type,
                 street, number, neighborhood, city, state, zip_code,
                 sale_price, condo_fee, iptu,
                 area_m2, bedrooms, bathrooms, parking_spaces,
                 latitude, longitude, images, amenities,
                 description, building_amenities, unit_amenities,
                 floor_number, total_floors, year_built, furnished,
                 pet_friendly, content_hash, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    listing.source_id,
                    listing.source_url,
                    listing.property_type.value,
                    listing.address.street,
                    listing.address.number,
                    listing.address.neighborhood,
                    listing.address.city,
                    listing.address.state,
                    listing.address.zip_code,
                    listing.price.sale_price,
                    listing.price.condo_fee,
                    listing.price.iptu,
                    listing.area_m2,
                    listing.bedrooms,
                    listing.bathrooms,
                    listing.parking_spaces,
                    listing.coordinates.latitude if listing.coordinates else None,
                    listing.coordinates.longitude if listing.coordinates else None,
                    json.dumps(listing.images),
                    json.dumps(listing.amenities),
                    listing.description,
                    json.dumps(listing.building_amenities),
                    json.dumps(listing.unit_amenities),
                    listing.floor_number,
                    listing.total_floors,
                    listing.year_built,
                    listing.furnished.value,
                    1 if listing.pet_friendly else (
                        0 if listing.pet_friendly is False else None
                    ),
                    str(listing.content_hash) if listing.content_hash else "",
                    listing.status.value,
                    now,
                    now,
                ),
            )
            await conn.commit()
            listing.id = cursor.lastrowid

        return listing

    async def upsert_many(self, listings: list[Listing]) -> int:
        created = 0
        for listing in listings:
            existing = await self.get_by_source_id(listing.source_id)
            if not existing:
                await self.upsert(listing)
                created += 1
        logger.info("Upserted %d/%d listings", created, len(listings))
        return created

    async def get_by_status(self, status: ProcessingStatus) -> list[Listing]:
        conn = self._db.connection
        cursor = await conn.execute(
            "SELECT * FROM listings WHERE status=?", (status.value,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_listing(row) for row in rows]

    async def get_by_source_id(self, source_id: str) -> Listing | None:
        conn = self._db.connection
        cursor = await conn.execute(
            "SELECT * FROM listings WHERE source_id=?", (source_id,)
        )
        row = await cursor.fetchone()
        return self._row_to_listing(row) if row else None

    async def exists_by_hash(self, content_hash: ContentHash) -> bool:
        conn = self._db.connection
        cursor = await conn.execute(
            "SELECT 1 FROM listings WHERE content_hash=? AND status=?",
            (str(content_hash), ProcessingStatus.ENRICHED.value),
        )
        return await cursor.fetchone() is not None

    async def get_enriched(self) -> list[Listing]:
        return await self.get_by_status(ProcessingStatus.ENRICHED)

    @staticmethod
    def _row_to_listing(row: object) -> Listing:
        r = dict(row)  # type: ignore[arg-type]
        hash_val = r["content_hash"]
        lat = r["latitude"]
        lon = r["longitude"]
        pet = r["pet_friendly"]

        return Listing(
            id=r["id"],
            source_id=r["source_id"],
            source_url=r["source_url"],
            property_type=PropertyType(r["property_type"]) if r["property_type"] else PropertyType.UNKNOWN,
            address=Address(
                street=r["street"] or "",
                number=r["number"] or "",
                neighborhood=r["neighborhood"] or "",
                city=r["city"] or "",
                state=r["state"] or "",
                zip_code=r["zip_code"] or "",
            ),
            price=PriceInfo(
                sale_price=r["sale_price"] or 0.0,
                condo_fee=r["condo_fee"] or 0.0,
                iptu=r["iptu"] or 0.0,
            ),
            area_m2=r["area_m2"] or 0.0,
            bedrooms=r["bedrooms"] or 0,
            bathrooms=r["bathrooms"] or 0,
            parking_spaces=r["parking_spaces"] or 0,
            coordinates=Coordinates(latitude=lat, longitude=lon) if lat and lon else None,
            images=json.loads(r["images"]) if r["images"] else [],
            amenities=json.loads(r["amenities"]) if r["amenities"] else [],
            description=r["description"] or "",
            building_amenities=json.loads(r["building_amenities"]) if r["building_amenities"] else [],
            unit_amenities=json.loads(r["unit_amenities"]) if r["unit_amenities"] else [],
            floor_number=r["floor_number"],
            total_floors=r["total_floors"],
            year_built=r["year_built"],
            furnished=FurnishedStatus(r["furnished"]) if r["furnished"] else FurnishedStatus.UNKNOWN,
            pet_friendly=True if pet == 1 else (False if pet == 0 else None),
            content_hash=ContentHash(value=hash_val) if hash_val else None,
            status=ProcessingStatus(r["status"]),
            created_at=datetime.fromisoformat(r["created_at"]),
            updated_at=datetime.fromisoformat(r["updated_at"]),
        )
