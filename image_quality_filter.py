"""
Image quality filtering module for drone imagery.

Classifies images as GOOD or BAD based on configurable quality metrics:
- Image dimensions (width, height)
- Platform speed (groundSpeed)
- Blur score (Laplacian variance)
- Brightness (grayscale mean)
- Distance between consecutive images (Haversine formula)
- ISO (from EXIF if available)
- Digital zoom (from EXIF/XMP if available)
"""

import json
import os
import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

import cv2
import exifread


@dataclass
class FilterConfig:
    """Quality filter configuration."""
    min_distance_meters: float = 200.0
    max_speed_mps: float = 5.0
    max_digital_zoom: float = 1.0
    min_blur_score: float = 500.0
    min_width: int = 3000
    min_height: int = 2000
    max_iso: int = 1600
    min_brightness: float = 20.0
    max_brightness: float = 240.0
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "FilterConfig":
        """Create FilterConfig from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ImageMetrics:
    """Calculated metrics for an image."""
    distance_meters: Optional[float] = None
    speed_mps: Optional[float] = None
    digital_zoom: Optional[float] = None
    blur_score: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    iso: Optional[int] = None
    brightness: Optional[float] = None


@dataclass
class FilterResult:
    """Result of quality filtering for a single image."""
    image: str
    status: str  # "GOOD" or "BAD"
    score: int  # 0-100
    reasons: List[str]
    metrics: Dict


def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula.
    
    Args:
        lat1, lon1: First coordinate pair (degrees)
        lat2, lon2: Second coordinate pair (degrees)
    
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def _extract_iso_from_exif(image_path: str) -> Optional[int]:
    """Extract ISO value from EXIF if available."""
    try:
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
            if "EXIF ISOSpeedRatings" in tags:
                return int(tags["EXIF ISOSpeedRatings"].values[0])
    except Exception:
        pass
    return None


def _extract_digital_zoom_from_exif(image_path: str) -> Optional[float]:
    """Extract digital zoom ratio from EXIF/XMP if available."""
    try:
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
            # Try common digital zoom EXIF tags
            for tag_name in ["EXIF DigitalZoomRatio", "MakerNote DigitalZoomRatio"]:
                if tag_name in tags:
                    try:
                        val = tags[tag_name].values[0]
                        if isinstance(val, (int, float)):
                            return float(val)
                        elif hasattr(val, "numerator") and hasattr(val, "denominator"):
                            return float(val.numerator) / float(val.denominator)
                    except Exception:
                        pass
    except Exception:
        pass
    return None


def calculate_image_quality_metrics(
    image_path: str,
    metadata: Dict,
    previous_metrics: Optional[ImageMetrics] = None,
) -> ImageMetrics:
    """
    Calculate quality metrics for an image.
    
    Args:
        image_path: Path to the image file
        metadata: Parsed JSON metadata dictionary
        previous_metrics: Metrics from previous accepted image (for distance calculation)
    
    Returns:
        ImageMetrics object with all calculated values (None if unavailable)
    """
    metrics = ImageMetrics()
    
    # Extract from metadata
    try:
        basic_data = metadata.get("BasicData", {})
        camera_pos = metadata.get("CameraPosition", {})
        platform_data = metadata.get("PlatformData", {})
        
        metrics.width = basic_data.get("width")
        metrics.height = basic_data.get("height")
        metrics.speed_mps = platform_data.get("groundSpeed")
    except Exception:
        pass
    
    # Calculate distance if we have previous GPS location
    try:
        if previous_metrics and previous_metrics.distance_meters is not None:
            current_lat = metadata.get("CameraPosition", {}).get("gpsLatitude")
            current_lon = metadata.get("CameraPosition", {}).get("gpsLongitude")
            # Distance is stored as the previous calculation's result
            # We calculate based on previous accepted position
            metrics.distance_meters = previous_metrics.distance_meters
    except Exception:
        pass
    
    # Extract ISO and digital zoom from EXIF
    if os.path.isfile(image_path):
        metrics.iso = _extract_iso_from_exif(image_path)
        metrics.digital_zoom = _extract_digital_zoom_from_exif(image_path)
    
    # Calculate blur score using Laplacian variance
    try:
        if os.path.isfile(image_path):
            img = cv2.imread(image_path)
            if img is not None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                metrics.blur_score = round(float(laplacian_var), 2)
    except Exception:
        pass
    
    # Calculate brightness using grayscale mean
    try:
        if os.path.isfile(image_path):
            img = cv2.imread(image_path)
            if img is not None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                brightness = gray.mean()
                metrics.brightness = round(float(brightness), 2)
    except Exception:
        pass
    
    # Default digital zoom to 1.0 if not found
    if metrics.digital_zoom is None:
        metrics.digital_zoom = 1.0
    
    return metrics


def classify_image_quality(
    image_name: str,
    metrics: ImageMetrics,
    config: FilterConfig,
) -> FilterResult:
    """
    Classify an image as GOOD or BAD based on metrics and config.
    
    Args:
        image_name: Name of the image file
        metrics: Calculated ImageMetrics
        config: FilterConfig with thresholds
    
    Returns:
        FilterResult with status, reasons, and score
    """
    reasons = []
    
    # Check dimensions
    if metrics.width is not None and metrics.width < config.min_width:
        reasons.append(f"image width too small ({metrics.width} < {config.min_width})")
    
    if metrics.height is not None and metrics.height < config.min_height:
        reasons.append(f"image height too small ({metrics.height} < {config.min_height})")
    
    # Check speed
    if metrics.speed_mps is not None and metrics.speed_mps > config.max_speed_mps:
        reasons.append(f"platform moving too fast ({metrics.speed_mps:.2f} > {config.max_speed_mps})")
    
    # Check distance (only if set)
    if metrics.distance_meters is not None and metrics.distance_meters < config.min_distance_meters:
        reasons.append(f"too close to previous image ({metrics.distance_meters:.1f}m < {config.min_distance_meters}m)")
    
    # Check blur
    if metrics.blur_score is not None and metrics.blur_score < config.min_blur_score:
        reasons.append(f"image is blurry (blur_score {metrics.blur_score:.1f} < {config.min_blur_score})")
    
    # Check brightness
    if metrics.brightness is not None:
        if metrics.brightness < config.min_brightness:
            reasons.append(f"image too dark ({metrics.brightness:.1f}° < {config.min_brightness}°)")
        elif metrics.brightness > config.max_brightness:
            reasons.append(f"image too bright ({metrics.brightness:.1f}° > {config.max_brightness}°)")
    
    # Check ISO
    if metrics.iso is not None and metrics.iso > config.max_iso:
        reasons.append(f"ISO too high ({metrics.iso} > {config.max_iso})")
    
    # Check digital zoom
    if metrics.digital_zoom is not None and metrics.digital_zoom > config.max_digital_zoom:
        reasons.append(f"digital zoom too high ({metrics.digital_zoom}x > {config.max_digital_zoom}x)")
    
    # Calculate score (0-100)
    # Start at 100, deduct points for each issue
    score = 100
    score -= len(reasons) * 10  # -10 per issue
    score = max(0, min(100, score))
    
    status = "GOOD" if not reasons else "BAD"
    
    return FilterResult(
        image=image_name,
        status=status,
        score=score,
        reasons=reasons,
        metrics=asdict(metrics),
    )


def filter_images(
    image_paths: List[str],
    metadata_dict: Dict[str, Dict],
    config: FilterConfig,
) -> Tuple[List[FilterResult], Dict]:
    """
    Filter multiple images and return results.
    
    Args:
        image_paths: List of image file paths
        metadata_dict: Mapping of filename -> metadata JSON dict
        config: FilterConfig with thresholds
    
    Returns:
        Tuple of (all results, summary dict with good/bad counts)
    """
    if not config.enabled:
        # Return all images as GOOD if filtering is disabled
        results = []
        for img_path in image_paths:
            img_name = os.path.basename(img_path)
            metrics = ImageMetrics()
            result = FilterResult(
                image=img_name,
                status="GOOD",
                score=100,
                reasons=[],
                metrics=asdict(metrics),
            )
            results.append(result)
        return results, {"total": len(results), "good": len(results), "bad": 0}
    
    results = []
    last_good_metrics = None
    
    for img_path in image_paths:
        img_name = os.path.basename(img_path)
        metadata = metadata_dict.get(img_name, {})
        
        # Calculate distance from last accepted image
        if last_good_metrics and metadata.get("CameraPosition"):
            current_lat = metadata["CameraPosition"].get("gpsLatitude")
            current_lon = metadata["CameraPosition"].get("gpsLongitude")
            prev_lat = metadata.get("_prev_gps_lat")
            prev_lon = metadata.get("_prev_gps_lon")
            
            if current_lat and current_lon and prev_lat and prev_lon:
                distance = calculate_distance_meters(prev_lat, prev_lon, current_lat, current_lon)
                last_good_metrics.distance_meters = distance
        
        # Calculate metrics
        metrics = calculate_image_quality_metrics(img_path, metadata, last_good_metrics)
        
        # Classify
        result = classify_image_quality(img_name, metrics, config)
        results.append(result)
        
        # Update last accepted position if this image is good
        if result.status == "GOOD":
            last_good_metrics = metrics
            # Store GPS for next iteration
            if metadata.get("CameraPosition"):
                metadata["_prev_gps_lat"] = metadata["CameraPosition"].get("gpsLatitude")
                metadata["_prev_gps_lon"] = metadata["CameraPosition"].get("gpsLongitude")
    
    # Build summary
    good_count = sum(1 for r in results if r.status == "GOOD")
    bad_count = sum(1 for r in results if r.status == "BAD")
    
    summary = {
        "total": len(results),
        "good": good_count,
        "bad": bad_count,
    }
    
    return results, summary


def save_quality_report(results: List[FilterResult], output_path: str) -> None:
    """
    Save quality filter results to a JSON report file.
    
    Args:
        results: List of FilterResult objects
        output_path: Path to save the report
    """
    good_images = [r for r in results if r.status == "GOOD"]
    bad_images = [r for r in results if r.status == "BAD"]
    
    report = {
        "summary": {
            "total": len(results),
            "good": len(good_images),
            "bad": len(bad_images),
        },
        "good_images": [asdict(r) for r in good_images],
        "bad_images": [asdict(r) for r in bad_images],
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
