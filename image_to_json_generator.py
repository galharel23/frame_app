import json
import os
import re
import shutil

from PIL import Image, ImageFilter, ImageStat
import exifread

from services.exif_service import extract_gps_info_from_tags, extract_relative_altitude, get_los_fields
from services.full_metadata_service import generate_full_metadata_json
from services.json_builders_service import build_json_structure, classify_sensor_type_from_name
from utils.logging_service import get_logger

logger = get_logger(__name__)

# Main processing


def _read_drone_type_from_config(folder_path: str) -> str:
    """
    קורא את config.json (אם קיים) ומחזיר את שדה 'drone_type'.
    אם לא קיים או ריק – מחזיר מחרוזת ברירת מחדל.
    """
    cfg_path = os.path.join(folder_path, "config.json")
    try:
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                dt = (cfg.get("drone_type") or "").strip()
                if dt:
                    return dt
    except Exception as e:
        print(f"Warning: could not read config.json: {e}")
    return "Unknown platform"


def _ensure_output_dirs(session_dir: str) -> tuple[str, str]:
    """
    Ensure that output/ and fail_output/ directories exist inside the session directory.

    Returns:
        (output_dir, fail_output_dir)
    """
    output_dir = os.path.join(session_dir, "output")
    fail_output_dir = os.path.join(session_dir, "fail_output")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(fail_output_dir, exist_ok=True)
    return output_dir, fail_output_dir


def _ensure_quality_dirs(session_dir: str) -> tuple[str, str]:
    """
    Ensure that GOOD_IMAGES/ and BAD_IMAGES/ directories exist inside the session directory.
    """
    good_dir = os.path.join(session_dir, "GOOD_IMAGES")
    bad_dir = os.path.join(session_dir, "BAD_IMAGES")
    os.makedirs(good_dir, exist_ok=True)
    os.makedirs(bad_dir, exist_ok=True)
    return good_dir, bad_dir


def _load_quality_filter_config(session_dir: str) -> dict:
    """
    Read optional quality filter settings from config.json.
    """
    cfg_path = os.path.join(session_dir, "config.json")
    defaults = {
        "blur_threshold": 10.0,
        "min_relative_altitude": 3.0,
        "max_relative_altitude": 500.0,
        "allow_thermal": True,
        "allow_visible": True,
        "allow_zoom": True,
        "allow_wide": True,
    }
    try:
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                quality = cfg.get("quality_filter", {}) or {}
                defaults["blur_threshold"] = float(quality.get("blur_threshold", defaults["blur_threshold"]))
                defaults["min_relative_altitude"] = float(quality.get("min_relative_altitude", defaults["min_relative_altitude"]))
                defaults["max_relative_altitude"] = float(quality.get("max_relative_altitude", defaults["max_relative_altitude"]))
                defaults["allow_thermal"] = bool(quality.get("allow_thermal", defaults["allow_thermal"]))
                defaults["allow_visible"] = bool(quality.get("allow_visible", defaults["allow_visible"]))
                defaults["allow_zoom"] = bool(quality.get("allow_zoom", defaults["allow_zoom"]))
                defaults["allow_wide"] = bool(quality.get("allow_wide", defaults["allow_wide"]))
    except Exception as e:
        logger.warning(f"Could not read quality filter settings from config.json: {e}")
    return defaults


def _get_image_altitude(tags: dict, relative_alt: float) -> float:
    """
    Return the best available height estimate for quality filtering.
    """
    if relative_alt and relative_alt != 0.0:
        return relative_alt
    try:
        gps_alt = float(str(tags.get("GPS GPSAltitude", "0")))
        return gps_alt
    except Exception:
        return 0.0


def _get_sensor_suffix(filename: str) -> str:
    """Extract the suffix letter from the image filename, e.g. _T, _Z, _W."""
    base = os.path.splitext(os.path.basename(filename))[0]
    match = re.search(r"_([A-Za-z])$", base)
    return match.group(1).upper() if match else ""


