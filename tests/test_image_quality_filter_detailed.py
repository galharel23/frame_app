"""Tests for image_quality_filter module."""

import math
import pytest
from image_quality_filter import (
    FilterConfig,
    ImageMetrics,
    calculate_distance_meters,
    classify_image_quality,
    FilterResult,
)


class TestCalculateDistance:
    """Test Haversine distance calculation."""
    
    def test_same_location(self):
        """Same coordinates should result in 0 distance."""
        distance = calculate_distance_meters(0, 0, 0, 0)
        assert abs(distance) < 0.01
    
    def test_known_distance(self):
        """Test with known distance between two cities."""
        # Tel Aviv to Jerusalem (approximate)
        tel_aviv_lat, tel_aviv_lon = 32.0853, 34.7818
        jerusalem_lat, jerusalem_lon = 31.7683, 35.2137
        
        distance = calculate_distance_meters(tel_aviv_lat, tel_aviv_lon, 
                                            jerusalem_lat, jerusalem_lon)
        # Distance should be approximately 60 km
        assert 55000 < distance < 65000
    
    def test_symmetric_distance(self):
        """Distance A->B should equal B->A."""
        lat1, lon1 = 32.0853, 34.7818
        lat2, lon2 = 31.7683, 35.2137
        
        dist_ab = calculate_distance_meters(lat1, lon1, lat2, lon2)
        dist_ba = calculate_distance_meters(lat2, lon2, lat1, lon1)
        
        assert abs(dist_ab - dist_ba) < 0.01


class TestFilterConfig:
    """Test FilterConfig dataclass."""
    
    def test_default_values(self):
        """Test default FilterConfig values."""
        config = FilterConfig()
        assert config.min_distance_meters == 200.0
        assert config.max_speed_mps == 5.0
        assert config.min_blur_score == 500.0
        assert config.enabled is True
    
    def test_from_dict(self):
        """Test creating FilterConfig from dictionary."""
        data = {
            "min_distance_meters": 300.0,
            "max_speed_mps": 3.0,
            "min_blur_score": 400.0,
            "enabled": False,
        }
        config = FilterConfig.from_dict(data)
        assert config.min_distance_meters == 300.0
        assert config.max_speed_mps == 3.0
        assert config.min_blur_score == 400.0
        assert config.enabled is False
        # Other values should use defaults
        assert config.max_iso == 1600


class TestClassifyImageQuality:
    """Test image quality classification."""
    
    def test_good_image(self):
        """Image with all metrics passing should be classified as GOOD."""
        metrics = ImageMetrics(
            width=3840,
            height=2160,
            speed_mps=1.5,
            distance_meters=300.0,
            blur_score=600.0,
            brightness=150.0,
            iso=400,
            digital_zoom=1.0,
        )
        config = FilterConfig()
        
        result = classify_image_quality("test.jpg", metrics, config)
        
        assert result.status == "GOOD"
        assert result.score == 100
        assert len(result.reasons) == 0
    
    def test_bad_width(self):
        """Image with width below minimum should be rejected."""
        metrics = ImageMetrics(
            width=2000,  # Below minimum of 3000
            height=2160,
            speed_mps=1.5,
            blur_score=600.0,
            brightness=150.0,
        )
        config = FilterConfig()
        
        result = classify_image_quality("test.jpg", metrics, config)
        
        assert result.status == "BAD"
        assert any("width" in reason for reason in result.reasons)
    
    def test_bad_blur(self):
        """Image with low blur score should be rejected."""
        metrics = ImageMetrics(
            width=3840,
            height=2160,
            speed_mps=1.5,
            blur_score=300.0,  # Below minimum of 500.0
            brightness=150.0,
        )
        config = FilterConfig()
        
        result = classify_image_quality("test.jpg", metrics, config)
        
        assert result.status == "BAD"
        assert any("blur" in reason.lower() for reason in result.reasons)
    
    def test_bad_brightness_too_dark(self):
        """Image that's too dark should be rejected."""
        metrics = ImageMetrics(
            width=3840,
            height=2160,
            speed_mps=1.5,
            blur_score=600.0,
            brightness=10.0,  # Below minimum of 20.0
        )
        config = FilterConfig()
        
        result = classify_image_quality("test.jpg", metrics, config)
        
        assert result.status == "BAD"
        assert any("dark" in reason.lower() for reason in result.reasons)
    
    def test_bad_brightness_too_bright(self):
        """Image that's too bright should be rejected."""
        metrics = ImageMetrics(
            width=3840,
            height=2160,
            speed_mps=1.5,
            blur_score=600.0,
            brightness=250.0,  # Above maximum of 240.0
        )
        config = FilterConfig()
        
        result = classify_image_quality("test.jpg", metrics, config)
        
        assert result.status == "BAD"
        assert any("bright" in reason.lower() for reason in result.reasons)
    
    def test_missing_optional_metrics(self):
        """Missing optional metrics should not cause rejection."""
        metrics = ImageMetrics(
            width=3840,
            height=2160,
            speed_mps=1.5,
            blur_score=600.0,
            brightness=150.0,
            # iso and digital_zoom are None
        )
        config = FilterConfig()
        
        result = classify_image_quality("test.jpg", metrics, config)
        
        assert result.status == "GOOD"
        assert len(result.reasons) == 0
    
    def test_multiple_failures(self):
        """Multiple metric failures should list all reasons."""
        metrics = ImageMetrics(
            width=2000,  # Too small
            height=1500,  # Too small
            speed_mps=8.0,  # Too fast
            blur_score=200.0,  # Too blurry
            brightness=250.0,  # Too bright
            iso=3200,  # Too high
        )
        config = FilterConfig()
        
        result = classify_image_quality("test.jpg", metrics, config)
        
        assert result.status == "BAD"
        assert len(result.reasons) > 3
        assert result.score < 100
    
    def test_score_calculation(self):
        """Test score decreases with more failures."""
        config = FilterConfig()
        
        # One failure
        metrics_one = ImageMetrics(width=2000)  # Only width is bad
        result_one = classify_image_quality("test.jpg", metrics_one, config)
        
        # Multiple failures
        metrics_multi = ImageMetrics(
            width=2000,
            height=1500,
            speed_mps=8.0,
            blur_score=200.0,
        )
        result_multi = classify_image_quality("test.jpg", metrics_multi, config)
        
        assert result_multi.score < result_one.score
