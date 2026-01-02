from encodings.punycode import digits
import os
import json
import re
from datetime import datetime, timezone

from exif_service import (
    extract_xmp_metadata,
    get_los_fields,
    extract_relative_altitude,
    run_exiftool,
)

from utils_service import (
    get_float,
    to_float_rounded,
    to_float,
)

from geo_math_service import (
    calculate_resolution,
    normalize_azimuth,
    normalize_pitch,
)


# ------------------------------------------------------------
# Sensor classification by FILE NAME (_T / _Z / _W)
# ------------------------------------------------------------

def classify_sensor_type_from_name(filename: str) -> str:
    """
    Classify sensor type by filename suffix:
      *_T -> IR
      *_Z -> EO
      *_W -> VIS
    Default -> VIS
    """
    base = os.path.splitext(os.path.basename(filename))[0]
    match = re.search(r"_([A-Za-z])$", base)

    if not match:
        return "VIS"

    suffix = match.group(1).upper()

    if suffix == "T":
        return "IR"
    if suffix == "Z":
        return "EO"
    if suffix == "W":
        return "VIS"

    return "VIS"


# ------------------------------------------------------------
# Imaging time (UTC)
# ------------------------------------------------------------

def _build_imaging_time_utc(tags) -> str:
    try:
        gps_date_tag = tags.get("GPS GPSDate") or tags.get("GPS GPSDateStamp")
        gps_time_tag = tags.get("GPS GPSTimeStamp")

        if gps_date_tag and gps_time_tag and hasattr(gps_time_tag, "values"):
            year, month, day = map(int, str(gps_date_tag).split(":"))
            vals = gps_time_tag.values

            def _r(r): return float(r.num) / float(r.den)

            hour = int(_r(vals[0]))
            minute = int(_r(vals[1]))
            sec = _r(vals[2])
            second = int(sec)
            micro = int(round((sec - second) * 1_000_000))

            dt = datetime(
                year, month, day,
                hour, minute, second, micro,
                tzinfo=timezone.utc
            )
            return dt.isoformat().replace("+00:00", "Z")
    except Exception:
        pass

    try:
        raw = str(tags.get("EXIF DateTimeOriginal", ""))
        if raw:
            dt = datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
            return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass

    return ""


# ------------------------------------------------------------
# Build sections
# ------------------------------------------------------------

def build_basic_data(filename, tags, full_path):
    width = int(str(tags.get("EXIF ExifImageWidth", "0")))
    height = int(str(tags.get("EXIF ExifImageLength", "0")))

    imaging_time = _build_imaging_time_utc(tags)
    sensor_type = classify_sensor_type_from_name(filename)

    try:
        xmp_data = extract_xmp_metadata(full_path)
        if xmp_data is not None:
            xmp_root, ns = xmp_data
            desc = xmp_root.find(".//rdf:Description", ns)
            if desc is not None:
                val = desc.attrib.get(f"{{{ns['drone-dji']}}}RelativeAltitude")
                if val is not None:
                    altitude = float(val.lstrip("+"))
                    resolution = calculate_resolution(
                        width, height, 82.9, 52.5, altitude
                    )
                else:
                    resolution = 0.0
            else:
                resolution = 0.0
        else:
            resolution = 0.0
    except Exception:
        resolution = 0.0

    return {
        "id": os.path.splitext(filename)[0],
        "sensorName": "Modash",
        "sensorType": sensor_type,   # ✅ IR / EO / VIS לפי השם
        "imageFile": filename,
        "imagingTime": imaging_time,
        "prevImagingTime": None,
        "nextImagingTime": None,
        "height": height,
        "width": width,
        "resolution": resolution,
    }


def build_camera_data(tags):
    width = int(str(tags.get("EXIF ExifImageWidth", "0")))
    height = int(str(tags.get("EXIF ExifImageLength", "0")))

    try:
        focal_35mm = float(str(tags.get("EXIF FocalLengthIn35mmFilm", "0")))
        fx = (focal_35mm / 36.0) * width
        fy = (focal_35mm / 24.0) * height
    except Exception:
        fx, fy = 0.0, 0.0

    return {
        "focalLengthInPixelsX": round(fx, 4),
        "focalLengthInPixelsY": round(fy, 4),
        "foVX": 82.9,
        "foVY": 52.5,
        "cx": width / 2.0,
        "cy": height / 2.0,
        "k1": 0.0,
        "k2": 0.0,
        "k3": 0.0,
        "p1": 0.0,
        "p2": 0.0,
        "alpha": 0.0,
        "cameraMake": str(tags.get("Image Make", "")),
        "cameraModel": str(tags.get("Image Model", "")),
        "focalId": None,
        "exposureDuration": None,
        "fnumber": None,
    }


def build_camera_position(tags, lat, lon, image_path):
    los_fields = get_los_fields(image_path)
    relative_alt = extract_relative_altitude(image_path)

    return {
        "gpsLatitude": lat,
        "gpsLongitude": lon,
        "gpsAltitude": get_float("GPS GPSAltitude", tags, 0.0),
        "relativeAltitude": relative_alt,
        "losAzimuth": round(normalize_azimuth(los_fields["losAzimuth"]), 4),
        "losPitch": round(normalize_pitch(los_fields["losPitch"]), 4),
        "losRoll": round(los_fields["losRoll"], 4),
    }


def build_platform_data(tags, drone_type, image_path):
    true_course = get_float("GPS GPSTrack", tags, 0.0)

    msl_alt = get_float("GPS GPSAltitude", tags, 0.0)
    yaw = pitch = roll = 0.0

    try:
        cp = run_exiftool([
            "-n", "-json",
            "-GPSAltitude", "-GPSAltitudeRef", "-AbsoluteAltitude",
            "-FlightYawDegree", "-FlightPitchDegree", "-FlightRollDegree",
            image_path,
        ])
        data = json.loads(cp.stdout)[0] if cp.stdout else {}

        gps_alt = to_float(data.get("GPSAltitude"))
        gps_alt_ref = to_float(data.get("GPSAltitudeRef"))
        abs_alt = to_float(data.get("AbsoluteAltitude"))

        if gps_alt is not None and (gps_alt_ref is None or int(gps_alt_ref) == 0):
            msl_alt = gps_alt
        elif abs_alt is not None:
            msl_alt = abs_alt

        yaw = normalize_azimuth(to_float_rounded(data.get("FlightYawDegree"), 4) or 0.0)
        pitch = normalize_pitch(to_float_rounded(data.get("FlightPitchDegree"), 4) or 0.0)
        roll = to_float_rounded(data.get("FlightRollDegree"), 4) or 0.0
    except Exception:
        pass

    return {
        "platformName": drone_type,
        "platformId": None,
        "trueCourse": true_course,
        "groundSpeed": 0.01,
        "mslAltitude": msl_alt,
        "platformYaw": yaw,
        "platformPitch": pitch,
        "platformRoll": roll,
    }


def build_operational_data():
    return {
        "missionNumber": None,
        "operationUnit": "Padam",
    }


def build_sensor_specific_data():
    return {
        "state": "0",
        "sixDofSource": None,
        "groundRef": None,
    }


# ------------------------------------------------------------
# Final JSON
# ------------------------------------------------------------

def build_json_structure(filename, tags, lat, lon, full_path, drone_type):
    return {
        "BasicData": build_basic_data(filename, tags, full_path),
        "CameraData": build_camera_data(tags),
        "CameraPosition": build_camera_position(tags, lat, lon, full_path),
        "PlatformData": build_platform_data(tags, drone_type, full_path),
        "Operational": build_operational_data(),
        "SensorSpecificData": build_sensor_specific_data(),
    }
