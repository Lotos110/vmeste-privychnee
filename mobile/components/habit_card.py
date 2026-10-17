"""Карточка привычки (главная и профиль) и кнопка-отметка."""

import flet as ft

import theme
from components import common as ui

WEEKDAY_LETTERS = ["П", "В", "С", "Ч", "П", "С", "В"]  # Пн ... Вс


def category_colors(category: str | None) -> tuple[str, str]:
    return theme.CATEGORY_COLORS.get(category or "", theme.DEFAULT_CATEGORY_COLORS)


def partners_of(habit: dict) -> list[dict]:
    return [m for m in habit["members"] if not m["is_me"] and m["status"] == "active"]


def check_button(status: str, on_click, size=34, pop=False) -> ft.Container:
    """Кружок отметки: выполнено / срыв / ждёт отметки / сегодня отдых.

    pop=True: «выполнено» рисуется уменьшенным и с анимацией; чтобы кружок «выпрыгнул»,
    после показа экрана ему нужно выставить scale = 1 (это делает HomeScreen).
    """
    common = dict(width=size, height=size, border_radius=size / 2, alignment=ft.alignment.center, on_click=on_click)
    if status == "done":
        extra = {}
        if pop:
            extra = dict(scale=0.3, animate_scale=ft.Animation(450, ft.AnimationCurve.ELASTIC_OUT))
        return ft.Container(
            bgcolor=theme.GREEN,
            content=ft.Icon(ui.icon("CHECK"), color=theme.WHITE, size=size * 0.58),
            **common,
            **extra,
        )
    if status == "missed":
        return ft.Container(bgcolor=theme.RED_SOFT, content=ft.Icon(ui.icon("CLOSE"), color=theme.RED, size=size * 0.58), **common)
    if status == "off":
        return ft.Container(bgcolor=theme.BG, content=ft.Icon(ui.icon("BEDTIME"), color=theme.MUTED, size=size * 0.52), **common)
    return ft.Container(border=ft.border.all(2, theme.BORDER), **common)


def streak_text(current: int) -> str:
    return f"{ui.days_text(current)} подряд" if current > 0 else "Начните серию"


def week_strip(days: list[dict], today: str | None) -> ft.Row:
    """Семь кружков за последние 7 дней: выполнено, срыв, ждёт отметки, не по расписанию."""
    cells = []
    for day in days:
        status = day["status"]
        is_today = day["date"] == today
        letter = WEEKDAY_LETTERS[day["weekday"] % 7]
        if status == "done":
            bg, fg = theme.GREEN, theme.WHITE
        elif status == "missed":
            bg, fg = theme.RED_SOFT, theme.RED
        elif status == "off":
            bg, fg = None, theme.BORDER
        else:
            bg, fg = None, theme.MUTED
        border = None
        if is_today and bg is None:
            border = ft.border.all(1.5, theme.PRIMARY)
        elif status == "none":
            border = ft.border.all(1.2, theme.BORDER)
        cells.append(
            ft.Container(
                width=22,
                height=22,
                border_radius=11,
                bgcolor=bg,
                border=border,
                alignment=ft.alignment.center,
                content=ui.txt(letter, 10, ui.W_BOLD if bg else None, fg),
            )
        )
    return ft.Row(cells, spacing=6)


def habit_card(app, habit: dict, on_open, on_toggle, pop=False) -> tuple[ft.Container, ft.Container]:
    """Возвращает (карточку, кнопку-отметку): кнопка нужна экрану для анимации «выпрыгивания»."""
    bg, fg = category_colors(habit.get("category"))
    partners = partners_of(habit)
    if partners:
        subtitle = "Вместе с: " + ", ".join(p["name"] for p in partners)
    else:
        subtitle = habit.get("goal") or "Пока без напарника"
    planned = habit.get("week_planned") or 0
    percent = round(100 * habit.get("week_done", 0) / planned) if planned else 0
    week_days = habit.get("week_days") or []  # у старого сервера поля нет: тогда обычная полоска
    button = check_button(habit["today_status"], on_toggle, size=42, pop=pop)

    progress = week_strip(week_days, habit.get("today")) if week_days else ui.progress(percent)
    card = ui.card(
        ft.Row(
            [
                ui.circle_icon(habit.get("icon") or "CHECK_CIRCLE_OUTLINE", bg, fg, 54),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ui.txt(habit["title"], 17, ui.W_BOLD, expand=True, max_lines=1,
                                       overflow=ft.TextOverflow.ELLIPSIS),
                                button,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ui.muted(subtitle, 12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        progress,
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
                    spacing=7,
                    expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=14,
        ),
        padding=16,
        on_click=on_open,
        opacity=0.78 if habit["today_status"] == "done" else 1.0,  # выполненные чуть бледнее: взгляд идёт к тем, что ждут
    )
    return card, button
