from rpaquintoandar.domain.value_objects import ContentHash


class TestContentHash:
    def test_from_text_produces_sha256(self):
        content_hash = ContentHash.from_text("hello world")
        assert len(content_hash.value) == 64

    def test_same_text_produces_same_hash(self):
        h1 = ContentHash.from_text("test content")
        h2 = ContentHash.from_text("test content")
        assert h1 == h2

    def test_different_text_produces_different_hash(self):
        h1 = ContentHash.from_text("content A")
        h2 = ContentHash.from_text("content B")
        assert h1 != h2

    def test_str_returns_value(self):
        content_hash = ContentHash.from_text("test")
        assert str(content_hash) == content_hash.value

    def test_frozen(self):
        content_hash = ContentHash.from_text("test")
        try:
            content_hash.value = "changed"  # type: ignore[misc]
            assert False, "Should raise"
        except AttributeError:
            pass
