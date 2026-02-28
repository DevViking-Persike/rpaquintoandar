from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.enums import ProcessingStatus
from rpaquintoandar.domain.value_objects import ContentHash


def make_listing(**kwargs):
    defaults = {
        "source_id": "test-123",
        "source_url": "https://www.quintoandar.com.br/imovel/test-123",
    }
    defaults.update(kwargs)
    return Listing(**defaults)


class TestListing:
    def test_default_status_is_pending(self):
        listing = make_listing()
        assert listing.status == ProcessingStatus.PENDING

    def test_mark_enriched(self):
        listing = make_listing()
        content_hash = ContentHash.from_text("some content")

        listing.mark_enriched(content_hash)

        assert listing.status == ProcessingStatus.ENRICHED
        assert listing.content_hash == content_hash

    def test_mark_failed(self):
        listing = make_listing()
        listing.mark_failed()
        assert listing.status == ProcessingStatus.FAILED

    def test_mark_duplicate(self):
        listing = make_listing()
        listing.mark_duplicate()
        assert listing.status == ProcessingStatus.DUPLICATE
