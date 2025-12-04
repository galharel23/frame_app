import os
import json
from string import digits
import subprocess
import re
from xml.etree import ElementTree as ET
from pathlib import Path
from shutil import which

from utils_service import to_float_rounded

# -------------------------------
# ExifTool resolution & wrapper
# -------------------------------

def resolve_exiftool_path():
    """
    מחפש את exiftool.exe לפי הסדר:
    1) משתנה סביבה EXIFTOOL_PATH
    2) ב-PATH (which)
    3) נתיבים יחסיים נפוצים ליד הקובץ הזה
    """
    env_p = os.environ.get("EXIFTOOL_PATH")
    if env_p and os.path.exists(env_p):
        return env_p

    w = which("exiftool")
    if w and os.path.exists(w):
        return w

    here = Path(__file__).resolve().parent
    local_candidates = [
        here / "exiftool-13.30_64" / "exiftool.exe",
        here / "exiftool-13.32_64" / "exiftool.exe",
        here / "exiftool.exe",
    ]
    for c in local_candidates:
        if c.is_file():
            return str(c)

    return None

EXIFTOOL_PATH = resolve_exiftool_path()

def run_exiftool(args):
    """
    הרצה בטוחה של ExifTool (ללא shell=True).
    זורק חריגות אם אין EXIFTOOL או אם ההרצה נכשלה (check=True).
    """
    if not EXIFTOOL_PATH:
        raise FileNotFoundError(
            "ExifTool לא נמצא. עדכן את EXIFTOOL_PATH, הוסף ל-PATH, או ודא שהקובץ exiftool.exe קיים ליד הסקריפט."
        )
    cmd = [EXIFTOOL_PATH] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, check=True)

# -------------------------------
# EXIF / XMP helpers
# -------------------------------

def get_decimal_from_dms(dms, ref):
    """
    Convert DMS (Degrees, Minutes, Seconds) to Decimal Degrees
    dms: tuple of (degrees, minutes, seconds)
    ref: reference direction ('N', 'S', 'E', 'W')
    """
    try:
        degrees = float(dms[0].num) / float(dms[0].den)
        minutes = float(dms[1].num) / float(dms[1].den)
        seconds = float(dms[2].num) / float(dms[2].den)
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ["S", "W"]:
            decimal = -decimal
        return round(decimal, 6)
    except Exception as e:
        print(f"Error converting DMS to decimal: {e}")
        return None

def extract_gps_info_from_tags(tags):
    """
    Extract GPS coordinates from EXIF tags
    Returns coordinates in WGS84 Decimal Degrees format
    """
    try:
        required = [
            "GPS GPSLatitude",
            "GPS GPSLatitudeRef",
            "GPS GPSLongitude",
            "GPS GPSLongitudeRef",
        ]
        if not all(key in tags for key in required):
            print("Missing required GPS tags")
            return None, None

        lat = tags["GPS GPSLatitude"]
        lat_ref = tags["GPS GPSLatitudeRef"].printable
        lat_decimal = get_decimal_from_dms(lat.values, lat_ref)

        lon = tags["GPS GPSLongitude"]
        lon_ref = tags["GPS GPSLongitudeRef"].printable
        lon_decimal = get_decimal_from_dms(lon.values, lon_ref)

        if lat_decimal is None or lon_decimal is None:
            print("Failed to convert GPS coordinates")
            return None, None

        if not (-90 <= lat_decimal <= 90) or not (-180 <= lon_decimal <= 180):
            print(f"Invalid coordinate values: lat={lat_decimal}, lon={lon_decimal}")
            return None, None

        print(f"Extracted GPS coordinates: {lat_decimal}, {lon_decimal}")
        return lat_decimal, lon_decimal

    except Exception as e:
        print(f"Error extracting GPS info: {e}")
        return None, None

def extract_xmp_metadata(image_path):
    """Extract XMP metadata from image file"""
    try:
        with open(image_path, "rb") as f:
            jpeg_data = f.read()
            xmp_match = re.search(
                br"<x:xmpmeta[^>]*>.*?</x:xmpmeta>", jpeg_data, re.DOTALL
            )
            if not xmp_match:
                return None

            xmp_data = xmp_match.group(0).decode("utf-8", errors="ignore")
            xmp_root = ET.fromstring(xmp_data)
            ns = {
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "drone-dji": "http://www.dji.com/drone-dji/1.0/",
            }
            return xmp_root, ns
    except Exception as e:
        print(f"Error extracting XMP metadata: {str(e)}")
        return None

def get_los_fields(image_path):
    """
    מחלץ זוויות/כיוונים של הגימבל באמצעות ExifTool.
    מחזיר always dict עם מפתחות losAzimuth/losPitch/losRoll.
    """
    try:
        cp = run_exiftool(
            [
                "-n",
                "-json",
                "-GimbalYawDegree",
                "-GimbalPitchDegree",
                "-GimbalRollDegree",
                image_path,
            ]
        )
        data = json.loads(cp.stdout)[0] if cp.stdout else {}

        return {
            "losAzimuth": to_float_rounded(data.get("GimbalYawDegree"), digits = 4),
            "losPitch": to_float_rounded(data.get("GimbalPitchDegree"), digits = 4),
            "losRoll": to_float_rounded(data.get("GimbalRollDegree"), digits = 4),
        }
    except FileNotFoundError as e:
        print(f"Warning: ExifTool not found: {e}")
        return {"losAzimuth": 0.0, "losPitch": 0.0, "losRoll": 0.0}
    except subprocess.CalledProcessError as e:
        print(f"Warning: ExifTool failed: {e.stderr.strip() if e.stderr else e}")
        return {"losAzimuth": 0.0, "losPitch": 0.0, "losRoll": 0.0}
    except Exception as e:
        print(f"Warning: Could not extract LOS fields: {e}")
        return {"losAzimuth": 0.0, "losPitch": 0.0, "losRoll": 0.0}

def extract_relative_altitude(image_path):
    xmp_data = extract_xmp_metadata(image_path)
    if xmp_data is None:
        return 0.0
    xmp_root, ns = xmp_data
    desc = xmp_root.find(".//rdf:Description", ns)
    if desc is None:
        return 0.0
    val = desc.attrib.get(f"{{{ns['drone-dji']}}}RelativeAltitude")
    if val is None:
        return 0.0
    try:
        return float(val.lstrip("+"))
    except ValueError:
        return 0.0
