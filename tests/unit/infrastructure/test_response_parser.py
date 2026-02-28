from rpaquintoandar.infrastructure.api.response_parser import (
    parse_search_response,
    parse_ssr_house,
    parse_ssr_houses,
)


class TestResponseParser:
    def test_parse_ssr_house_basic(self):
        house = {
            "id": 893075840,
            "type": "Apartamento",
            "neighbourhood": "Vila Mariana",
            "salePrice": 500000,
            "area": 65,
            "bedrooms": 2,
            "bathrooms": 1,
            "parkingSpots": 1,
            "amenities": ["CHURRASQUEIRA", "PISCINA"],
        }
        listing = parse_ssr_house(house)

        assert listing.source_id == "893075840"
        assert listing.address.neighborhood == "Vila Mariana"
        assert listing.price.sale_price == 500000.0
        assert listing.area_m2 == 65.0
        assert listing.bedrooms == 2
        assert listing.parking_spaces == 1

    def test_parse_ssr_house_missing_fields(self):
        house = {"id": 123456}
        listing = parse_ssr_house(house)

        assert listing.source_id == "123456"
        assert listing.price.sale_price == 0.0
        assert listing.bedrooms == 0

    def test_parse_ssr_houses_dict(self):
        houses = {
            "111": {"id": 111, "type": "Casa", "salePrice": 800000},
            "222": {"id": 222, "type": "Apartamento", "salePrice": 400000},
            "nonNumericMeta": "some metadata string",
        }
        listings = parse_ssr_houses(houses)

        assert len(listings) == 2
        ids = {l.source_id for l in listings}
        assert "111" in ids
        assert "222" in ids

    def test_parse_ssr_house_with_condo_iptu(self):
        house = {
            "id": 999,
            "condoIptu": "R$ 800 + R$ 200",
        }
        listing = parse_ssr_house(house)

        assert listing.price.condo_fee == 800.0
        assert listing.price.iptu == 200.0

    def test_parse_search_response(self):
        data = {
            "hits": {
                "total": {"value": 100},
                "hits": [
                    {"_source": {"id": "a1", "neighbourhood": "SP"}},
                    {"_source": {"id": "a2", "neighbourhood": "SP"}},
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
