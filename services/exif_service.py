import os
import json
from string import digits
import subprocess
import re
from xml.etree import ElementTree as ET
from pathlib import Path
from shutil import which, copytree, ignore_patterns
import sys

from services.utils_service import to_float_rounded
from utils.logging_service import get_logger

logger = get_logger("exif_service")

# ======= SOLUTION: Extract exiftool_files to AppData on startup =======
def _ensure_exiftool_files_extracted():
    """
    Extract exiftool_files to AppData\Local\TekenFrame\exiftool_files 
    This ensures files are accessible even if PyInstaller bundling fails.
    """
    try:
        # Determine source location
        try:
            base_path = Path(sys._MEIPASS)  # PyInstaller
            logger.debug(f"PyInstaller bundle detected: {base_path}")
        except AttributeError:
            base_path = Path(__file__).resolve().parent.parent  # Regular execution
            logger.debug(f"Regular execution mode: {base_path}")
        
        source_dir = base_path / "exiftool-13.30_64" / "exiftool_files"
        
        # Destination in AppData
        appdata_local = Path.home() / "AppData" / "Local" / "TekenFrame"
        appdata_local.mkdir(parents=True, exist_ok=True)
        dest_dir = appdata_local / "exiftool_files"
        
        logger.debug(f"Source: {source_dir}")
        logger.debug(f"Destination: {dest_dir}")
        logger.debug(f"Source exists: {source_dir.exists()}")
        
        # Extract if not already there or if source is newer
        if not dest_dir.exists() and source_dir.exists():
            logger.info(f"Extracting exiftool_files to AppData: {dest_dir}")
            copytree(source_dir, dest_dir)
            logger.info("✓ Successfully extracted exiftool_files to AppData")
            return dest_dir
        elif dest_dir.exists():
            logger.debug(f"exiftool_files already exists at {dest_dir}")
            return dest_dir
        else:
            logger.warning(f"Source exiftool_files not found at {source_dir}")
            return None
    except Exception as e:
        logger.error(f"Failed to extract exiftool_files: {e}")
        return None