def _compute_blur_score(image_path: str) -> float:
    """
    Estimate image sharpness using edge contrast. Lower scores indicate a blurrier image.
    """
    try:
        with Image.open(image_path) as img:
            gray = img.convert("L")
            gray = gray.resize((320, 320))
            edges = gray.filter(ImageFilter.FIND_EDGES)
            stats = ImageStat.Stat(edges)
            return float(stats.mean[0])
    except Exception as e:
        logger.warning(f"Could not compute blur score for {image_path}: {e}")
        return 0.0


def _classify_image_quality(
    filename: str,
    full_path: str,
    tags: dict,
    relative_alt: float,
    los_fields: dict,
    session_dir: str,
    quality_config: dict,
) -> tuple[str, dict]:
    """
    Classify the image as GOOD or BAD based on quality criteria.
    """
    sensor_type = classify_sensor_type_from_name(filename)
    sensor_suffix = _get_sensor_suffix(filename)
    is_thermal = sensor_type.upper() == "IR"
    altitude = _get_image_altitude(tags, relative_alt)
    blur_score = _compute_blur_score(full_path)

    reasons = []
    if blur_score < quality_config["blur_threshold"]:
        reasons.append("blurred image")
    if altitude < quality_config["min_relative_altitude"]:
        reasons.append("altitude below threshold")
    if altitude > quality_config["max_relative_altitude"]:
        reasons.append("altitude above threshold")

    if sensor_suffix == "T" and not quality_config.get("allow_thermal", True):
        reasons.append("thermal images are excluded")
    elif sensor_suffix == "Z" and not quality_config.get("allow_zoom", True):
        reasons.append("zoom images are excluded")
    elif sensor_suffix == "W" and not quality_config.get("allow_wide", True):
        reasons.append("wide images are excluded")
    elif sensor_suffix not in {"T", "Z", "W"} and not quality_config.get("allow_visible", True):
        reasons.append("visible images are excluded")

    # Images with missing critical fields should be treated as bad.
    if los_fields.get("losAzimuth", 0.0) == 0.0 or los_fields.get("losPitch", 0.0) == 0.0 or relative_alt == 0.0:
        reasons.append("missing critical flight metadata")

    classification = "good" if not reasons else "bad"
    quality_data = {
        "classification": classification,
        "sensorType": sensor_type,
        "sensorSuffix": sensor_suffix,
        "isThermal": is_thermal,
        "blurScore": round(blur_score, 2),
        "altitude": round(altitude, 2),
        "blurThreshold": quality_config.get("blur_threshold", 10.0),
        "minRelativeAltitude": quality_config.get("min_relative_altitude", 3.0),
        "maxRelativeAltitude": quality_config.get("max_relative_altitude", 500.0),
        "allowThermal": quality_config.get("allow_thermal", True),
        "allowVisible": quality_config.get("allow_visible", True),
        "allowZoom": quality_config.get("allow_zoom", True),
        "allowWide": quality_config.get("allow_wide", True),
        "reasons": reasons,
    }
    return classification, quality_data


def _copy_to_quality_dir(
    session_dir: str,
    filename: str,
    full_path: str,
    json_data: dict,
    classification: str,
) -> None:
    """
    Copy the image and its JSON metadata into the GOOD_IMAGES or BAD_IMAGES folder.
    """
    good_dir, bad_dir = _ensure_quality_dirs(session_dir)
    target_dir = good_dir if classification == "good" else bad_dir
    os.makedirs(target_dir, exist_ok=True)

    base_name = os.path.splitext(filename)[0]
    target_image_path = os.path.join(target_dir, filename)
    target_json_path = os.path.join(target_dir, f"{base_name}.json")

    try:
        shutil.copy2(full_path, target_image_path)
    except Exception:
        pass

    try:
        _write_json(target_json_path, json_data)
    except Exception as e:
        logger.warning(f"Could not write quality JSON for {filename}: {e}")


