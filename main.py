import flet as ft
import threading

from typing import Optional

class VexDesktop:
    def __init__(self):
        pass

def main(page: ft.Page):
    page.title = "Vex Desktop Video Editor"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1400
    page.window_height = 900
    page.padding = 10
    page.spacing = 10

    # AppBar
    page.appbar = ft.AppBar(
        title=ft.Text("Vex - AI Video Editor"),
        bgcolor=ft.colors.SURFACE_VARIANT,
        actions=[
            ft.IconButton(ft.icons.SETTINGS, tooltip="Settings"),
            ft.IconButton(ft.icons.EXPORT, tooltip="Export"),
        ],
    )

    # Main layout - Row with preview, chat, timeline
    preview = ft.Container(
        content=ft.Text("Video Preview Area\n\nDrag & drop video here", size=20, text_align=ft.TextAlign.CENTER),
        expand=2,
        bgcolor=ft.colors.BLACK,
        border=ft.border.all(1, ft.colors.WHITE24),
        alignment=ft.alignment.center,
    )

    # Chat panel
    messages = ft.ListView(expand=True, spacing=10, auto_scroll=True)
    input_field = ft.TextField(
        hint_text="Describe your video edit (e.g. 'trim first 10 seconds and add subtitles')",
        expand=True,
        multiline=True,
        shift_enter=True,
    )

    def send_command(e):
        if not input_field.value:
            return
        messages.controls.append(ft.Text(f"You: {input_field.value}", color=ft.colors.BLUE_200))
        page.update()
        # TODO: Call Vex agent in thread
        input_field.value = ""
        page.update()

    chat = ft.Column([
        messages,
        ft.Row([input_field, ft.ElevatedButton("Send", icon=ft.icons.SEND, on_click=send_command)]),
    ], expand=3)

    timeline = ft.Container(
        content=ft.Text("Timeline Panel\nUndo stack, clips, assets", size=16),
        expand=2,
        bgcolor=ft.colors.SURFACE_VARIANT,
        border=ft.border.all(1),
    )

    main_row = ft.Row([preview, chat, timeline], expand=True, spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)

    page.add(main_row)
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
