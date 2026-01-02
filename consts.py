from pathlib import Path
import sys

# Project root directory (frame_app)
PROJECT_ROOT = Path(__file__).resolve().parent

# Image directory (for future expansion if needed)
IMAGE_DIR = PROJECT_ROOT / "image"


def resource_path(rel_path: str) -> str:
    """
    Returns the full path to a resource file (image, icon, etc.):
    - Supports running as exe (PyInstaller - sys._MEIPASS)
    - Supports regular execution with `python app.py`
    rel_path is always relative to the project root (PROJECT_ROOT).
    """
    rel = Path(rel_path)

    # When running from within exe (PyInstaller)
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        # Regular execution with python
        base = PROJECT_ROOT

    return str(base / rel)


# ---- Graphical resources (images, etc.) ----

DRONE_IMG = resource_path("image/Drone.gif")
LOGO_IMG = resource_path("image/logo.png")
