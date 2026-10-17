"""Выбор иконки и цвета для своей привычки."""

import flet as ft

import theme
from components import common as ui


class IconPicker:
    """Ряд цветов и сетка иконок. Выбранное лежит в .icon и .color, сам блок — в .control."""

    def __init__(self, icon: str | None = None, color: str | None = None):
        self.initial_icon = icon
        self.initial_color = color
        self.icon = icon
        self.color = color
        self.control = ft.Column(spacing=12)
        self._render()

    @property
    def changes(self) -> dict:
        """Что пользователь поменял: только эти поля нужно отправлять при правке привычки."""
        result = {}
        if self.icon != self.initial_icon:
            result["icon"] = self.icon
        if self.color != self.initial_color:
            result["color"] = self.color
        return result

    def _render(self) -> None:
        soft, strong = theme.HABIT_COLORS.get(self.color or "", theme.DEFAULT_CATEGORY_COLORS)
        swatches = [
            ft.Container(
                width=34,
                height=34,
                border_radius=17,
                bgcolor=theme.HABIT_COLORS[key][1],
                alignment=ft.alignment.center,
                border=ft.border.all(3, theme.TEXT) if key == self.color else None,
                content=ft.Icon(ui.icon("CHECK"), color=theme.WHITE, size=18) if key == self.color else None,
                on_click=lambda e, k=key: self._pick_color(k),
            )
            for key in theme.HABIT_COLORS
        ]
        icons = [
            ft.Container(
                width=46,
                height=46,
                border_radius=23,
                alignment=ft.alignment.center,
                bgcolor=soft if name == self.icon else theme.CARD,
                border=ft.border.all(2, strong if name == self.icon else theme.BORDER),
                content=ft.Icon(ui.icon(name), color=strong if name == self.icon else theme.MUTED, size=24),
                on_click=lambda e, n=name: self._pick_icon(n),
            )
            for name in theme.HABIT_ICONS
        ]
        self.control.controls = [
            ft.Row(swatches, spacing=10),
            ft.Row(icons, wrap=True, spacing=8, run_spacing=8),
        ]

    def _pick_color(self, key: str) -> None:
        self.color = key
        self._render()
        self.control.update()

    def _pick_icon(self, name: str) -> None:
        self.icon = name
        self._render()
        self.control.update()
