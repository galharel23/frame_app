# screens/image_select.py
from __future__ import annotations
import flet as ft
import asyncio, os, pathlib
from typing import List, Set
import logging

from utils.pipeline import run_whitening
from screens.results import build_results_screen
from screens.opening import build_opening_screen
from design_system import (
    BG_DARK_1, BG_DARK_2, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, 
    PRIMARY, ERROR, BORDER_COLOR, SPACING_LG, BORDER_RADIUS_MD, SPACING_SM, SPACING_MD, SPACING_XL
)

# Setup logger
logger = logging.getLogger(__name__)

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}


def _is_image(p: str) -> bool:
    return pathlib.Path(p).suffix.lower() in IMAGE_EXT


def _gather_images_in_dir(dir_path: str) -> List[str]:
    paths: List[str] = []
    for root, _, files in os.walk(dir_path):
        for f in files:
            full = os.path.join(root, f)
            if _is_image(full):
                paths.append(full)
    return paths


#  RTL
_LRM = "\u200E"
def _ltr(s: str) -> str:
    return f"{_LRM}{s}{_LRM}"


def build_image_select_screen(page: ft.Page, on_back=None, initial_files=None, initial_drone=None):
    # --- Global layout direction ---
    page.rtl = True
    page.appbar = None
    page.overlay.clear()

    # --- State ---
    selected_drone = ft.Dropdown(
        options=[
            ft.dropdown.Option("DJI M350 RTK"),
            ft.dropdown.Option("DJI Padam"),
            ft.dropdown.Option("Autel Alpha"),
            ft.dropdown.Option("EVO Max 4N"),
        ],
        label="סוג הרחפן",
        hint_text="בחרו את הדגם",
        autofocus=True,
        width=320,
        value=initial_drone or "DJI M350 RTK",  # ברירת מחדל
    )

    # 🔻 LOG selection is now disabled – no log file used in the flow
    # log_file = {"path": None}
    # selected_log_path = ft.Text("לא נבחר קובץ log", color="#9aa0a6", size=13)

    selected_files: Set[str] = set(initial_files or [])
    files_counter = ft.Text(f"נבחרו {len(selected_files)} קבצי תמונה", size=14, color=TEXT_SECONDARY)

    # error msg
    error_text = ft.Text("", color=ERROR, size=13)

    progress_dlg = ft.AlertDialog(
        modal=True,
        content=ft.Column(
            [ft.ProgressRing(), ft.Text("מריץ הלבנה ואריזה ל-ZIP...", size=16)],
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=16,
        ),
    )

    # --- Pickers ---
    # 🔻 Remove log picker from UI/logic
    # log_picker = ft.FilePicker(
    #     on_result=lambda e: (
    #         log_file.__setitem__("path", e.files[0].path if (e.files and e.files[0].path) else None),
    #         setattr(
    #             selected_log_path,
    #             "value",
    #             e.files[0].path if (e.files and e.files[0].path) else "לא נבחר קובץ log",
    #         ),
    #         setattr(selected_log_path, "color", "#9aa0a6"),
    #         setattr(error_text, "value", ""),
    #         page.update(),
    #     )
    # )
    # page.overlay.append(log_picker)

    imgs_picker = ft.FilePicker(
        on_result=lambda e: (
            selected_files.update(
                [f.path for f in (e.files or []) if f.path and _is_image(f.path)]
            ),
            setattr(error_text, "value", ""),
            refresh_files_ui(),
        )
    )
    page.overlay.append(imgs_picker)

    dir_picker = ft.FilePicker(
        on_result=lambda e: (
            selected_files.update(_gather_images_in_dir(e.path))
            if (getattr(e, "path", None))
            else None,
            setattr(error_text, "value", ""),
            refresh_files_ui(),
        )
    )
    page.overlay.append(dir_picker)

    # --- "ריבוע" המרכז – מציג שמות קבצים (עם גלילה) ---
    placeholder_text = ft.Text(
        _ltr("גררו תמונות/תיקיות לכאן או השתמשו בכפתורים למעלה"),
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

    next_btn = None

    def refresh_files_ui():
        count = len(selected_files)
        files_counter.value = f"נבחרו {count} קבצי תמונה"
        if count > 0:
            drop_list.controls = [
                ft.Text(_ltr(pathlib.Path(p).name), size=12, color=TEXT_SECONDARY, tooltip=p)
                for p in sorted(selected_files)
            ]
            drop_area.content = drop_list
        else:
            drop_area.content = placeholder_text

        if next_btn is not None:
            next_btn.disabled = count == 0

        page.update()

    # --- Drag & Drop מכל האפליקציה ---
    def handle_page_drop(e):
        added = 0
        for f in (e.files or []):
            if f.path:
                if os.path.isdir(f.path):
                    for p in _gather_images_in_dir(f.path):
                        if p not in selected_files:
                            selected_files.add(p)
                            added += 1
                elif _is_image(f.path) and f.path not in selected_files:
                    selected_files.add(f.path)
                    added += 1
        if added == 0:
            page.snack_bar = ft.SnackBar(
                ft.Text("לא נוספו קבצים (ודאו שמדובר בתמונות/תיקיות)")
            )
            page.snack_bar.open = True
        error_text.value = ""
        refresh_files_ui()

    try:
        page.on_drop = handle_page_drop
    except Exception:
        pass

    # --- Controls ---

    # 🔻 Log controls removed
    # pick_log_btn = ft.TextButton(
    #     "בחרו קובץ לוג…",
    #     on_click=lambda _: log_picker.pick_files(
    #         allow_multiple=False, allowed_extensions=["log", "txt", "csv"]
    #     ),
    # )

    # def on_no_log_toggle(e):
    #     if no_log_cb.value:
    #         pick_log_btn.disabled = True
    #         selected_log_path.value = "לא נדרש קובץ log"
    #         selected_log_path.color = "#7fd37f"
    #         log_file["path"] = None
    #     else:
    #         pick_log_btn.disabled = False
    #         selected_log_path.value = "לא נבחר קובץ log"
    #         selected_log_path.color = "#9aa0a6"
    #     error_text.value = ""
    #     page.update()

    # no_log_cb = ft.Checkbox(
    #     label="אין קובץ לוג (דלג)", value=False, on_change=on_no_log_toggle
    # )

    add_folder_btn = ft.FilledButton(
        "בחרו תיקייה…", on_click=lambda _: dir_picker.get_directory_path()
    )
    add_files_btn = ft.OutlinedButton(
        "בחרו תמונות…",
        on_click=lambda _: imgs_picker.pick_files(
            allow_multiple=True, file_type=ft.FilePickerFileType.IMAGE
        ),
    )
    clear_btn = ft.IconButton(
        icon=ft.Icons.DELETE_OUTLINE,
        tooltip="נקה בחירה",
        on_click=lambda _: (
            selected_files.clear(),
            setattr(error_text, "value", ""),
            refresh_files_ui(),
        ),
    )

    def on_next_clicked(e):
        # Basic validation
        error_text.value = ""
        problems = []
        if not selected_drone.value:
            problems.append("• לא נבחר סוג רחפן")
        if len(selected_files) == 0:
            problems.append("• לא נבחרו תמונות")

        if problems:
            error_text.value = "\n".join(problems)
            page.update()
            return

        try:
            page.controls.clear()
            page.add(build_image_filter_screen(
                page,
                selected_files=list(selected_files),
                selected_drone=selected_drone.value,
                on_back=on_back,
            ))
        except Exception as err:
            error_text.value = f"שגיאה בפתיחת מסך הסינון: {err}"
        finally:
            page.update()

    next_btn = ft.ElevatedButton(
        "הבא: הגדר סינון",
        bgcolor=PRIMARY,
        color=TEXT_PRIMARY,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=on_next_clicked,
    )
    refresh_files_ui()

    def build_image_filter_screen(page: ft.Page, selected_files: list[str], selected_drone: str, on_back=None):
        page.rtl = True
        page.appbar = None

        screen_title = ft.Text(
            "הגדרות סינון לעיבוד",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=TEXT_PRIMARY,
        )
        screen_subtitle = ft.Text(
            "בחרו אילו סוגי תמונות לעבד ואיזה טווח גובה לשמור.",
            size=11,
            color=TEXT_TERTIARY,
        )

        selected_count = len(selected_files)
        
        selected_label = ft.Text(
            f"סינון {selected_count} תמונות שנבחרו עבור {selected_drone}",
            size=12,
            color=TEXT_PRIMARY,
        )

        filter_description = ft.Text(
            "בחרו את הקריטריונים לעיבוד הסופי:",
            size=11,
            color=TEXT_SECONDARY,
        )

        sensor_type_picker = ft.Dropdown(
            label="בחר סוג תמונה לעיבוד",
            options=[
                ft.dropdown.Option("W"),
                ft.dropdown.Option("Z"),
                ft.dropdown.Option("T"),
            ],
            value="W",
            width=180,
            hint_text="בחר סוג תמונה",
        )

        min_altitude_field = ft.TextField(
            label="גובה מינימלי (מטר)",
            value="200",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        max_altitude_field = ft.TextField(
            label="גובה מרבי (מטר)",
            value="5000",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        # Quality filter section
        quality_filter_enabled_cb = ft.Checkbox(
            label="להפעיל סינון איכות תמונות",
            value=True,
            width=280,
        )

        quality_filter_title = ft.Text(
            "הגדרות סינון איכות",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=TEXT_PRIMARY,
        )

        # Distance between images
        min_distance_field = ft.TextField(
            label="מרחק מינימלי בין תמונות (מטר)",
            value="200.0",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        # Speed
        max_speed_field = ft.TextField(
            label="מהירות רחפן מקסימלית (m/s)",
            value="5.0",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        # Digital zoom
        max_zoom_field = ft.TextField(
            label="זום דיגיטלי מקסימלי",
            value="1.0",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        # Blur score
        min_blur_field = ft.TextField(
            label="Blur score מינימלי",
            value="500.0",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        # Image dimensions
        min_width_field = ft.TextField(
            label="רוחב תמונה מינימלי (פיקסל)",
            value="3000",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        min_height_field = ft.TextField(
            label="גובה תמונה מינימלי (פיקסל)",
            value="2000",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        # ISO
        max_iso_field = ft.TextField(
            label="ISO מקסימלי",
            value="1600",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        # Brightness
        min_brightness_field = ft.TextField(
            label="בהירות מינימלית",
            value="20.0",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        max_brightness_field = ft.TextField(
            label="בהירות מקסימלית",
            value="240.0",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        error_text = ft.Text("", color=ERROR, size=11)

        progress_dlg = ft.AlertDialog(
            modal=True,
            content=ft.Column(
                [ft.ProgressRing(), ft.Text("מריץ עיבוד...", size=14)],
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=16,
            ),
        )

        async def on_process_clicked(e):
            problems = []
            if selected_count == 0:
                problems.append("• לא נבחרו תמונות לעיבוד")
            if not sensor_type_picker.value:
                problems.append("• יש לבחור לפחות סוג תמונה אחד לסינון")

            try:
                min_altitude = float(min_altitude_field.value or "0")
            except Exception:
                problems.append("• יש להזין גובה מינימלי תקין")
                min_altitude = 0.0

            try:
                max_altitude = float(max_altitude_field.value or "0")
            except Exception:
                problems.append("• יש להזין גובה מרבי תקין")
                max_altitude = 0.0

            if min_altitude < 0:
                problems.append("• הגובה המינימלי חייב להיות חיובי")
            if max_altitude > 0 and max_altitude < min_altitude:
                problems.append("• הגובה המרבי חייב להיות גדול מהגובה המינימלי")

            quality_filter = {
                "enabled": quality_filter_enabled_cb.value,
                "selected_sensor_suffix": sensor_type_picker.value,
                "min_distance_meters": 200.0,
                "max_speed_mps": 5.0,
                "max_digital_zoom": 1.0,
                "min_blur_score": 500.0,
                "min_width": 3000,
                "min_height": 2000,
                "max_iso": 1600,
                "min_brightness": 20.0,
                "max_brightness": 240.0,
            }

            if quality_filter_enabled_cb.value:
                try:
                    quality_filter["min_distance_meters"] = float(min_distance_field.value or "200.0")
                except Exception:
                    problems.append("• יש להזין מרחק מינימלי תקין")

                try:
                    quality_filter["max_speed_mps"] = float(max_speed_field.value or "5.0")
                except Exception:
                    problems.append("• יש להזין מהירות מקסימלית תקינה")

                try:
                    quality_filter["max_digital_zoom"] = float(max_zoom_field.value or "1.0")
                except Exception:
                    problems.append("• יש להזין זום דיגיטלי תקין")

                try:
                    quality_filter["min_blur_score"] = float(min_blur_field.value or "500.0")
                except Exception:
                    problems.append("• יש להזין Blur score תקין")

                try:
                    quality_filter["min_width"] = int(min_width_field.value or "3000")
                except Exception:
                    problems.append("• יש להזין רוחב מינימלי תקין")

                try:
                    quality_filter["min_height"] = int(min_height_field.value or "2000")
                except Exception:
                    problems.append("• יש להזין גובה מינימלי תקין")

                try:
                    quality_filter["max_iso"] = int(max_iso_field.value or "1600")
                except Exception:
                    problems.append("• יש להזין ISO מקסימלי תקין")

                try:
                    quality_filter["min_brightness"] = float(min_brightness_field.value or "20.0")
                except Exception:
                    problems.append("• יש להזין בהירות מינימלית תקינה")

                try:
                    quality_filter["max_brightness"] = float(max_brightness_field.value or "240.0")
                except Exception:
                    problems.append("• יש להזין בהירות מקסימלית תקינה")

            if problems:
                error_text.value = "\n".join(problems)
                page.update()
                return

            process_btn.disabled = True
            process_btn.text = None
            process_btn.content = ft.Row(
                [
                    ft.ProgressRing(width=18, height=18),
                    ft.Text("מעבד תמונות...", color=TEXT_PRIMARY),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            page.dialog = progress_dlg
            progress_dlg.open = True
            page.update()

            try:
                result = await asyncio.to_thread(
                    run_whitening,
                    selected_files,
                    selected_drone,
                    None,
                    True,
                    quality_filter,
                )
            except Exception as err:
                progress_dlg.open = False
                process_btn.disabled = False
                process_btn.content = None
                process_btn.text = "עיבוד תמונות"
                error_text.value = f"שגיאה בעיבוד: {err}"
                page.update()
                return
            finally:
                progress_dlg.open = False
                process_btn.disabled = False
                process_btn.content = None
                process_btn.text = "עיבוד תמונות"

            page.controls.clear()
            def on_media_type_btn(e=None):
                if on_back:
                    if asyncio.iscoroutinefunction(on_back):
                        asyncio.create_task(on_back(e))
                    else:
                        on_back(e)
            page.add(build_results_screen(page, result, on_again=back_to_select, on_media_type=on_media_type_btn))
            page.update()

        process_btn = ft.ElevatedButton(
            "עיבוד תמונות",
            bgcolor=PRIMARY,
            color=TEXT_PRIMARY,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            width=150,
            on_click=on_process_clicked,
        )

        filter_controls = ft.Column(
            [
                screen_title,
                screen_subtitle,
                ft.Divider(opacity=0.15),
                selected_label,
                filter_description,
                sensor_type_picker,
                ft.Row([min_altitude_field, max_altitude_field], spacing=12),
                ft.Divider(opacity=0.1),
                quality_filter_enabled_cb,
                quality_filter_title,
                ft.Row([min_distance_field, max_speed_field], spacing=12),
                ft.Row([max_zoom_field, min_blur_field], spacing=12),
                ft.Row([min_width_field, min_height_field], spacing=12),
                ft.Row([max_iso_field], spacing=12),
                ft.Row([min_brightness_field, max_brightness_field], spacing=12),
                ft.Container(height=4),
                process_btn,
                ft.Container(height=4),
                error_text,
            ],
            spacing=6,
            width=720,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )

        # Wrap in scrollable column for accessibility
        scrollable_controls = ft.Column(
            [filter_controls],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        def back_to_select(_):
            page.controls.clear()
            page.add(build_image_select_screen(
                page,
                on_back=on_back,
                initial_files=selected_files,
                initial_drone=selected_drone,
            ))
            page.update()

        back_btn = ft.TextButton(
            "חזרה לבחירת תמונות",
            icon=ft.Icons.ARROW_BACK,
            on_click=back_to_select,
            style=ft.ButtonStyle(
                padding=ft.Padding(12, 8, 12, 8),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
        )

        return ft.Column(
            controls=[
                ft.Container(content=back_btn, alignment=ft.alignment.top_right, padding=ft.Padding(0, 16, 16, 0)),
                ft.Container(expand=True, alignment=ft.alignment.center, content=ft.Card(content=ft.Container(padding=16, content=scrollable_controls))),
            ],
            expand=True,
        )

    # --- Helper: button loading state ---
    def set_button_loading(is_loading: bool):
        if is_loading:
            next_btn.disabled = True
            next_btn.content = ft.Row(
                [
                    ft.ProgressRing(width=16, height=16),
                    ft.Text("טוען...", color="white"),
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            next_btn.text = None
        else:
            next_btn.disabled = False
            next_btn.content = None
            next_btn.text = "הבא: הגדר סינון"
        page.update()

    # ---- Back button (top-right) ----
    def back_to_media_type(_):
        if on_back:
            on_back(_)
        else:
            page.controls.clear()
            page.update()

    back_btn = ft.TextButton(
        "חזרה לבחירת סוג מדיה",
        icon=ft.Icons.ARROW_BACK,
        on_click=back_to_media_type,
        style=ft.ButtonStyle(
            padding=ft.Padding(12, 8, 12, 8),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
    )

    back_btn_container = ft.Container(
        content=back_btn,
        alignment=ft.alignment.top_right,
        padding=ft.Padding(0, 16, 16, 0),
    )

    # --- Layout ---
    header = ft.Text("🖼️ בחירת התמונות", size=36, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
    subtitle = ft.Text("בחרו תמונות להלבנה", size=14, color=TEXT_SECONDARY)
    
    header_section = ft.Container(
        content=ft.Column([header, subtitle], spacing=SPACING_SM, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(0, SPACING_LG, 0, SPACING_XL),
    )

    # Enhanced drop area with better visual design
    placeholder_icon = ft.Icon(ft.Icons.CLOUD_UPLOAD, size=64, color=TEXT_TERTIARY)
    enhanced_placeholder = ft.Column([
        placeholder_icon,
        ft.Text(
            "גררו תמונות או תיקיות לכאן",
            size=14,
            weight=ft.FontWeight.W_600,
            color=TEXT_TERTIARY,
            text_align=ft.TextAlign.CENTER,
        ),
        ft.Text(
            "או השתמשו בכפתורים למעלה",
            size=12,
            color=TEXT_TERTIARY,
            text_align=ft.TextAlign.CENTER,
        ),
    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=SPACING_MD)
    
    drop_area.content = enhanced_placeholder
    drop_area.height = 240
    drop_area.bgcolor = BG_DARK_2
    
    # Better button group styling
    button_group = ft.Container(
        content=ft.Row([
            ft.Container(content=add_folder_btn, expand=True),
            ft.Container(content=add_files_btn, expand=True),
            ft.Container(content=clear_btn, expand=False),
        ], spacing=SPACING_MD),
        padding=ft.Padding(0, SPACING_MD, 0, SPACING_MD),
    )

    body = ft.Column(
        [
            header_section,
            selected_drone,
            ft.Divider(opacity=0.1, height=1),
            ft.Text("📁 הוספת תמונות", size=14, weight=ft.FontWeight.W_600, color=TEXT_SECONDARY),
            button_group,
            ft.Row([files_counter], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            drop_area,
            ft.Container(height=6),
            ft.Row([next_btn], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([error_text], alignment=ft.MainAxisAlignment.CENTER),
        ],
        spacing=12,
        width=640,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )

    main_card = ft.Card(content=ft.Container(padding=24, content=body))

    return ft.Column(
        controls=[
            back_btn_container,
            ft.Container(expand=True, alignment=ft.alignment.center, content=main_card),
        ],
        expand=True,
    )
