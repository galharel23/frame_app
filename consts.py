from pathlib import Path
import sys

# תיקיית השורש של הפרויקט (frame_app)
PROJECT_ROOT = Path(__file__).resolve().parent

# תיקיית התמונות (אם תרצה להרחיב בעתיד)
IMAGE_DIR = PROJECT_ROOT / "image"


def resource_path(rel_path: str) -> str:
    """
    מחזיר נתיב מלא לקובץ משאב (תמונה, אייקון וכו'):
    - תומך בהרצה כ-exe (PyInstaller - sys._MEIPASS)
    - תומך בהרצה רגילה עם `python app.py`
    rel_path הוא תמיד יחסי לשורש הפרויקט (PROJECT_ROOT).
    """
    rel = Path(rel_path)

    # כאשר רץ מתוך exe (PyInstaller)
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        # הרצה רגילה עם python
        base = PROJECT_ROOT

    return str(base / rel)


# ---- משאבים גרפיים (תמונות וכו') ----

DRONE_IMG = resource_path("image/Drone.gif")
LOGO_IMG = resource_path("image/logo.png")
