import flet as ft
from design_system import (TEXT_PRIMARY, BUTTON_SECONDARY, PRIMARY, TEXT_SECONDARY, 
                           SPACING_LG, SPACING_XL, SPACING_MD, BORDER_RADIUS_XL,
                           BG_DARK_2, ACCENT_PURPLE, ACCENT_GREEN, TEXT_TERTIARY)

def build_media_type_screen(on_photos, on_videos):
    """
    Modern media type selection screen with enhanced visual design.
    """
    title = ft.Text(
        "בחרו סוג מדיה לעיבוד",
        size=40,
        weight=ft.FontWeight.BOLD,
        color=TEXT_PRIMARY,
        text_align=ft.TextAlign.CENTER,
    )
    
    subtitle = ft.Text(
        "בחרו את סוג הקבצים להמרה",
        size=14,
        color=TEXT_SECONDARY,
        text_align=ft.TextAlign.CENTER,
    )
    
    # Photos button with modern design
    photos_btn = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.IMAGE, size=48, color=TEXT_PRIMARY),
            ft.Text("תמונות", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Text("עיבוד קבצי תמונה", size=12, color=TEXT_SECONDARY),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        on_click=on_photos,
        padding=ft.Padding(32, 40, 32, 40),
        bgcolor=BUTTON_SECONDARY,
        border_radius=BORDER_RADIUS_XL,
        alignment=ft.alignment.center,
        ink=True,
    )
    
    # Videos button with modern design
    videos_btn = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.VIDEOCAM, size=48, color=TEXT_PRIMARY),
            ft.Text("וידאו", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Text("המרת קבצי וידאו", size=12, color=TEXT_SECONDARY),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        on_click=on_videos,
        padding=ft.Padding(32, 40, 32, 40),
        bgcolor=PRIMARY,
        border_radius=BORDER_RADIUS_XL,
        alignment=ft.alignment.center,
        ink=True,
    )
    
    btn_row = ft.Row([
        ft.Container(content=photos_btn, expand=True),
        ft.Container(width=SPACING_LG),
        ft.Container(content=videos_btn, expand=True),
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=0)
    
    card = ft.Card(
        content=ft.Container(
            width=700,
            padding=SPACING_XL,
            content=ft.Column([
                title,
                ft.Container(height=SPACING_MD),
                subtitle,
                ft.Container(height=SPACING_XL),
                btn_row
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
        )
    )
    return ft.Container(expand=True, alignment=ft.alignment.center, content=card)
