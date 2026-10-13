"""Карточка привычки (главная и профиль) и кнопка-отметка."""

import flet as ft

import theme
from components import common as ui


def category_colors(category: str | None) -> tuple[str, str]:
    return theme.CATEGORY_COLORS.get(category or "", theme.DEFAULT_CATEGORY_COLORS)


def partners_of(habit: dict) -> list[dict]:
    return [m for m in habit["members"] if not m["is_me"] and m["status"] == "active"]


def check_button(status: str, on_click, size=34) -> ft.Container:
    """Кружок отметки: выполнено / срыв / ждёт отметки / сегодня отдых."""
    common = dict(width=size, height=size, border_radius=size / 2, alignment=ft.alignment.center, on_click=on_click)
    if status == "done":
        return ft.Container(bgcolor=theme.GREEN, content=ft.Icon(ui.icon("CHECK"), color=theme.WHITE, size=20), **common)
    if status == "missed":
        return ft.Container(bgcolor=theme.RED_SOFT, content=ft.Icon(ui.icon("CLOSE"), color=theme.RED, size=20), **common)
    if status == "off":
        return ft.Container(bgcolor=theme.BG, content=ft.Icon(ui.icon("BEDTIME"), color=theme.MUTED, size=18), **common)
    return ft.Container(border=ft.border.all(2, theme.BORDER), **common)


def streak_text(current: int) -> str:
    return f"{ui.days_text(current)} подряд" if current > 0 else "Начните серию"


def habit_card(app, habit: dict, on_open, on_toggle) -> ft.Container:
    bg, fg = category_colors(habit.get("category"))
    partners = partners_of(habit)
    if partners:
        subtitle = "Вместе с: " + ", ".join(p["name"] for p in partners)
    else:
        subtitle = habit.get("goal") or "Пока без напарника"
    planned = habit.get("week_planned") or 0
    percent = round(100 * habit.get("week_done", 0) / planned) if planned else 0

    return ui.card(
        ft.Row(
            [
                ui.circle_icon(habit.get("icon") or "CHECK_CIRCLE_OUTLINE", bg, fg, 48),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(habit["title"], size=16, weight=ui.W_BOLD, color=theme.TEXT,
                                        expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                check_button(habit["today_status"], on_toggle),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ui.muted(subtitle, 12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ui.progress(percent),
                        ft.Row(
                            [
                                ui.muted(streak_text(habit["current_streak"]), 12),
                                ft.Row(
                                    [
                                        ft.Icon(ui.icon("LOCAL_FIRE_DEPARTMENT"), color=theme.ORANGE, size=14),
                                        ui.muted(f"Рекорд: {ui.days_text(habit['best_streak'])}", 12),
                                    ],
                                    spacing=2,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=6,
                    expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=12,
        ),
        padding=14,
        on_click=on_open,
    )