def _iter_session_images(session_dir: str):
    """
    Iterate over image filenames in the session directory.
    Only regular files ending with .jpg/.jpeg/ .png (case-insensitive) are yielded.
    """
    files = os.listdir(session_dir)
    print(f"Found {len(files)} files")

    for filename in files:
        full_path = os.path.join(session_dir, filename)

        # Skip folders and non-image files
        if not os.path.isfile(full_path):
            continue
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            print(f"Skipping (not an image): {filename}")
            continue

        yield filename, full_path


def _write_json(path: str, data: dict) -> None:
    """
    Write a JSON object to disk with UTF-8 encoding and pretty-print indentation.
    """
    with open(path, "w", encoding="utf-8") as jf:
        json.dump(data, jf, indent=4, ensure_ascii=False)


def _process_single_image(
    filename: str,
    full_path: str,
    output_dir: str,
    fail_output_dir: str,
    drone_type: str,
    session_dir: str,
    quality_config: dict,
) -> str:
    """
    Process a single image:
      - Read EXIF
      - Extract GPS, LOS, relative altitude
      - Build JSON structure
      - Decide whether it goes to output/ or fail_output/

    Returns:
        "success"          – if critical fields exist (LOS + relative altitude)
        "failed_missing"   – if missing critical fields
        "failed_exception" – if an exception occurred during processing
    """
    logger.info(f"Processing image: {filename}")

    try:
        # Read EXIF tags from the image
        logger.debug(f"Reading EXIF from: {full_path}")
        with open(full_path, "rb") as img_file:
            tags = exifread.process_file(img_file, details=True)
        logger.debug(f"EXIF tags extracted: {len(tags)} tags found")

        # GPS (lat/lon in WGS84 decimal degrees)
        logger.debug("Extracting GPS information...")
        lat, lon = extract_gps_info_from_tags(tags)
        logger.debug(f"GPS: Latitude={lat}, Longitude={lon}")

        # LOS + relative altitude (from ExifTool / XMP)
        logger.debug("Extracting LOS fields...")
        los_fields = get_los_fields(full_path, drone_type=drone_type)
        logger.debug(
            f"LOS: Azimuth={los_fields.get('losAzimuth')}, "
            f"Pitch={los_fields.get('losPitch')}, "
            f"Roll={los_fields.get('losRoll')}"
        )

        logger.debug("Extracting relative altitude...")
        relative_alt = extract_relative_altitude(full_path)
        logger.debug(f"Relative altitude: {relative_alt}")

        has_los_fields = los_fields.get("losAzimuth", 0.0) != 0.0 and los_fields.get("losPitch", 0.0) != 0.0
        has_relative_alt = relative_alt != 0.0

        logger.debug(f"Validation: has_los={has_los_fields}, has_alt={has_relative_alt}")

        # Build the JSON structure (including platformName = drone_type)
        logger.debug("Building JSON structure...")
        json_data = build_json_structure(
            filename,
            tags,
            lat,
            lon,
            full_path,
            drone_type,
        )

        # Add quality metadata and classification
        classification, quality_data = _classify_image_quality(
            filename=filename,
            full_path=full_path,
            tags=tags,
            relative_alt=relative_alt,
            los_fields=los_fields,
            session_dir=session_dir,
            quality_config=quality_config,
        )
        json_data["QualityControl"] = quality_data

        # Save a copy into the quality folders as well
        _copy_to_quality_dir(session_dir, filename, full_path, json_data, classification)

        # Decide which folder to use for the JSON output
        if has_los_fields and has_relative_alt:
            # Successful image: create a dedicated folder inside output/
            base_name, _ = os.path.splitext(filename)
            image_dir = os.path.join(output_dir, base_name)
            os.makedirs(image_dir, exist_ok=True)

            # Copy the original image into its folder (for easier per-image inspection)
            try:
                shutil.copy2(full_path, os.path.join(image_dir, filename))
            except Exception:
                # Non-fatal: continue even if image copy fails
                pass

            output_path = os.path.join(image_dir, f"{base_name}.json")
            logger.info(f"✓ {filename}: Successfully extracted critical fields → {output_path}")
            _write_json(output_path, json_data)
            return "success"

        # Missing some critical fields → goes to fail_output
        base_name, _ = os.path.splitext(filename)
        fail_image_dir = os.path.join(fail_output_dir, base_name)
        os.makedirs(fail_image_dir, exist_ok=True)

        try:
            shutil.copy2(full_path, os.path.join(fail_image_dir, filename))
        except Exception:
            pass

        output_path = os.path.join(fail_image_dir, f"{base_name}.json")
        missing = []
        if not has_los_fields:
            missing.append("LOS fields (azimuth/pitch)")
        if not has_relative_alt:
            missing.append("relative altitude")
        logger.warning(f"⚠️ {filename}: Missing critical fields ({', '.join(missing)}) → {output_path}")
        _write_json(output_path, json_data)
        return "failed_missing"

    except Exception as e:
        logger.error(f"✗ {filename}: Exception during processing: {e}", exc_info=True)
        print(f"❌ Failed to process {filename}: {e}")

        # Best-effort attempt to produce a "fallback" JSON with whatever data we can read
        try:
            with open(full_path, "rb") as img_file:
                tags = exifread.process_file(img_file, details=True)
            lat, lon = extract_gps_info_from_tags(tags)
            json_data = build_json_structure(
                filename,
                tags,
                lat,
                lon,
                full_path,
                drone_type,
            )
            json_data["QualityControl"] = {
                "classification": "bad",
                "sensorType": classify_sensor_type_from_name(filename),
                "isThermal": classify_sensor_type_from_name(filename).upper() == "IR",
                "blurScore": 0.0,
                "altitude": 0.0,
                "blurThreshold": quality_config.get("blur_threshold", 10.0),
                "minRelativeAltitude": quality_config.get("min_relative_altitude", 3.0),
                "maxRelativeAltitude": quality_config.get("max_relative_altitude", 500.0),
                "allowThermal": quality_config.get("allow_thermal", True),
                "allowVisible": quality_config.get("allow_visible", True),
                "reasons": ["exception during processing"],
            }
            _copy_to_quality_dir(session_dir, filename, full_path, json_data, "bad")
            fallback_path = os.path.join(
                fail_output_dir,
                f"{os.path.splitext(filename)[0]}.json",
            )
            _write_json(fallback_path, json_data)
        except Exception as inner_e:
            print(f"❌ Could not create JSON for {filename}: {inner_e}")

        return "failed_exception"


