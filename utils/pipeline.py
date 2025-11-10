# utils/pipeline.py
from __future__ import annotations
import os, shutil, tempfile, pathlib, json
from typing import Iterable, List, Dict
from datetime import datetime
from pathlib import Path

from image_to_json_generator import (
    process_images_to_individual_json,
    prepare_data_for_qgis,
)

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


def _image_name_from_json(json_path: str) -> str:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d.get("BasicData", {}).get("imageFile") or (Path(json_path).stem + ".JPG")
    except Exception:
        return Path(json_path).stem + ".JPG"

import math

def _create_jpw_from_json(json_path: str):
    """
    יוצר קובץ JPW לפי נתוני ה-JSON שלך (DJI / Modash)
    רק שינוי קנה-מידה ומיקום — בלי מתיחה או סיבוב.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        basic = data.get("BasicData", {})
        camera_pos = data.get("CameraPosition", {})

        res = basic.get("resolution")  # מטר לפיקסל
        width = basic.get("width")
        height = basic.get("height")
        lon = camera_pos.get("gpsLongitude")
        lat = camera_pos.get("gpsLatitude")

        if not all([res, width, height, lon, lat]):
            print(f"Skipping JPW creation for {json_path} — missing data")
            return

        # המרה למטרים (Web Mercator)
        R = 6378137.0
        x_center = R * math.radians(lon)
        y_center = R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

        # חישוב פינה שמאלית-עליונה
        C = x_center - (width / 2) * res
        F = y_center + (height / 2) * res

        # רק שינוי גודל — אין סיבוב
        A = res      # pixel size X
        D = 0.0
        B = 0.0
        E = -res     # pixel size Y (שלילי)

        # כתיבת JPW
        jpw_path = os.path.splitext(json_path)[0] + ".jpw"
        with open(jpw_path, "w", encoding="utf-8") as jf:
            jf.write(f"{A}\n{D}\n{B}\n{E}\n{C}\n{F}\n")

        print(f"JPW created (no distortion): {jpw_path}")

    except Exception as ex:
        print(f"JPW generation failed for {json_path}: {ex}")





def run_whitening(
    selected_paths: Iterable[str],
    drone_type: str,
    log_path: str | None = None,
    skip_log: bool = False,
) -> Dict:
    """
    1) יוצר תיקיית סשן בשם תאריך־שעה
    2) מעתיק אליה את *כל התמונות* שנבחרו ואת config.json
    3) מריץ את העיבוד על תיקיית הסשן עצמה
    4) מכין TO_QGIS + ZIP
    5) מחזיר אובייקט לתצוגה במסך התוצאות
    """
    # 1) תיקיית סשן
    session_dir, session_name = _create_session_dir()

    # 2) העתקת תמונות שנבחרו
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
        for jf in sorted(os.listdir(output_dir)):
            if jf.lower().endswith(".json"):
                jp = os.path.join(output_dir, jf)
                img_name = _image_name_from_json(jp)
                results[img_name] = {"status": "success", "json_path": jp}

    if os.path.isdir(fail_dir):
        for jf in sorted(os.listdir(fail_dir)):
            if jf.lower().endswith(".json"):
                jp = os.path.join(fail_dir, jf)
                img_name = _image_name_from_json(jp)
                results.setdefault(img_name, {"status": "failed", "json_path": jp})

    # 8) יצירת קובצי JPW והעברת התמונות ל-output
    for img_name, info in results.items():
        json_path = info["json_path"]
        _create_jpw_from_json(json_path)

        # העברת התמונה ל-output (אם קיימת בתיקיית הסשן)
        img_src = os.path.join(session_used, img_name)
        img_dst = os.path.join(output_dir, img_name)
        if os.path.isfile(img_src):
            try:
                shutil.move(img_src, img_dst)
            except Exception:
                # אם כבר קיימת — נניח שהיא כבר שם
                pass

    return {
        "session_dir": session_used,
        "zip_path": zip_path,
        "output_dir": output_dir,
        "fail_output_dir": fail_dir,
        "to_qgis_dir": to_qgis_dir,
        "results": results,  # לשימוש screens/results.py
    }
