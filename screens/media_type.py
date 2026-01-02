import flet as ft

def build_media_type_screen(on_photos, on_videos):
    """
    Screen with two buttons: Photos and Videos.
    """
    title = ft.Text("בחרו סוג מדיה לעיבוד", size=36, weight=ft.FontWeight.BOLD, color="#eeeeee")
    photos_btn = ft.ElevatedButton(
        text="תמונות",
        on_click=on_photos,
        style=ft.ButtonStyle(
            bgcolor="#4caf50",
            color="#ffffff",
            padding=ft.Padding(44, 32, 44, 32),
            text_style=ft.TextStyle(size=26, weight=ft.FontWeight.BOLD),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )
    videos_btn = ft.ElevatedButton(
        text="וידאו",
        on_click=on_videos,
        style=ft.ButtonStyle(
            bgcolor="#2196f3",
            color="#ffffff",
            padding=ft.Padding(44, 32, 44, 32),
            text_style=ft.TextStyle(size=26, weight=ft.FontWeight.BOLD),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )
    btn_row = ft.Row([
        photos_btn,
        videos_btn
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=40)
    card = ft.Card(
        content=ft.Container(
            width=500,
            padding=32,
            content=ft.Column([
                title,
                ft.Container(height=40),
                btn_row
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=24)
        )
    )
    return ft.Container(expand=True, alignment=ft.alignment.center, content=card)
