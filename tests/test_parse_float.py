import pytest
from scraper import _parse_float


class TestParseFloatBasic:
    def test_simple_decimal_comma(self):
        assert _parse_float("0,1774") == pytest.approx(0.1774)

    def test_simple_decimal_dot(self):
        assert _parse_float("0.1774") == pytest.approx(0.1774)

    def test_integer_value(self):
        assert _parse_float("165") == pytest.approx(165.0)

    def test_standard_price(self):
        assert _parse_float("177,36") == pytest.approx(177.36)

    def test_none_on_garbage(self):
        assert _parse_float("N/A") is None

    def test_none_on_empty(self):
        assert _parse_float("") is None

    def test_nbsp_stripped(self):
        assert _parse_float("165,36\xa0") == pytest.approx(165.36)


class TestParseFloatThousandSeparator:

    def test_thousand_dot_with_decimal_comma(self):
        assert _parse_float("1.048,92") == pytest.approx(1048.92)

    def test_thousand_dot_no_decimal(self):
        result = _parse_float("1.048")
        assert result is not None

    def test_large_abonnement_ilek(self):
        assert _parse_float("1.048,92") == pytest.approx(1048.92)

    def test_large_abonnement_ilek_hphc(self):
        assert _parse_float("1.048,08") == pytest.approx(1048.08)

    def test_space_as_thousand_separator(self):
        assert _parse_float("1 048,92") == pytest.approx(1048.92)

    def test_nbsp_as_thousand_separator(self):
        assert _parse_float("1\xa0048,92") == pytest.approx(1048.92)

