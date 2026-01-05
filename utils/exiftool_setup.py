# utils/exiftool_setup.py
from __future__ import annotations
import os, sys
from pathlib import Path
from shutil import which
from utils.logging_service import get_logger

logger = get_logger("exiftool_setup")

# Get base path for PyInstaller or regular execution
try:
    BASE_PATH = Path(sys._MEIPASS)  # PyInstaller bundled
    logger.info(f"Running as PyInstaller bundle. BASE_PATH: {BASE_PATH}")
except AttributeError:
    BASE_PATH = Path(__file__).resolve().parent.parent  # Regular execution
    logger.info(f"Running in regular mode. BASE_PATH: {BASE_PATH}")

# Windows-only registry helpers
if os.name == "nt":
    import winreg
    import ctypes

SENTINEL_NAME = ".exiftool_path_set"

def _find_exiftool_dir(base_dir: Path) -> Path | None:
    """
    Search for the directory containing exiftool.exe relative to the project directory (base_dir).
    """
    logger.debug(f"_find_exiftool_dir: Searching in {base_dir}")
    
    # Common candidates within the project
    candidates = [
        base_dir / "exiftool.exe",
        base_dir / "exiftool-13.30_64" / "exiftool.exe",
        base_dir / "exiftool-13.32_64" / "exiftool.exe",
        BASE_PATH / "exiftool.exe",
        BASE_PATH / "exiftool-13.30_64" / "exiftool.exe",
        BASE_PATH / "exiftool-13.32_64" / "exiftool.exe",
    ]
    
    for c in candidates:
        logger.debug(f"  Checking: {c}")
        if c.is_file():
            logger.info(f"✓ Found exiftool at: {c.parent}")
            return c.parent

    # Search for exiftool*/exiftool.exe up to depth 3
    logger.debug("Searching recursively for exiftool.exe...")
    for exe in base_dir.rglob("exiftool.exe"):
        try:
            depth = len(exe.parent.relative_to(base_dir).parts)
        except ValueError:
            depth = 99
        if depth <= 3 and exe.is_file():
            logger.info(f"✓ Found exiftool (recursive search) at: {exe.parent}")
            return exe.parent
    
    logger.warning(f"✗ ExifTool not found in {base_dir}")
    return None

def _get_user_path() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, "Path")
            return val
    except Exception:
        return ""

def _set_user_path(new_val: str) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_val)

def _broadcast_env_change():
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x001A
    SMTO_ABORTIFHUNG = 0x0002
    res = ctypes.c_long()
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
        SMTO_ABORTIFHUNG, 5000, ctypes.byref(res)
    )

def ensure_exiftool_on_path(base_dir: Path) -> tuple[bool, str]:
    """
    Ensure exiftool is available on PATH.
    Returns (success, message).
    """
    logger.info("ensure_exiftool_on_path() called")
    
    # Not Windows? Nothing to do.
    if os.name != "nt":
        logger.info("Non-Windows environment - skipping")
        return True, "Non-Windows environment – skipping PATH setup."

    sentinel = base_dir / SENTINEL_NAME

    # Already on PATH?
    if which("exiftool"):
        logger.info("✓ ExifTool already on PATH")
        try:
            sentinel.write_text("ok", encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not write sentinel file: {e}")
        return True, "ExifTool already on PATH."

    logger.info("ExifTool not on PATH - searching for bundled version...")
    
    # Try to find exiftool in bundled location first (PyInstaller)
    exif_dir = _find_exiftool_dir(BASE_PATH)
    
    # If not found in bundle, try in the provided base_dir
    if not exif_dir:
        logger.info(f"Not found in BASE_PATH, searching in base_dir: {base_dir}")
        exif_dir = _find_exiftool_dir(base_dir)
    
    if not exif_dir:
        error_msg = "ExifTool not found. Please ensure exiftool-13.30_64 folder exists in the application directory."
        logger.error(error_msg)
        return False, error_msg

    # Update user PATH
    current = _get_user_path()
    parts = [p for p in (current.split(";") if current else []) if p.strip()]
    
    target_norm = exif_dir.resolve().as_posix().lower()
    already = False
    for p in parts:
        try:
            if Path(p).exists():
                if Path(p).resolve().as_posix().lower() == target_norm:
                    already = True
                    logger.info(f"ExifTool path already in PATH: {p}")
                    break
        except Exception:
            if p.replace("\\", "/").lower() == target_norm:
                already = True
                logger.info(f"ExifTool path already in PATH (string match): {p}")
                break

    if not already:
        logger.info(f"Adding ExifTool to PATH: {exif_dir}")
        parts.append(str(exif_dir))
        new_val = ";".join(parts)
        _set_user_path(new_val)
        _broadcast_env_change()
        logger.info("✓ PATH updated successfully")

    try:
        sentinel.write_text("ok", encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not write sentinel file: {e}")

    logger.info(f"✓ ExifTool setup complete: {exif_dir}")
    return True, f"Added to PATH: {exif_dir}"
