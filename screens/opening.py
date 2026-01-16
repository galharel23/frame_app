# screens/opening.py
from __future__ import annotations

from pathlib import Path

import flet as ft

from consts import DRONE_IMG, LOGO_IMG
from design_system import BORDER_RADIUS_XL, PRIMARY, SPACING_MD, SPACING_XL, TEXT_PRIMARY, TEXT_SECONDARY


def build_opening_screen(on_start):
    # Animated title with gradient effect
    title = (
        ft.Image(src=LOGO_IMG, width=950, height=200, fit=ft.ImageFit.CONTAIN)
        if Path(LOGO_IMG).exists()
        else ft.Text("הלוגו logo.png לא נמצא", size=40, color="#ff8a80")
    )

    # Enhanced start button with modern styling
    start_btn = ft.ElevatedButton(
        text="🚀 בואו נלבין",
        on_click=on_start,
        style=ft.ButtonStyle(
            bgcolor=PRIMARY,
            color=TEXT_PRIMARY,
            padding=ft.Padding(48, 28, 48, 28),
            text_style=ft.TextStyle(size=24, weight=ft.FontWeight.BOLD, letter_spacing=0.5),
            shape=ft.RoundedRectangleBorder(radius=BORDER_RADIUS_XL),
            side=ft.BorderSide(2, PRIMARY),
            shadow_color=PRIMARY,
        ),
    )

    # Subtitle with description
    subtitle = ft.Text(
        "המרה חכמה של תמונות",
        size=16,
        color=TEXT_SECONDARY,
        text_align=ft.TextAlign.CENTER,
        weight=ft.FontWeight.W_500,
    )

    left = ft.Column(
        [
            title,
            ft.Container(height=SPACING_MD),
            subtitle,
            ft.Container(height=SPACING_XL),
            start_btn,
        ],
        spacing=0,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Animated drone image with container
    right_content = (
        ft.Image(src=DRONE_IMG, width=600, height=600, fit=ft.ImageFit.CONTAIN)
        if Path(DRONE_IMG).exists()
        else ft.Text("התמונה Drone.gif לא נמצאה", color="#ff8a80")
    )

    right = ft.Container(content=right_content, padding=ft.Padding(150, 20, 20, 20), alignment=ft.alignment.center_left)

    return ft.Row(
        [
            ft.Container(content=left, expand=6, padding=10),
            ft.Container(content=right, expand=4),
        ],
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
