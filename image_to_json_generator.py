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

def _make_session_dir(base_dir: str) -> tuple[str, str]:
    """
    יוצר תיקיית סשן בשם חותמת זמן בתוך base_dir.
    מחזיר (session_dir, session_name).
    """
    session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(base_dir, session_name)
    os.makedirs(session_dir, exist_ok=True)
    return session_dir, session_name

# -------------------------------
# Main processing
# -------------------------------

def process_images_to_individual_json(session_dir: str, drone_type: str | None = None) -> str:
    """
    מריץ את עיבוד ההלבנה על תיקיית סשן *קיימת* (session_dir) שבה נמצאות התמונות והקובץ config.json.
    יוצר תתי-תיקיות output/ ו-fail_output/, מייצר JSON לכל תמונה,
    וכותב קובץ סמן <session>.fns בתוך output/.
    מחזיר את נתיב תיקיית הסשן (לנוחות שרשור בצינור העיבוד).
    """
    # שם הסשן לצורך .fns
    session_name = os.path.basename(os.path.normpath(session_dir))

    # תיקיות פלט
    output_dir = os.path.join(session_dir, "output")
    fail_output_dir = os.path.join(session_dir, "fail_output")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(fail_output_dir, exist_ok=True)

    # platformName מתוך config.json אם לא הועבר פרמטר
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

        # מדלג על תיקיות/קבצים שאינם תמונה
        if not os.path.isfile(full_path):
            continue
        if not filename.lower().endswith((".jpg", ".jpeg")):
            print(f"Skipping (not an image): {filename}")
            continue

        total_images += 1
        print(f"\nProcessing: {filename}")

        try:
            with open(full_path, "rb") as img_file:
                tags = exifread.process_file(img_file, details=True)

            # GPS
            lat, lon = extract_gps_info_from_tags(tags)

            # LOS + גובה יחסי
            los_fields = get_los_fields(full_path)
            relative_alt = extract_relative_altitude(full_path)

            has_los_fields = (los_fields.get("losAzimuth", 0.0) != 0.0 and
                              los_fields.get("losPitch",   0.0) != 0.0)
            has_relative_alt = relative_alt != 0.0

            # בניית JSON (כולל platformName = drone_type)
            json_data = build_json_structure(filename, tags, lat, lon, full_path, drone_type)

            # בחירת יעד הפלט
            if has_los_fields and has_relative_alt:
                output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.json")
                successful_extractions += 1
                print(f"✅ Successfully extracted critical fields: {output_path}")
            else:
                output_path = os.path.join(fail_output_dir, f"{os.path.splitext(filename)[0]}.json")
                failed_extractions += 1
                missing = []
                if not has_los_fields:
                    missing.append("LOS fields (azimuth/pitch)")
                if not has_relative_alt:
                    missing.append("relative altitude")
                print(f"⚠️ Missing critical fields ({', '.join(missing)}): {output_path}")

            # כתיבה לדיסק
            with open(output_path, "w", encoding="utf-8") as jf:
                json.dump(json_data, jf, indent=4, ensure_ascii=False)

        except Exception as e:
            failed_extractions += 1
            print(f"❌ Failed to process {filename}: {e}")
            # ניסיון לכתוב JSON "נופל" עם המידע שיש
            try:
                with open(full_path, "rb") as img_file:
                    tags = exifread.process_file(img_file, details=True)
                lat, lon = extract_gps_info_from_tags(tags)
                json_data = build_json_structure(filename, tags, lat, lon, full_path, drone_type)
                fallback_path = os.path.join(fail_output_dir, f"{os.path.splitext(filename)[0]}.json")
                with open(fallback_path, "w", encoding="utf-8") as jf:
                    json.dump(json_data, jf, indent=4, ensure_ascii=False)
            except Exception as inner_e:
                print(f"❌ Could not create JSON for {filename}: {inner_e}")

    # קובץ סמן .fns בתוך output/
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

    print("\nProcessing Statistics:")
    print(f"Total images processed: {total_images}")
    print(f"Successfully extracted all critical fields: {successful_extractions}")
    print(f"Failed or missing critical fields: {failed_extractions}")
    print(f"\nSuccessful extractions saved to: {output_dir}")
    print(f"Failed extractions saved to: {fail_output_dir}")

    ### second JSON
    try:
        generate_full_metadata_json(session_dir, output_dir)
    except Exception as e:
        print(f"Warning: could not generate all-metadata JSON: {e}")

    return session_dir