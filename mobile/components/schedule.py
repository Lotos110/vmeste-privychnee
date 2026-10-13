"""Выбор дней недели для расписания привычки."""

import re

import flet as ft

import theme
from components import common as ui

TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")


def normalize_time(value: str | None) -> str | None:
    """'9:00' -> '09:00'; пустое значение -> None; неверный формат -> ValueError."""
    value = (value or "").strip()
    if not value:
        return None
    if not TIME_RE.match(value):
        raise ValueError("Время нужно в формате ЧЧ:ММ, например 18:30")
    hours, minutes = value.split(":")
    if int(hours) > 23 or int(minutes) > 59:
        raise ValueError("Время нужно в формате ЧЧ:ММ, например 18:30")
    return f"{int(hours):02d}:{minutes}"


def schedule_label(schedule: list[int]) -> str:
    if len(schedule) == 7:
        return "Каждый день"
    return ", ".join(theme.WEEKDAYS[d] for d in sorted(schedule))


class ScheduleSelector:
    def __init__(self, selected=None):
        self.selected: set[int] = set(selected if selected else range(7))
        self.row = ft.Row(wrap=True, spacing=8, run_spacing=8)
        self._render()

    def _render(self) -> None:
        self.row.controls = [
            ui.chip(name, index in self.selected, lambda e, i=index: self._toggle(i))
            for index, name in enumerate(theme.WEEKDAYS)
        ]

    def _toggle(self, index: int) -> None:
        if index in self.selected:
            if len(self.selected) > 1:  # хотя бы один день должен остаться
                self.selected.discard(index)
        else:
            self.selected.add(index)
        self._render()
        self.row.update()

    @property
    def value(self) -> list[int]:
        return sorted(self.selected)
