from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from rpaquintoandar.application.pipeline import PipelineContext
from rpaquintoandar.domain.enums import ErrorCategory, StepStatus
from rpaquintoandar.domain.value_objects import ErrorInfo, StepResult

logger = logging.getLogger(__name__)


class ExportStep:
    @property
    def name(self) -> str:
        return "export"

    async def execute(self, context: PipelineContext) -> StepResult:
        result = StepResult()
        try:
            repo = context.container.listing_repo()
            listings = await repo.get_enriched()
            result.items_processed = len(listings)

            if not listings:
                logger.info("No listings to export")
                return result

            output_dir = Path(context.container.settings.export.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            formats = context.container.settings.export.formats

            records = [
                {
                    "source_id": l.source_id,
                    "source_url": l.source_url,
                    "property_type": l.property_type.value,
                    "street": l.address.street,
                    "number": l.address.number,
                    "neighborhood": l.address.neighborhood,
                    "city": l.address.city,
                    "state": l.address.state,
                    "zip_code": l.address.zip_code,
                    "sale_price": l.price.sale_price,
                    "condo_fee": l.price.condo_fee,
                    "iptu": l.price.iptu,
                    "area_m2": l.area_m2,
                    "bedrooms": l.bedrooms,
                    "bathrooms": l.bathrooms,
                    "parking_spaces": l.parking_spaces,
                    "latitude": l.coordinates.latitude if l.coordinates else None,
                    "longitude": l.coordinates.longitude if l.coordinates else None,
                    "description": l.description,
                    "amenities": l.amenities,
                    "building_amenities": l.building_amenities,
                    "unit_amenities": l.unit_amenities,
                    "floor_number": l.floor_number,
                    "total_floors": l.total_floors,
                    "year_built": l.year_built,
                    "furnished": l.furnished.value,
                    "pet_friendly": l.pet_friendly,
                    "images": l.images,
                    "content_hash": str(l.content_hash) if l.content_hash else "",
                }
                for l in listings
            ]

            if "json" in formats:
                json_path = output_dir / "listings.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                logger.info("Exported %d listings to %s", len(records), json_path)

            if "csv" in formats:
                csv_path = output_dir / "listings.csv"
                flat_records = []
                for rec in records:
                    flat = {**rec}
                    flat["amenities"] = json.dumps(flat["amenities"])
                    flat["building_amenities"] = json.dumps(flat["building_amenities"])
                    flat["unit_amenities"] = json.dumps(flat["unit_amenities"])
                    flat["images"] = json.dumps(flat["images"])
                    flat_records.append(flat)
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=flat_records[0].keys())
                    writer.writeheader()
                    writer.writerows(flat_records)
                logger.info("Exported %d listings to %s", len(records), csv_path)

            result.items_created = len(records)

        except Exception as exc:
            result.status = StepStatus.FAILED
            result.errors.append(ErrorInfo.from_exception(exc, ErrorCategory.UNKNOWN))
            logger.exception("ExportStep failed")

        return result
