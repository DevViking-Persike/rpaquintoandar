from rpaquintoandar.shared.hashing import normalize_text, sha256_hash


class TestHashing:
    def test_normalize_text_collapses_whitespace(self):
        assert normalize_text("hello   world") == "hello world"

    def test_normalize_text_strips(self):
        assert normalize_text("  hello  ") == "hello"

    def test_sha256_hash_returns_hex(self):
        result = sha256_hash("test")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_sha256_hash_deterministic(self):
        h1 = sha256_hash("content")
        h2 = sha256_hash("content")
        assert h1 == h2
