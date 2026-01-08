"""
Unit tests for utility services.
Tests helper functions and utilities.
"""
import pytest

from services.utils_service import get_float, to_float, to_float_rounded


class TestGetFloat:
    """Test get_float function"""

    def test_get_float_valid_value(self):
        """Test getting float from valid tags"""
        tags = {"altitude": "100.5"}
        result = get_float("altitude", tags)
        assert result == 100.5

    def test_get_float_missing_key(self):
        """Test get_float with missing key returns default"""
        tags = {"altitude": "100.5"}
        result = get_float("longitude", tags)
        assert result == 0.0

    def test_get_float_custom_default(self):
        """Test get_float with custom default"""
        tags = {}
        result = get_float("altitude", tags, default=-1.0)
        assert result == -1.0

    def test_get_float_invalid_value(self):
        """Test get_float with invalid value returns default"""
        tags = {"altitude": "invalid"}
        result = get_float("altitude", tags, default=0.0)
        assert result == 0.0

    def test_get_float_string_conversion(self):
        """Test get_float converts string to float"""
        tags = {"altitude": "42"}
        result = get_float("altitude", tags)
        assert result == 42.0
        assert isinstance(result, float)


class TestToFloatRounded:
    """Test to_float_rounded function"""

    def test_round_to_default_digits(self):
        """Test rounding to default 4 digits"""
        result = to_float_rounded(3.14159265)
        assert result == 3.1416

    def test_round_to_custom_digits(self):
        """Test rounding to custom digits"""
        result = to_float_rounded(3.14159265, digits=2)
        assert result == 3.14

    def test_round_to_zero_digits(self):
        """Test rounding to 0 digits (integer)"""
        result = to_float_rounded(3.7, digits=0)
        assert result == 4.0

    def test_invalid_input_returns_zero(self):
        """Test invalid input returns 0.0"""
        result = to_float_rounded("invalid")
        assert result == 0.0

    def test_none_input_returns_zero(self):
        """Test None input returns 0.0"""
        result = to_float_rounded(None)
        assert result == 0.0


class TestToFloat:
    """Test to_float function"""

    def test_convert_string_to_float(self):
        """Test converting string to float"""
        result = to_float("123.45")
        assert result == 123.45

    def test_convert_integer_to_float(self):
        """Test converting integer to float"""
        result = to_float(123)
        assert result == 123.0

    def test_remove_plus_sign(self):
        """Test removing plus sign from string"""
        result = to_float("+123.45")
        assert result == 123.45

    def test_strip_whitespace(self):
        """Test stripping whitespace"""
        result = to_float("  123.45  ")
        assert result == 123.45

    def test_invalid_string_returns_none(self):
        """Test invalid string returns None"""
        result = to_float("not_a_number")
        assert result is None

    def test_empty_string_returns_none(self):
        """Test empty string returns None"""
        result = to_float("")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
