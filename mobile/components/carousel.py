"""Карусель баннеров: листается свайпом, нажатием на точки и сама раз в несколько секунд."""

import threading
import time
from collections.abc import Callable

import flet as ft

import theme
from components import common as ui

BANNER_HEIGHT = 150


def banner(image: str, title: str, text: str, button: str, on_click=None, color: str = theme.PRIMARY) -> ft.Container:
    """Один баннер: картинка-фон, слева заголовок, пояснение и кнопка-«пилюля»."""
    pill = ft.Container(
        content=ui.txt(button, 12, ui.W_SEMI, color if on_click else theme.WHITE),
        bgcolor=theme.WHITE if on_click else "#33FFFFFF",  # «#AARRGGBB»: у неактивной плашки фон полупрозрачный
        padding=ft.padding.symmetric(horizontal=14, vertical=7),
        border_radius=14,
    )
    return ft.Container(
        height=BANNER_HEIGHT,
        border_radius=22,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        image=ft.DecorationImage(src=image, fit=ft.ImageFit.COVER, alignment=ft.alignment.center_right),
        padding=ft.padding.only(left=18, top=16, bottom=16, right=8),
        on_click=on_click,
        content=ft.Row(
            [
                ft.Column(
                    [
                        ui.txt(title, 19, ui.W_BOLD, theme.WHITE, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ui.txt(text, 12, color=theme.WHITE, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                        pill,
                    ],
                    spacing=6,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    expand=5,
                ),
                ft.Container(expand=4),  # справа остаётся место под рисунок на фоне
            ],
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )


class Carousel:
    """Показывает по одному баннеру. Сама листает, пока экран открыт (is_alive() == True)."""

    def __init__(self, page: ft.Page, slides: list[ft.Control], is_alive: Callable[[], bool], interval: float = 5.0):
        self.page = page
        self.slides = slides
        self.is_alive = is_alive
        self.interval = interval
        self.index = 0
        self._stopped = False
        self._started = False
        self._last_move = time.monotonic()
        self.switcher = ft.AnimatedSwitcher(
            content=slides[0],
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=350,
            reverse_duration=200,
        )
        self.dots = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=6)
        self._draw_dots()
        self.control = ft.Column(
            [
                ft.GestureDetector(
                    content=self.switcher,
                    on_horizontal_drag_end=self._on_swipe,
                ),
                self.dots,
            ],
            spacing=10,
        )

    # ---------- управление ----------

    def start(self) -> None:
        if len(self.slides) > 1 and not self._started and not self._stopped:
            self._started = True
            threading.Thread(target=self._loop, daemon=True).start()

    def stop(self) -> None:
        self._stopped = True

    def show(self, index: int, update: bool = True) -> None:
        self.index = index % len(self.slides)
        self._last_move = time.monotonic()
        self.switcher.content = self.slides[self.index]
        self._draw_dots()
        if update:
            self.control.update()

    def _on_swipe(self, e) -> None:
        velocity = e.primary_velocity or 0
        if abs(velocity) < 150:  # слишком слабое движение — не считаем свайпом
            return
        self.show(self.index + (1 if velocity < 0 else -1))

    def _draw_dots(self) -> None:
        self.dots.controls = [
            ft.Container(
                width=22 if i == self.index else 7,
                height=7,
                border_radius=4,
                bgcolor=theme.PRIMARY if i == self.index else theme.BORDER,
                animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                on_click=lambda e, n=i: self.show(n),
            )
            for i in range(len(self.slides))
        ]

    def _loop(self) -> None:
        while not self._stopped:
            time.sleep(0.5)
            if self._stopped or not self.is_alive():
                return  # экран закрыт или перестроен: поток завершается, новый создаст новая карусель
            if time.monotonic() - self._last_move >= self.interval:
                try:
                    self.show(self.index + 1)
                except Exception:
                    return
