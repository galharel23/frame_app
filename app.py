# app.py
import flet as ft
import asyncio
import sys, os
from pathlib import Path
# ---------------------------------------------------------
# 🔹 ייבוא מסכים ופונקציות עזר
from screens.opening import build_opening_screen
from screens.image_select import build_image_select_screen
from utils.exiftool_setup import ensure_exiftool_on_path


# ---------------------------------------------------------
# 🔹 פונקציה שתוודא שקובץ קיים גם ב-EXE וגם בדיבאג רגיל
# ---------------------------------------------------------
def resource_path(relative_path: str):
    """
    מאפשר למצוא קובץ גם בזמן פיתוח וגם לאחר בניית EXE
    ע"י PyInstaller.
    """
    try:
        base_path = sys._MEIPASS  # כשזה EXE – הקבצים בפנים
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# ---------------------------------------------------------
# 🔹 פונקציית הראשית – פתיחת האפליקציה
# ---------------------------------------------------------
def main(page: ft.Page):
    page.title = "WhiteBox"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#000000"
    page.horizontal_alignment = "center"
    page.vertical_alignment = "center"
    page.rtl = True

    from screens.media_type import build_media_type_screen
    from screens.video_processing import build_video_processing_screen

    setup_dlg = ft.AlertDialog(
        modal=True,
        content=ft.Column(
            controls=[ft.ProgressRing(), ft.Text("מכין סביבת עבודה (ExifTool)...", size=16)],
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
        ),
    )

    async def go_to_select(e=None):
        page.dialog = setup_dlg
        setup_dlg.open = True
        page.update()
        try:
            base_dir = Path(resource_path(""))
            ok, msg = await asyncio.to_thread(ensure_exiftool_on_path, base_dir)
        except Exception as err:
            ok, msg = False, f"שגיאה בהכנת ExifTool: {err}"
        setup_dlg.open = False
        page.update()
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()
        page.controls.clear()
        page.add(build_image_select_screen(page, on_back=go_to_media_type))
        page.update()

    def go_to_video_processing(e=None):
        page.controls.clear()
        page.add(build_video_processing_screen())
        page.update()

    def go_to_media_type_sync(e=None):
        # Wrapper for async go_to_media_type
        asyncio.create_task(go_to_media_type(e))

    async def go_to_media_type(e=None):
        page.controls.clear()
        page.add(build_media_type_screen(on_photos=go_to_select, on_videos=go_to_video_processing))
        page.update()

    def go_to_media_type(e=None):
        page.controls.clear()
        page.add(build_media_type_screen(on_photos=go_to_select, on_videos=go_to_video_processing))
        page.update()

    page.add(build_opening_screen(on_start=go_to_media_type_sync))

# ---------------------------------------------------------
# 🔸 הרצה כאפליקציה
# ---------------------------------------------------------
if __name__ == "__main__":
    ft.app(target=main)
