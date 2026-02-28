from __future__ import annotations

import logging

from rpaquintoandar.domain.value_objects import SearchCriteria
from rpaquintoandar.shared.di_container import Container

logger = logging.getLogger(__name__)


class SinglePageTestWork:
    def __init__(self, container: Container, criteria: SearchCriteria) -> None:
        self._container = container
        self._criteria = criteria

    async def execute(self) -> None:
        logger.info("Starting SinglePageTestWork (test-search)")
        api_client = self._container.api_client()
        listings, total_count = await api_client.search(self._criteria, offset=0)

        print(f"\n{'='*60}")
        print(f"Search Results: {len(listings)} listings (total available: {total_count})")
        print(f"{'='*60}\n")

        for i, listing in enumerate(listings[:5], 1):
            print(f"#{i}")
            print(f"  ID:           {listing.source_id}")
            print(f"  URL:          {listing.source_url}")
            print(f"  Type:         {listing.property_type.value}")
            print(f"  Neighborhood: {listing.address.neighborhood}")
            print(f"  City:         {listing.address.city}")
            print(f"  Price:        R$ {listing.price.sale_price:,.2f}")
            print(f"  Area:         {listing.area_m2} m²")
            print(f"  Bedrooms:     {listing.bedrooms}")
            print(f"  Bathrooms:    {listing.bathrooms}")
            print(f"  Parking:      {listing.parking_spaces}")
            print()

        logger.info("SinglePageTestWork finished")
