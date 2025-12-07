import os
import json
import exifread
import base64
import re
from datetime import datetime

from full_metadata_service import generate_full_metadata_json
#from qgis_service import prepare_data_for_qgis

from exif_service import (
    extract_gps_info_from_tags,
    get_los_fields,
    extract_relative_altitude,
)
from json_builders_service import build_json_structure

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

# Main processing

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

    Side effects:
        - Creates the subfolders:
            session_dir/output
            session_dir/fail_output
        - Writes JSON files per image into the relevant folder.
        - Writes a <session_name>.fns text file into output/.
        - Calls `generate_full_metadata_json(session_dir, output_dir)` to produce
          additional "*_all_metadata_file.json" files per image.
    """
    # Session name is used for the .fns marker file
    session_name = os.path.basename(os.path.normpath(session_dir))

    # Output folders
    output_dir = os.path.join(session_dir, "output")
    fail_output_dir = os.path.join(session_dir, "fail_output")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(fail_output_dir, exist_ok=True)

    # Platform name (drone_type) from config.json if not provided explicitly
    if not drone_type:
        drone_type = _read_drone_type_from_config(session_dir)

    print(f"Using platformName (drone_type): {drone_type}")
    print(f"Session dir: {session_dir}")
    print(f"Looking for images in: {session_dir}")

    files = os.listdir(session_dir)
    print(f"Found {len(files)} files")

    total_images = 0
    successful_extractions = 0
    failed_extractions = 0

    for filename in files:
        full_path = os.path.join(session_dir, filename)

        # Skip folders and non-image files
        if not os.path.isfile(full_path):
            continue
        if not filename.lower().endswith((".jpg", ".jpeg")):
            print(f"Skipping (not an image): {filename}")
            continue

        total_images += 1
        print(f"\nProcessing: {filename}")

        try:
            # Read EXIF tags from the image
            with open(full_path, "rb") as img_file:
                tags = exifread.process_file(img_file, details=True)

            # GPS (lat/lon in WGS84 decimal degrees)
            lat, lon = extract_gps_info_from_tags(tags)

            # LOS + relative altitude (from ExifTool / XMP)
            los_fields = get_los_fields(full_path)
            relative_alt = extract_relative_altitude(full_path)

            has_los_fields = (
                los_fields.get("losAzimuth", 0.0) != 0.0
                and los_fields.get("losPitch", 0.0) != 0.0
            )
            has_relative_alt = relative_alt != 0.0

            # Build the JSON structure (including platformName = drone_type)
            json_data = build_json_structure(
                filename,
                tags,
                lat,
                lon,
                full_path,
                drone_type,
            )

            # Decide which folder to use for the JSON output
            if has_los_fields and has_relative_alt:
                output_path = os.path.join(
                    output_dir,
                    f"{os.path.splitext(filename)[0]}.json",
                )
                successful_extractions += 1
                print(f"✅ Successfully extracted critical fields: {output_path}")
            else:
                output_path = os.path.join(
                    fail_output_dir,
                    f"{os.path.splitext(filename)[0]}.json",
                )
                failed_extractions += 1
                missing = []
                if not has_los_fields:
                    missing.append("LOS fields (azimuth/pitch)")
                if not has_relative_alt:
                    missing.append("relative altitude")
                print(
                    f"⚠️ Missing critical fields ({', '.join(missing)}): {output_path}"
                )

            # Write JSON file to disk
            with open(output_path, "w", encoding="utf-8") as jf:
                json.dump(json_data, jf, indent=4, ensure_ascii=False)

        except Exception as e:
            failed_extractions += 1
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
                fallback_path = os.path.join(
                    fail_output_dir,
                    f"{os.path.splitext(filename)[0]}.json",
                )
                with open(fallback_path, "w", encoding="utf-8") as jf:
                    json.dump(json_data, jf, indent=4, ensure_ascii=False)
            except Exception as inner_e:
                print(f"❌ Could not create JSON for {filename}: {inner_e}")

    # Create .fns marker file inside output/
    fns_path = os.path.join(output_dir, f"{session_name}.fns")
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

    # Print summary statistics to the console
    print("\nProcessing Statistics:")
    print(f"Total images processed: {total_images}")
    print(f"Successfully extracted all critical fields: {successful_extractions}")
    print(f"Failed or missing critical fields: {failed_extractions}")
    print(f"\nSuccessful extractions saved to: {output_dir}")
    print(f"Failed extractions saved to: {fail_output_dir}")

    # Second JSON: full metadata for each image (ExifTool -json output)
    try:
        generate_full_metadata_json(session_dir, output_dir)
    except Exception as e:
        print(f"Warning: could not generate all-metadata JSON: {e}")

    return session_dir
