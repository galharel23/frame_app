# screens/video_processing.py
from __future__ import annotations
import flet as ft
import asyncio
import os
import pathlib
from typing import List, Set

from services.srt_service import convert_srt_to_csv
from screens.results import build_results_screen

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
    files_counter = ft.Text("נבחרו 0 קבצי SRT", size=14, color="#cccccc")

    # Error message
    error_text = ft.Text("", color="#ff5252", size=13)

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
        color="#9aa0a6",
        size=12,
        text_align=ft.TextAlign.CENTER,
    )

    drop_list = ft.ListView(height=180, spacing=4, auto_scroll=False)
    drop_area = ft.Container(
        height=200,
        bgcolor="#0f0f0f",
        border=ft.border.all(1, "#303030"),
        border_radius=10,
        alignment=ft.alignment.center,
        content=placeholder_text,
        padding=10,
    )

    def refresh_files_ui():
        count = len(selected_files)
        files_counter.value = f"נבחרו {count} קבצי SRT"
        if count > 0:
            drop_list.controls = [
                ft.Text(_ltr(pathlib.Path(p).name), size=12, color="#bdbdbd", tooltip=p)
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
            
            for srt_file in selected_files:
                success, message, output_path = convert_srt_to_csv(srt_file)
                results.append({
                    "file": pathlib.Path(srt_file).name,
                    "status": "success" if success else "error",
                    "message": message,
                    "output_path": output_path
                })
            
            progress_dlg.open = False
            page.update()
            
            # Navigate to results screen
            page.clean()
            page.add(build_video_results_screen(page, results, on_back=on_back))
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
            ft.Divider(height=1, color="#303030"),
            ft.Column(
                [
                    ft.Text("בחר קבצי SRT להמרה:", size=14, color="#b0bec5"),
                    pick_srt_btn,
                    files_counter,
                    ft.Text("קבצים:", size=12, color="#9aa0a6"),
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


def build_video_results_screen(page: ft.Page, results: list, on_back=None):
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
                        color="#7fd37f" if result["status"] == "success" else "#ff5252"
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

    # Open CSV button (if any successful conversions)
    successful = [r for r in results if r["status"] == "success"]
    
    def open_folder_click(e):
        if successful:
            folder = pathlib.Path(successful[0]["output_path"]).parent
            if folder.exists():
                import subprocess
                subprocess.Popen(f'explorer /select,"{successful[0]["output_path"]}"')

    open_btn = ft.FilledButton(
        f"פתח קטלוג ({len(successful)} CSV)",
        on_click=open_folder_click,
        disabled=len(successful) == 0,
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
        bgcolor="#374151",
        color="white",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
    )

    # Main layout
    content = ft.Column(
        [
            ft.Row(
                [back_btn, ft.Text("הודעות המרה", size=28, weight=ft.FontWeight.BOLD)],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            ft.Divider(height=1, color="#303030"),
            ft.Column(
                [
                    ft.Text(f"פועלו {len(results)} קבצים", size=14, color="#b0bec5"),
                    results_table,
                    open_btn,
                    again_btn,
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