def _write_fns_marker(
    output_dir: str,
    session_name: str,
    session_dir: str,
    total_images: int,
    successful_extractions: int,
    failed_extractions: int,
) -> None:
    """
    Write a .fns marker file inside the output directory with basic statistics
    about the processing run.
    """
    fns_path = os.path.join(output_dir, "a.fns")
    try:
        with open(fns_path, "w", encoding="utf-8") as f:
            f.write(
                f"session={session_name}\n"
                f"base_dir={session_dir}\n"
                f"total_images={total_images}\n"
                f"ok={successful_extractions}\n"
                f"failed={failed_extractions}\n"
            )
        print(f"Created FNS marker: {fns_path}")
    except Exception as e:
        print(f"Warning: could not write .fns file: {e}")


def process_images_to_individual_json(session_dir: str, drone_type: str | None = None) -> str:
    """
    Process all images in a given session directory and generate per-image JSON files.

    Pipeline:
      1. Create output/ and fail_output/ subfolders inside the session directory.
      2. For each JPG/JPEG image in the session directory:
         - Read EXIF tags using exifread.
         - Extract GPS coordinates.
         - Extract LOS (line-of-sight) fields and relative altitude using ExifTool / XMP.
         - Build a structured JSON document (BasicData, CameraData, CameraPosition,
           PlatformData, Operational, SensorSpecificData).
         - Decide whether the image is considered "successful" (has LOS + relative altitude)
           or "failed" (missing critical fields), and write the JSON accordingly to either:
             - output/<image_name>.json
             - fail_output/<image_name>.json
      3. Create a .fns marker file inside output/ with basic statistics about the run.
      4. Generate a second "full metadata" JSON for each image (all ExifTool fields),
         using `generate_full_metadata_json`.

    Args:
        session_dir: Path to an existing "session" directory that already contains:
                     - The source images
                     - (Optionally) a config.json with "drone_type".
        drone_type:  Optional explicit platform name. If None, the function will try
                     to read it from config.json (field "drone_type"). If that also
                     fails, it falls back to "Unknown platform".

    Returns:
        The session_dir path (for convenient chaining in the processing pipeline).
    """
    # Session name is used for the .fns marker file
    session_name = os.path.basename(os.path.normpath(session_dir))

    # Output folders
    output_dir, fail_output_dir = _ensure_output_dirs(session_dir)
    good_images_dir, bad_images_dir = _ensure_quality_dirs(session_dir)
    quality_config = _load_quality_filter_config(session_dir)

    # Platform name (drone_type) from config.json if not provided explicitly
    if not drone_type:
        drone_type = _read_drone_type_from_config(session_dir)

    logger.info("=== Starting image batch processing ===")
    logger.info(f"Session: {session_name} | Platform: {drone_type}")
    logger.info(f"Session dir: {session_dir}")
    logger.info(f"Output folders: success={output_dir}, failed={fail_output_dir}")

    total_images = 0
    successful_extractions = 0
    failed_extractions = 0

    # Main per-image loop
    for filename, full_path in _iter_session_images(session_dir):
        total_images += 1
        status = _process_single_image(
            filename=filename,
            full_path=full_path,
            output_dir=output_dir,
            fail_output_dir=fail_output_dir,
            drone_type=drone_type,
            session_dir=session_dir,
            quality_config=quality_config,
        )

        if status == "success":
            successful_extractions += 1
        else:
            # Both "failed_missing" and "failed_exception" are counted as failed
            failed_extractions += 1

    # Create .fns marker file inside EACH image folder (success and fail)
    # The user requested 1 .fns file per folder of image processed.

    # 1. Successful images
    try:
        if os.path.isdir(output_dir):
            for item in os.listdir(output_dir):
                sub_path = os.path.join(output_dir, item)
                if os.path.isdir(sub_path):
                    _write_fns_marker(
                        output_dir=sub_path,
                        session_name=session_name,
                        session_dir=session_dir,
                        total_images=total_images,
                        successful_extractions=successful_extractions,
                        failed_extractions=failed_extractions,
                    )
    except Exception as e:
        logger.error(f"Failed to write .fns files in output_dir: {e}")

    # 2. Failed images
    try:
        if os.path.isdir(fail_output_dir):
            for item in os.listdir(fail_output_dir):
                sub_path = os.path.join(fail_output_dir, item)
                if os.path.isdir(sub_path):
                    _write_fns_marker(
                        output_dir=sub_path,
                        session_name=session_name,
                        session_dir=session_dir,
                        total_images=total_images,
                        successful_extractions=successful_extractions,
                        failed_extractions=failed_extractions,
                    )
    except Exception as e:
        logger.error(f"Failed to write .fns files in fail_output_dir: {e}")

    # Print summary statistics to the console
    logger.info("=== Processing Complete ===")
    logger.info(f"Total: {total_images} | Success: {successful_extractions} | Failed: {failed_extractions}")
    print("\nProcessing Statistics:")
    print(f"Total images processed: {total_images}")
    print(f"Successfully extracted all critical fields: {successful_extractions}")
    print(f"Failed or missing critical fields: {failed_extractions}")
    print(f"\nSuccessful extractions saved to: {output_dir}")
    print(f"Failed extractions saved to: {fail_output_dir}")
    print(f"Good image classification saved to: {good_images_dir}")
    print(f"Bad image classification saved to: {bad_images_dir}")

    # Second JSON: full metadata for each image (ExifTool -json output)
    try:
        generate_full_metadata_json(session_dir, output_dir)
    except Exception as e:
        print(f"Warning: could not generate all-metadata JSON: {e}")

    return session_dir
