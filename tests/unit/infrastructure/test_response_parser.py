from rpaquintoandar.infrastructure.api.response_parser import parse_search_hit, parse_search_response


class TestResponseParser:
    def test_parse_search_hit_basic(self):
        source = {
            "id": "abc-123",
            "type": "APARTMENT",
            "neighbourhood": "Vila Mariana",
            "city": "São Paulo",
            "state": "SP",
            "salePrice": 500000,
            "area": 65.0,
            "bedrooms": 2,
            "bathrooms": 1,
            "parkingSpaces": 1,
        }
        listing = parse_search_hit(source)

        assert listing.source_id == "abc-123"
        assert listing.address.neighborhood == "Vila Mariana"
        assert listing.price.sale_price == 500000.0
        assert listing.area_m2 == 65.0
        assert listing.bedrooms == 2

    def test_parse_search_hit_missing_fields(self):
        source = {"id": "xyz-456"}
        listing = parse_search_hit(source)

        assert listing.source_id == "xyz-456"
        assert listing.price.sale_price == 0.0
        assert listing.bedrooms == 0

    def test_parse_search_response(self):
        data = {
            "hits": {
                "total": {"value": 100},
                "hits": [
                    {"_source": {"id": "a1", "city": "SP"}},
                    {"_source": {"id": "a2", "city": "SP"}},
                ],
            }
        }
        listings, total = parse_search_response(data)

        assert total == 100
        assert len(listings) == 2
        assert listings[0].source_id == "a1"

    def test_parse_search_response_empty(self):
        data = {"hits": {"total": {"value": 0}, "hits": []}}
        listings, total = parse_search_response(data)

        assert total == 0
        assert len(listings) == 0
