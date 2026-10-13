"""Точка входа мобильного клиента «Вместе привычнее» (Flet).

Запуск для разработки:  flet run            (из папки mobile/)
Сборка для Android:     flet build apk
"""

import logging

import flet as ft

from core import App

logging.basicConfig(level=logging.INFO)


def main(page: ft.Page) -> None:
    App(page).start()


if __name__ == "__main__":
    ft.app(target=main)
