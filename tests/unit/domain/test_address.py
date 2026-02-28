from rpaquintoandar.domain.value_objects import Address


class TestAddress:
    def test_default_values(self):
        addr = Address()
        assert addr.street == ""
        assert addr.city == ""
        assert addr.state == ""

    def test_frozen(self):
        addr = Address(street="Rua X", city="São Paulo")
        try:
            addr.street = "Rua Y"  # type: ignore[misc]
            assert False, "Should raise"
        except AttributeError:
            pass

    def test_equality(self):
        a1 = Address(street="Rua A", city="SP")
        a2 = Address(street="Rua A", city="SP")
        assert a1 == a2
