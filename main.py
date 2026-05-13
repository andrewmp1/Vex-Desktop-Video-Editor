import flet as ft
import threading

# TODO: Import your Vex wrapper
# from vex_desktop.agent import VexAgent

def main(page: ft.Page):
    page.title = "Vex Desktop Video Editor"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window_width = 1400
    page.window_height = 900

    # Placeholder UI
    page.add(ft.Text("Vex Desktop - Coming soon!", size=30))
    # Add video preview, chat, timeline here...

ft.app(target=main)