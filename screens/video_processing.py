# screens/video_processing.py
from __future__ import annotations
import flet as ft
import asyncio
import os
import pathlib
from typing import List, Set

from services.srt_service import convert_srt_to_csv
from screens.results import build_results_screen
from design_system import TEXT_SECONDARY, ERROR, TEXT_TERTIARY, BG_DARK_2, BORDER_COLOR, BORDER_RADIUS_MD, SUCCESS, BUTTON_SECONDARY, TEXT_PRIMARY

SRT_EXT = {".srt"}


def _is_srt(p: str) -> bool:
    return pathlib.Path(p).suffix.lower() in SRT_EXT


# RTL support
_LRM = "\u200E"
def _ltr(s: str) -> str:
    return f"{_LRM}{s}{_LRM}"


def build_video_processing_screen(page: ft.Page, on_back=None):
    """
    Video processing screen - Convert SRT files to CSV with GPS data.
    Supports file picker and drag-drop.
    """
    # Set page RTL layout
    page.rtl = True
    page.appbar = None

    # State
    selected_files: Set[str] = set()
    files_counter = ft.Text("נבחרו 0 קבצי SRT", size=14, color=TEXT_SECONDARY)

    # Error message
    error_text = ft.Text("", color=ERROR, size=13)

    # Progress dialog
    progress_dlg = ft.AlertDialog(
        modal=True,
        content=ft.Column(
            [ft.ProgressRing(), ft.Text("מעבד קבצי SRT ל-CSV...", size=16)],
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=16,
        ),
    )

    # File pickers
    srt_picker = ft.FilePicker(
        on_result=lambda e: (
            selected_files.update(
                [f.path for f in (e.files or []) if f.path and _is_srt(f.path)]
            ),
            setattr(error_text, "value", ""),
            refresh_files_ui(),
        )
    )
    page.overlay.append(srt_picker)

    # Drop area display
    placeholder_text = ft.Text(
        _ltr("גרור קבצי SRT לכאן או השתמש בכפתור לעיל"),
        color=TEXT_TERTIARY,
        size=12,
        text_align=ft.TextAlign.CENTER,
    )

    drop_list = ft.ListView(height=180, spacing=4, auto_scroll=False)
    drop_area = ft.Container(
        height=200,
        bgcolor=BG_DARK_2,
        border=ft.border.all(1, BORDER_COLOR),
        border_radius=BORDER_RADIUS_MD,
        alignment=ft.alignment.center,
        content=placeholder_text,
        padding=10,
    )

    def refresh_files_ui():
        count = len(selected_files)
        files_counter.value = f"נבחרו {count} קבצי SRT"
        if count > 0:
            drop_list.controls = [
                ft.Text(_ltr(pathlib.Path(p).name), size=12, color=TEXT_SECONDARY, tooltip=p)
                for p in sorted(selected_files)
            ]
            drop_area.content = drop_list
        else:
            drop_area.content = placeholder_text
        page.update()

    # Drag & Drop handler
    def handle_page_drop(e):
        added = 0
        for f in (e.files or []):
            if f.path and _is_srt(f.path) and f.path not in selected_files:
                selected_files.add(f.path)
                added += 1
        if added == 0:
            page.snack_bar = ft.SnackBar(
                ft.Text("לא נוספו קבצי SRT (ודא שהם .srt)")
            )
            page.snack_bar.open = True
        error_text.value = ""
        refresh_files_ui()

    try:
        page.on_drop = handle_page_drop
    except Exception:
        pass

    # Process button handler
    async def on_process_click(e):
        if not selected_files:
            error_text.value = "בחר לפחות קובץ SRT אחד"
            page.update()
            return

        page.dialog = progress_dlg
        progress_dlg.open = True
        page.update()

        try:
            results = []
            session_folder = None
            
            for srt_file in selected_files:
                success, message, output_folder = convert_srt_to_csv(srt_file)
                
                # Capture the session folder from first conversion
                if output_folder and not session_folder:
                    session_folder = str(output_folder.parent)
                
                results.append({
                    "file": pathlib.Path(srt_file).name,
                    "status": "success" if success else "error",
                    "message": message,
                    "output_folder": str(output_folder) if output_folder else None
                })
            
            progress_dlg.open = False
            page.update()
            
            # Navigate to results screen
            page.clean()
            page.add(build_video_results_screen(page, results, session_folder=session_folder, on_back=on_back))
            page.update()

        except Exception as err:
            progress_dlg.open = False
            error_text.value = f"שגיאה: {str(err)}"
            page.update()

    # UI Controls
    pick_srt_btn = ft.FilledButton(
        "בחר קבצי SRT...",
        on_click=lambda _: srt_picker.pick_files(
            allow_multiple=True, allowed_extensions=["srt"]
        ),
        width=300,
    )

    process_btn = ft.FilledButton(
        "המר ל-CSV",
        on_click=on_process_click,
        width=300,
        disabled=True,
    )

    def update_process_btn_state(e=None):
        process_btn.disabled = len(selected_files) == 0
        page.update()

    # Override refresh_files_ui to also update button state
    original_refresh = refresh_files_ui
    def refresh_files_ui():
        original_refresh()
        update_process_btn_state()

    # Back button handler
    def on_back_click(e):
        if on_back:
            if asyncio.iscoroutinefunction(on_back):
                asyncio.create_task(on_back(e))
            else:
                on_back(e)

    back_btn = ft.IconButton(
        ft.Icons.ARROW_BACK,
        icon_size=24,
        tooltip="Back",
        on_click=on_back_click,
    )

    # Main layout
    content = ft.Column(
        [
            ft.Row(
                [back_btn, ft.Text("עיבוד וידאו - SRT ל-CSV", size=28, weight=ft.FontWeight.BOLD)],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            ft.Divider(height=1, color=BORDER_COLOR),
            ft.Column(
                [
                    ft.Text("בחר קבצי SRT להמרה:", size=14, color=TEXT_SECONDARY),
                    pick_srt_btn,
                    files_counter,
                    ft.Text("קבצים:", size=12, color=TEXT_TERTIARY),
                    drop_area,
                    error_text,
                    process_btn,
                ],
                expand=True,
                spacing=16,
            ),
        ],
        expand=True,
        spacing=16,
    )

    return ft.Container(
        expand=True,
        padding=32,
        content=content,
    )


def build_video_results_screen(page: ft.Page, results: list, session_folder: str = None, on_back=None):
    """
    Display results of SRT to CSV conversion.
    """
    page.rtl = True
    page.appbar = None

    # Back button
    def on_back_click(e):
        if on_back:
            if asyncio.iscoroutinefunction(on_back):
                asyncio.create_task(on_back(e))
            else:
                on_back(e)

    back_btn = ft.IconButton(
        ft.Icons.ARROW_BACK,
        icon_size=24,
        tooltip="Back",
        on_click=on_back_click,
    )

    # Results table
    table_rows = []
    for result in results:
        table_rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(result["file"], size=11)),
                    ft.DataCell(ft.Text(
                        result["status"].upper(),
                        size=11,
                        color=SUCCESS if result["status"] == "success" else ERROR
                    )),
                    ft.DataCell(ft.Text(result["message"], size=11)),
                ],
            )
        )

    results_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("קובץ")),
            ft.DataColumn(ft.Text("סטטוס")),
            ft.DataColumn(ft.Text("הודעה")),
        ],
        rows=table_rows,
    )

    # Open folder button
    def open_folder_click(e):
        if session_folder and pathlib.Path(session_folder).exists():
            import subprocess
            subprocess.Popen(f'explorer "{session_folder}"')

    open_btn = ft.FilledButton(
        "פתח תיקייה",
        on_click=open_folder_click,
        disabled=not session_folder or not pathlib.Path(session_folder).exists(),
    )

    # "Additional Whitening" button
    def on_again_click(e):
        if on_back:
            if asyncio.iscoroutinefunction(on_back):
                asyncio.create_task(on_back(e))
            else:
                on_back(e)

    again_btn = ft.ElevatedButton(
        text="המרה נוספת",
        icon=ft.Icons.AUTORENEW,
        on_click=on_again_click,
        bgcolor=BUTTON_SECONDARY,
        color=TEXT_PRIMARY,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
    )

    # Main layout with scrollable results table
    content = ft.Column(
        [
            ft.Row(
                [back_btn, ft.Text("הודעות המרה", size=28, weight=ft.FontWeight.BOLD)],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            ft.Divider(height=1, color=BORDER_COLOR),
            # Scrollable results area
            ft.Column(
                [
                    ft.Text(f"פועלו {len(results)} קבצים", size=14, color=TEXT_SECONDARY),
                    ft.Container(
                        content=results_table,
                        height=400,
                    ),
                ],
                expand=True,
                spacing=16,
            ),
            # Fixed button area (always visible)
            ft.Column(
                [
                    open_btn,
                    again_btn,
                ],
                spacing=16,
            ),
        ],
        expand=True,
        spacing=16,
    )

    return ft.Container(
        expand=True,
        padding=32,
        content=content,
    )
