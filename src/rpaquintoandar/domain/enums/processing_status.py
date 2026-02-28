from enum import StrEnum


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    ENRICHED = "enriched"
    FAILED = "failed"
    DUPLICATE = "duplicate"
