from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from rpaquintoandar.domain.enums import FurnishedStatus, ProcessingStatus, PropertyType
from rpaquintoandar.domain.value_objects import Address, ContentHash, Coordinates, PriceInfo


@dataclass(slots=True)
class Listing:
    source_id: str
    source_url: str
    property_type: PropertyType = PropertyType.UNKNOWN
    address: Address = field(default_factory=Address)
    price: PriceInfo = field(default_factory=PriceInfo)
    area_m2: float = 0.0
    bedrooms: int = 0
    bathrooms: int = 0
    parking_spaces: int = 0
    coordinates: Coordinates | None = None
    images: list[str] = field(default_factory=list)
    amenities: list[str] = field(default_factory=list)
    # Enriched from detail page
    description: str = ""
    building_amenities: list[str] = field(default_factory=list)
    unit_amenities: list[str] = field(default_factory=list)
    floor_number: int | None = None
    total_floors: int | None = None
    year_built: int | None = None
    furnished: FurnishedStatus = FurnishedStatus.UNKNOWN
    pet_friendly: bool | None = None
    # Processing
    content_hash: ContentHash | None = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    id: int | None = None

    def mark_enriched(self, content_hash: ContentHash) -> None:
        self.content_hash = content_hash
        self.status = ProcessingStatus.ENRICHED
        self.updated_at = datetime.now()

    def mark_failed(self) -> None:
        self.status = ProcessingStatus.FAILED
        self.updated_at = datetime.now()

    def mark_duplicate(self) -> None:
        self.status = ProcessingStatus.DUPLICATE
        self.updated_at = datetime.now()
