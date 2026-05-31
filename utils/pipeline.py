# utils/pipeline.py
from __future__ import annotations
import os, shutil, tempfile, pathlib, json
from typing import Iterable, List, Dict
from datetime import datetime
from pathlib import Path

from image_to_json_generator import process_images_to_individual_json
from services.qgis_service import prepare_data_for_qgis


IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}


def _is_image(p: str) -> bool:
    return pathlib.Path(p).suffix.lower() in IMAGE_EXT


def _gather_images_in_dir(dir_path: str) -> List[str]:
    out: List[str] = []
    for root, _, files in os.walk(dir_path):
        for f in files:
            full = os.path.join(root, f)
            if _is_image(full):
                out.append(full)
    return out


def _create_session_dir() -> tuple[str, str]:
    """Create a timestamped session directory under the system temp."""
    session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(tempfile.gettempdir(), f"whitening_{session_name}")
    os.makedirs(session_dir, exist_ok=True)
    return session_dir, session_name


def _gather_main_jsons(root_dir: str) -> List[str]:
    """Collect all "main" JSONs under a directory, skipping full-metadata files.

    Works for both the old flat layout (files directly under root_dir)
    and the new per-image subfolder layout.
    """
    json_files: List[str] = []
    for dirpath, _, files in os.walk(root_dir):
        for f in files:
            if not f.lower().endswith(".json"):
                continue
            if f.endswith("_all_metadata_file.json"):
                continue
            json_files.append(os.path.join(dirpath, f))
    return json_files


def _image_name_from_json(json_path: str) -> str:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d.get("BasicData", {}).get("imageFile") or (Path(json_path).stem + ".JPG")
    except Exception:
        return Path(json_path).stem + ".JPG"

import math

def run_whitening(
    selected_paths: Iterable[str],
    drone_type: str,
    log_path: str | None = None,
    skip_log: bool = False,
    quality_filter: dict | None = None,
) -> Dict:
    """
    1) Create a session folder named date-time
    2) Copy to it all selected images and config.json
    3) Run processing on the session folder itself
    4) Prepare TO_QGIS + ZIP
    5) Return an object for display on the results screen

    Args:
        selected_paths: Local file paths or directories to include in the session.
        drone_type: Drone type selected by the user.
        log_path: Optional log file path (currently unused in the UI).
        skip_log: Whether to skip log processing.
        quality_filter: Optional quality filter settings to save in config.json.
    """
    # 1) Session folder
    session_dir, session_name = _create_session_dir()

    # 2) Copy selected images
    copied = 0
    for p in selected_paths:
        if not p:
            continue
        if os.path.isdir(p):
            for img in _gather_images_in_dir(p):
                shutil.copy2(img, os.path.join(session_dir, os.path.basename(img)))
                copied += 1
        elif _is_image(p) and os.path.isfile(p):
            shutil.copy2(p, os.path.join(session_dir, os.path.basename(p)))
            copied += 1
    if copied == 0:
        raise RuntimeError("לא נמצאו תמונות להלבנה.")

    # 3) כתיבת config.json בתוך תיקיית הסשן
    try:
        cfg = {"drone_type": drone_type, "log_path": log_path, "skip_log": bool(skip_log)}
        if quality_filter is not None:
            cfg["quality_filter"] = quality_filter
        with open(os.path.join(session_dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # 4) עיבוד — אנחנו מעבירים את תיקיית הסשן כדי שכל הפלט ירוכז בה
    session_used = process_images_to_individual_json(session_dir, drone_type=drone_type)

    # 5) הכנה ל-QGIS מתוך תיקיית הסשן עצמה
    prepare_data_for_qgis(session_used)

    # 6) יצירת ZIP של TO_QGIS בתוך הסשן
    to_qgis_dir = os.path.join(session_used, "TO_QGIS")
    zip_path = shutil.make_archive(os.path.join(session_used, "TO_QGIS"), "zip", to_qgis_dir)

    # 7) בניית מפת תוצאות להצגה
    output_dir = os.path.join(session_used, "output")
    fail_dir = os.path.join(session_used, "fail_output")
    results: Dict[str, Dict] = {}

    if os.path.isdir(output_dir):
        for jp in sorted(_gather_main_jsons(output_dir)):
            img_name = _image_name_from_json(jp)
            results[img_name] = {"status": "success", "json_path": jp}

    if os.path.isdir(fail_dir):
        for jp in sorted(_gather_main_jsons(fail_dir)):
            img_name = _image_name_from_json(jp)
            results.setdefault(img_name, {"status": "failed", "json_path": jp})

    return {
        "session_dir": session_used,
        "zip_path": zip_path,
        "output_dir": output_dir,
        "fail_output_dir": fail_dir,
        "to_qgis_dir": to_qgis_dir,
        "results": results,  # לשימוש screens/results.py
    }
