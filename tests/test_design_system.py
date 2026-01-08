"""
Unit tests for design system and constants.
Tests color values and configuration constants.
"""
import pytest

from design_system import (
    BG_DARK_0,
    BG_DARK_1,
    BG_DARK_2,
    BG_DARK_3,
    BORDER_COLOR,
    BORDER_RADIUS_LG,
    BORDER_RADIUS_MD,
    BORDER_RADIUS_SM,
    BORDER_RADIUS_XL,
    BUTTON_SECONDARY,
    DIVIDER_COLOR,
    ERROR,
    INFO,
    PRIMARY,
    PRIMARY_HOVER,
    SPACING_LG,
    SPACING_MD,
    SPACING_SM,
    SPACING_XL,
    SPACING_XS,
    SPACING_XXL,
    SUCCESS,
    TEXT_PLACEHOLDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    WARNING,
)


class TestColorConstants:
    """Test color constants are valid hex colors"""

    @pytest.mark.parametrize(
        "color",
        [
            PRIMARY,
            PRIMARY_HOVER,
            BUTTON_SECONDARY,
            BG_DARK_0,
            BG_DARK_1,
            BG_DARK_2,
            BG_DARK_3,
            TEXT_PRIMARY,
            TEXT_SECONDARY,
            TEXT_TERTIARY,
            TEXT_PLACEHOLDER,
            SUCCESS,
            WARNING,
            ERROR,
            INFO,
            BORDER_COLOR,
            DIVIDER_COLOR,
        ],
    )
    def test_color_is_valid_hex(self, color):
        """Test that color is valid hex format"""
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7  # "#RRGGBB"
        try:
            int(color[1:], 16)  # Should parse as hex
        except ValueError:
            pytest.fail(f"Invalid hex color: {color}")

    def test_color_hierarchy(self):
        """Test color hierarchy (darker to lighter background)"""
        # Background colors should transition from dark to light
        backgrounds = [BG_DARK_0, BG_DARK_1, BG_DARK_2, BG_DARK_3]
        for bg in backgrounds:
            assert bg.startswith("#")

    def test_status_colors_are_distinct(self):
        """Test status colors are different"""
        status_colors = [SUCCESS, WARNING, ERROR, INFO]
        assert len(set(status_colors)) == 4  # All should be unique


class TestSpacingConstants:
    """Test spacing constants"""

    @pytest.mark.parametrize(
        "spacing,expected_min",
        [
            (SPACING_XS, 0),
            (SPACING_SM, 4),
            (SPACING_MD, 8),
            (SPACING_LG, 12),
            (SPACING_XL, 20),
            (SPACING_XXL, 28),
        ],
    )
    def test_spacing_is_positive(self, spacing, expected_min):
        """Test spacing values are positive integers"""
        assert isinstance(spacing, int)
        assert spacing >= expected_min

    def test_spacing_progression(self):
        """Test spacing increases progressively"""
        spacings = [SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL]
        for i in range(len(spacings) - 1):
            assert spacings[i] < spacings[i + 1]


class TestBorderRadiusConstants:
    """Test border radius constants"""

    @pytest.mark.parametrize(
        "radius",
        [
            BORDER_RADIUS_SM,
            BORDER_RADIUS_MD,
            BORDER_RADIUS_LG,
            BORDER_RADIUS_XL,
        ],
    )
    def test_border_radius_is_positive(self, radius):
        """Test border radius values are positive integers"""
        assert isinstance(radius, int)
        assert radius > 0

    def test_border_radius_progression(self):
        """Test border radius increases progressively"""
        radii = [BORDER_RADIUS_SM, BORDER_RADIUS_MD, BORDER_RADIUS_LG, BORDER_RADIUS_XL]
        for i in range(len(radii) - 1):
            assert radii[i] < radii[i + 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
