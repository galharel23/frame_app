import os
import json
import subprocess
from typing import Iterable

def _resolve_exiftool_path() -> str:
    """
    מחפש את exiftool כך:
    1) אם קיים EXIFTOOL_PATH במשתני סביבה – נשתמש בו
    2) אחרת ננסה 'exiftool' מתוך ה-PATH
    """
    env_p = os.environ.get("EXIFTOOL_PATH")
    if env_p:
        return env_p

    # ברירת מחדל – נסמוך על זה שהוא ב-PATH
    return "exiftool"


EXIFTOOL_PATH = _resolve_exiftool_path()


def run_exiftool(args: list[str]) -> subprocess.CompletedProcess:
    """
    הרצה של ExifTool (ללא shell=True).
    """
    cmd = [EXIFTOOL_PATH] + args
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


IMG_EXTS = (".jpg", ".jpeg", ".dng", ".JPG", ".JPEG", ".DNG", ".png", ".PNG")


def iter_image_files(session_dir: str) -> Iterable[str]:
    """
    מחזיר שמות קבצי תמונה מתוך תיקיית הסשן.
    """
    for name in os.listdir(session_dir):
        full_path = os.path.join(session_dir, name)
        if not os.path.isfile(full_path):
            continue
        if not name.endswith(IMG_EXTS):
            continue
        yield name


def generate_full_metadata_json(session_dir: str, output_dir: str) -> None:
    """
    עבור כל תמונה בתיקיית הסשן (session_dir), מריץ ExifTool בפורמט JSON
    ושומר קובץ JSON נפרד עם *כל* המטא־דאטה של התמונה, בשם:
        <image_name>_all_metadata_file.json
    בתוך תיקיית ה-output.
    """
    os.makedirs(output_dir, exist_ok=True)

    for name in iter_image_files(session_dir):
        full_path = os.path.join(session_dir, name)
        print(f"Creating full metadata JSON for image: {name}")

        try:
            # ExifTool -json יחזיר מערך עם אובייקט אחד
            cp = run_exiftool(["-json", full_path])
            if not cp.stdout:
                print(f"ExifTool returned no JSON output for {name}")
                continue

            try:
                meta_list = json.loads(cp.stdout)
            except json.JSONDecodeError as e:
                print(f"Failed to parse ExifTool JSON output for {name}: {e}")
                continue

            if not meta_list:
                print(f"No metadata objects returned for {name}")
                continue

            full_meta = meta_list[0]

            base, _ = os.path.splitext(name)
            out_path = os.path.join(output_dir, f"{base}_all_metadata_file.json")

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(full_meta, f, ensure_ascii=False, indent=2)

            print(f"✅ Full metadata JSON created: {out_path}")

        except Exception as e:
            print(f"⚠ Failed to create full metadata JSON for {name}: {e}")
