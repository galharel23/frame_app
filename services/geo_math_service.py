import math


def normalize_azimuth(a):
    """Normalize azimuth/yaw to 0–360 degrees."""
    if a is None:
        return 0.0
    a = float(a)
    if a < 0:
        return a + 360.0
    if a >= 360.0:
        return a % 360.0
    return a


def normalize_pitch(p):
    """Normalize pitch to -90..90 and fix wrap-around (0..360 cases)."""
    if p is None:
        return 0.0

    p = float(p)
    # 1. Convert to range -180..+180
    p = ((p + 180.0) % 360.0) - 180.0

    # 2. Clamp to DJI valid range
    if p < -90.0:
        return -90.0
    if p > 90.0:
        return 90.0

    return p


def calculate_resolution(width, height, fov_x, fov_y, altitude):
    """
    Calculate resolution in meters per pixel
    """
    fov_x_rad = math.radians(fov_x)
    fov_y_rad = math.radians(fov_y)
    ground_width = 2 * altitude * math.tan(fov_x_rad / 2)
    ground_height = 2 * altitude * math.tan(fov_y_rad / 2)
    resolution_x = ground_width / width if width else 0
    resolution_y = ground_height / height if height else 0
    return (
        round((resolution_x + resolution_y) / 2, 5)
        if (resolution_x and resolution_y)
        else 0.0
    )