# Extract on module import
EXIFTOOL_FILES_EXTRACTED = _ensure_exiftool_files_extracted()

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
    Safe ExifTool execution (no shell=True).
    Uses perl.exe from AppData with exiftool.pl (most reliable for bundled deployments).
    Falls back to exiftool.exe if perl not available.
    Raises exceptions if ExifTool not found or execution failed (check=True).
    """
    if not EXIFTOOL_PATH:
        error_msg = "ExifTool not found. Update EXIFTOOL_PATH or ensure exiftool.exe exists."
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    # Set up environment with proper paths for ExifTool's Perl library
    env = os.environ.copy()
    exiftool_dir = os.path.dirname(EXIFTOOL_PATH)
    
    # Use extracted exiftool_files from AppData (most reliable)
    # PyInstaller doesn't always bundle subdirectories completely, so extraction ensures all files are present
    if EXIFTOOL_FILES_EXTRACTED and EXIFTOOL_FILES_EXTRACTED.exists():
        exiftool_files_dir = str(EXIFTOOL_FILES_EXTRACTED)
        logger.debug(f"Using extracted exiftool_files from AppData: {exiftool_files_dir}")
    else:
        # Fallback to bundled version (may be incomplete)
        exiftool_files_dir = os.path.join(exiftool_dir, 'exiftool_files')
        logger.warning(f"Extraction failed, using bundled exiftool_files: {exiftool_files_dir}")
    
    lib_dir = os.path.join(exiftool_files_dir, 'lib')
    
    logger.debug(f"ExifTool dir: {exiftool_dir}")
    logger.debug(f"ExifTool files dir: {exiftool_files_dir}")
    logger.debug(f"Lib dir: {lib_dir}")
    
    # Set PERL5LIB for Perl to find its libraries
    if os.path.isdir(lib_dir):
        env['PERL5LIB'] = lib_dir
        logger.debug(f"Set PERL5LIB to: {lib_dir}")
    else:
        logger.warning(f"lib directory not found at: {lib_dir}")
    
    # Add exiftool_files to PATH so perl5*.dll can be found
    if os.path.isdir(exiftool_files_dir):
        path_dirs = env.get('PATH', '').split(os.pathsep)
        if exiftool_files_dir not in path_dirs:
            path_dirs.insert(0, exiftool_files_dir)
            env['PATH'] = os.pathsep.join(path_dirs)
            logger.debug(f"Added to PATH: {exiftool_files_dir}")
            # Log what files are actually in that directory
            try:
                files_in_dir = os.listdir(exiftool_files_dir)
                logger.debug(f"Files in exiftool_files ({len(files_in_dir)} total): {files_in_dir}")
            except Exception as e:
                logger.error(f"Could not list files in {exiftool_files_dir}: {e}")
    else:
        logger.error(f"exiftool_files directory not found at: {exiftool_files_dir}")
    
    # Try to use perl.exe from AppData with exiftool.pl (works when exe not available)
    perl_exe = os.path.join(exiftool_files_dir, 'perl.exe')
    exiftool_pl = os.path.join(exiftool_files_dir, 'exiftool.pl')
    
    if os.path.isfile(perl_exe) and os.path.isfile(exiftool_pl):
        # Use perl + exiftool.pl from AppData (all dependencies in same directory)
        cmd = [perl_exe, exiftool_pl] + list(args)
        logger.debug(f"Using perl from AppData: {perl_exe}")
        logger.debug(f"Running: perl exiftool.pl {' '.join(args[:1])} ...")
    else:
        # Fall back to exiftool.exe from bundled location
        logger.warning(f"perl.exe or exiftool.pl not found in AppData, using bundled exiftool.exe")
        cmd = [EXIFTOOL_PATH] + list(args)
        logger.debug(f"Running ExifTool: {' '.join(cmd[:2])} ...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env, cwd=exiftool_files_dir)
        logger.debug(f"✓ ExifTool success for: {args[0] if args else 'unknown'}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ ExifTool error: {e.stderr}")
        raise

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
            logger.warning("Missing required GPS tags")
            return None, None

        lat = tags["GPS GPSLatitude"]
        lat_ref = tags["GPS GPSLatitudeRef"].printable
        lat_decimal = get_decimal_from_dms(lat.values, lat_ref)

        lon = tags["GPS GPSLongitude"]
        lon_ref = tags["GPS GPSLongitudeRef"].printable
        lon_decimal = get_decimal_from_dms(lon.values, lon_ref)

        if lat_decimal is None or lon_decimal is None:
            logger.warning("Failed to convert GPS coordinates")
            return None, None

        if not (-90 <= lat_decimal <= 90) or not (-180 <= lon_decimal <= 180):
            logger.warning(f"Invalid coordinate values: lat={lat_decimal}, lon={lon_decimal}")
            return None, None

        logger.debug(f"✓ Extracted GPS coordinates: {lat_decimal}, {lon_decimal}")
        return lat_decimal, lon_decimal

    except Exception as e:
        logger.error(f"Error extracting GPS info: {e}")
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

def get_los_fields(image_path, drone_type=None):
    """
    Extract gimbal angles/directions using ExifTool.
    Always returns dict with losAzimuth/losPitch/losRoll keys.
    
    Args:
        image_path: Path to the image file
        drone_type: Type of drone (e.g., "Autel Alpha", "DJI M350 RTK", etc.)
    """
    logger.info(f"get_los_fields() - Processing: {image_path}, Drone: {drone_type}")
    
    try:
        # Determine which EXIF fields to query based on drone type
        is_autel = drone_type and any(keyword in drone_type.lower() for keyword in ['autel', 'evo'])
        
        if is_autel:
            logger.debug("Detected Autel drone - using Autel field names")
            # Autel drones use different field names
            cp = run_exiftool(
                [
                    "-n",
                    "-json",
                    "-XMP:Yaw",
                    "-XMP:Pitch",
                    "-XMP:Roll",
                    "-Yaw",
                    "-Pitch",
                    "-Roll",
                    "-CameraYaw",
                    "-CameraPitch",
                    "-CameraRoll",
                    "-FlightYawDegree",
                    "-FlightPitchDegree",
                    "-FlightRollDegree",
                    image_path,
                ]
            )
            data = json.loads(cp.stdout)[0] if cp.stdout else {}
            logger.debug(f"Autel ExifTool response: {list(data.keys())}")
            
            # Try multiple field name variations for Autel
            yaw = (
                data.get("Yaw") or 
                data.get("XMP:Yaw") or
                data.get("CameraYaw") or 
                data.get("FlightYawDegree") or
                0.0
            )
            pitch = (
                data.get("Pitch") or 
                data.get("XMP:Pitch") or
                data.get("CameraPitch") or 
                data.get("FlightPitchDegree") or
                0.0
            )
            roll = (
                data.get("Roll") or 
                data.get("XMP:Roll") or
                data.get("CameraRoll") or 
                data.get("FlightRollDegree") or
                0.0
            )
            
            return {
                "losAzimuth": to_float_rounded(yaw, digits=4),
                "losPitch": to_float_rounded(pitch, digits=4),
                "losRoll": to_float_rounded(roll, digits=4),
            }
        else:
            # DJI and other drones use standard gimbal fields
            logger.debug("Detected DJI drone - using DJI gimbal field names")
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
            logger.debug(f"DJI ExifTool response: {list(data.keys())}")

            result = {
                "losAzimuth": to_float_rounded(data.get("GimbalYawDegree"), digits=4),
                "losPitch": to_float_rounded(data.get("GimbalPitchDegree"), digits=4),
                "losRoll": to_float_rounded(data.get("GimbalRollDegree"), digits=4),
            }
            logger.info(f"✓ LOS fields extracted: Azimuth={result['losAzimuth']}, Pitch={result['losPitch']}, Roll={result['losRoll']}")
            return result
            
    except FileNotFoundError as e:
        logger.error(f"ExifTool not found: {e}")
        return {"losAzimuth": 0.0, "losPitch": 0.0, "losRoll": 0.0}
    except subprocess.CalledProcessError as e:
        logger.error(f"ExifTool failed: {e.stderr.strip() if e.stderr else e}")
        return {"losAzimuth": 0.0, "losPitch": 0.0, "losRoll": 0.0}
    except Exception as e:
        logger.error(f"Could not extract LOS fields: {e}")
        return {"losAzimuth": 0.0, "losPitch": 0.0, "losRoll": 0.0}

def extract_relative_altitude(image_path):
    """
    Extract relative altitude from XMP metadata.
    Supports both DJI (RelativeAltitude) and Autel (AboveGroundAltitude) formats.
    """
    xmp_data = extract_xmp_metadata(image_path)
    if xmp_data is None:
        return 0.0
    xmp_root, ns = xmp_data
    desc = xmp_root.find(".//rdf:Description", ns)
    if desc is None:
        return 0.0
    
    # Try DJI RelativeAltitude first
    val = desc.attrib.get(f"{{{ns['drone-dji']}}}RelativeAltitude")
    if val is not None:
        try:
            return float(val.lstrip("+"))
        except ValueError:
            pass
    
    # Try Autel AboveGroundAltitude
    # Check all attributes for AboveGroundAltitude (namespace might vary)
    for attr_name, attr_val in desc.attrib.items():
        if 'AboveGroundAltitude' in attr_name:
            try:
                return float(attr_val)
            except ValueError:
                pass
    
    return 0.0
