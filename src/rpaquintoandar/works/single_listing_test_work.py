from __future__ import annotations

import json
import logging

from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.shared.di_container import Container

logger = logging.getLogger(__name__)


class SingleListingTestWork:
    def __init__(self, container: Container, listing_id: str) -> None:
        self._container = container
        self._listing_id = listing_id

    async def execute(self) -> None:
        logger.info("Starting SingleListingTestWork (test-listing) id=%s", self._listing_id)

        listing = Listing(
            source_id=self._listing_id,
            source_url=f"https://www.quintoandar.com.br/imovel/{self._listing_id}",
        )

        detail_extractor = await self._container.detail_extractor()
        json_str = await detail_extractor.extract_detail(listing)

        print(f"\n{'='*60}")
        print(f"Listing Detail Extraction: {self._listing_id}")
        print(f"{'='*60}\n")

        if not json_str:
            print("FAILED: Could not extract __NEXT_DATA__")
            return

        try:
            data = json.loads(json_str)
            props = data.get("props", {}).get("pageProps", {})
            house = props.get("house", {}) or props.get("listing", {}) or {}

            print(f"  Description:  {(house.get('description', '') or '')[:200]}...")
            print(f"  Address:      {house.get('address', {})}")
            print(f"  Price:        {house.get('salePrice', 'N/A')}")
            print(f"  Area:         {house.get('area', 'N/A')} m²")
            print(f"  Bedrooms:     {house.get('bedrooms', 'N/A')}")
            print(f"  Furnished:    {house.get('furnished', 'N/A')}")
            print(f"  Pet Friendly: {house.get('petFriendly', 'N/A')}")
            print(f"  Year Built:   {house.get('yearBuilt', 'N/A')}")
            print(f"  JSON size:    {len(json_str)} chars")
        except json.JSONDecodeError:
            print(f"  Raw data ({len(json_str)} chars): {json_str[:500]}...")

        print()
        logger.info("SingleListingTestWork finished")
