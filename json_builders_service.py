from encodings.punycode import digits
import os
import json
from datetime import datetime

from exif_service import (
    extract_xmp_metadata,
    get_los_fields,
    extract_relative_altitude,
    run_exiftool,
)

from utils_service import get_float

from geo_math_service import (
    calculate_resolution,
    normalize_azimuth,
    normalize_pitch,
)

from utils_service import (
     get_float, 
     to_float_rounded,
     to_float,
    )


# Build each sector

def build_basic_data(filename, tags, full_path):
    width = int(str(tags.get("EXIF ExifImageWidth", "0")))
    height = int(str(tags.get("EXIF ExifImageLength", "0")))

    try:
        imaging_time = str(tags.get("EXIF DateTimeOriginal", ""))
        if imaging_time:
            dt = datetime.strptime(imaging_time, "%Y:%m:%d %H:%M:%S")
            imaging_time = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception as e:
        print(f"Warning: Could not format imaging time: {e}")
        imaging_time = ""

    try:
        print(f"Attempting to calculate resolution for: {filename}")
        print(f"Image dimensions: {width}x{height}")

        xmp_data = extract_xmp_metadata(full_path)
        if xmp_data is not None:
            print("Found XMP metadata section")
            xmp_root, ns = xmp_data
            desc = xmp_root.find(".//rdf:Description", ns)
            if desc is not None:
                print("Found XMP Description")
                val = desc.attrib.get(f"{{{ns['drone-dji']}}}RelativeAltitude")
                if val is not None:
                    print(f"Found RelativeAltitude: {val}")
                    altitude = float(val.lstrip("+"))
                    print(f"Using altitude: {altitude} meters")
                    resolution = calculate_resolution(width, height, 82.9, 52.5, altitude)
                    print(f"Calculated resolution: {resolution} meters/pixel")
                else:
                    print("RelativeAltitude not found in XMP")
                    resolution = 0.0
            else:
                print("XMP Description not found")
                resolution = 0.0
        else:
            print("XMP metadata section not found")
            resolution = 0.0
    except Exception as e:
        print(f"Error calculating resolution: {str(e)}")
        resolution = 0.0

    return {
        "id": os.path.splitext(filename)[0],
        "sensorName": "Modash",
        "sensorType": "VIS",
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
        "focalLengthInPixelsX": round(fx,4),
        "focalLengthInPixelsY": round(fy,4),
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
    def get_altitude(tag_name, default=0.0):
        val = tags.get(tag_name)
        try:
            if val and hasattr(val, "values"):
                ratio = val.values[0]
                return ratio.num / ratio.den
        except Exception:
            pass
        return default

    los_fields = get_los_fields(image_path)
    relative_alt = extract_relative_altitude(image_path)

    return {
        "gpsLatitude": lat,
        "gpsLongitude": lon,
        "gpsAltitude": get_altitude("GPS GPSAltitude", 0.0),
        "relativeAltitude": relative_alt,
        "losAzimuth": round(normalize_azimuth(los_fields["losAzimuth"]),4),
        "losPitch": round(normalize_pitch(los_fields["losPitch"]),4),
        "losRoll": round(los_fields["losRoll"],4),
    }

def build_platform_data(tags, drone_type, image_path):
    """
    ממלא 4 שדות מ-ExifTool:
      - mslAltitude: GPSAltitude (כש GPSAltitudeRef==0) אחרת AbsoluteAltitude
      - platformYaw/Pitch/Roll: FlightYaw/Pitch/RollDegree
    נשמרת הלוגיקה שלך ל-trueCourse וה-groundSpeed.
    """
    true_course = get_float("GPS GPSTrack", tags, 0.0)

    msl_alt = get_float("GPS GPSAltitude", tags, 0.0)
    yaw = 0.0
    pitch = 0.0
    roll = 0.0

    try:
        cp = run_exiftool(
            [
                "-n",
                "-json",
                "-GPSAltitude",
                "-GPSAltitudeRef",
                "-AbsoluteAltitude",
                "-FlightYawDegree",
                "-FlightPitchDegree",
                "-FlightRollDegree",
                image_path,
            ]
        )
        data = json.loads(cp.stdout)[0] if cp.stdout else {}


        

        gps_alt = to_float(data.get("GPSAltitude"))
        gps_alt_ref = to_float(data.get("GPSAltitudeRef"))
        abs_alt = to_float(data.get("AbsoluteAltitude"))
        
        yaw_exif = to_float_rounded(data.get("FlightYawDegree"), digits=4)
        pitch_exif = to_float_rounded(data.get("FlightPitchDegree"), digits=4)
        roll_exif = to_float_rounded(data.get("FlightRollDegree"), digits=4)

        if gps_alt is not None and (gps_alt_ref is None or int(gps_alt_ref) == 0):
            msl_alt = gps_alt
        elif abs_alt is not None:
            msl_alt = abs_alt

        if yaw_exif is not None:
            yaw = normalize_azimuth(yaw_exif)
        if pitch_exif is not None:
            pitch = normalize_pitch(pitch_exif)
        if roll_exif is not None:
            roll = roll_exif

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

# Build full Skeleton

def build_json_structure(filename, tags, lat, lon, full_path, drone_type):
    return {
        "BasicData": build_basic_data(filename, tags, full_path),
        "CameraData": build_camera_data(tags),
        "CameraPosition": build_camera_position(tags, lat, lon, full_path),
        "PlatformData": build_platform_data(tags, drone_type, full_path),
        "Operational": build_operational_data(),
        "SensorSpecificData": build_sensor_specific_data(),
    }
