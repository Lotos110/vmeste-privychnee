"""Поле даты «ДД.ММ.ГГГГ»: вводятся только цифры, точки ставятся сами, рядом кнопка-календарь."""

from datetime import date, datetime

import flet as ft

import theme
from components import common as ui

MASK_HINT = "__.__.____"
MIN_DATE = date(1900, 1, 1)  # раньше сервер дату рождения не принимает


def format_digits(raw: str) -> str:
    """'12052000' -> '12.05.2000'. Точка появляется только вместе со следующей цифрой.

    Так клавиша «стереть» работает как обычно: точку, которую поле добавило само,
    не нужно стирать отдельно.
    """
    digits = "".join(ch for ch in raw if ch.isdigit())[:8]
    out = digits[:2]
    if len(digits) > 2:
        out += "." + digits[2:4]
    if len(digits) > 4:
        out += "." + digits[4:]
    return out


def format_date(value: date | None) -> str:
    return value.strftime("%d.%m.%Y") if value else ""


class DateInput:
    """Текстовое поле + календарь. Поле лежит в .field, его нужно добавить на экран."""

    def __init__(self, app, label: str, value: date | None = None, max_date: date | None = None):
        self.app = app
        self.max_date = max_date or date.today()
        self.field = ui.field(
            label,
            format_date(value),
            prefix="CALENDAR_MONTH",
            keyboard=ft.KeyboardType.NUMBER,
            hint=MASK_HINT,
            max_length=10,
            input_filter=ft.InputFilter(regex_string=r"[0-9.]", allow=True, replacement_string=""),
            on_change=self._on_change,
            suffix=ft.IconButton(
                icon=ui.icon("EVENT"),
                icon_color=theme.PRIMARY,
                tooltip="Выбрать в календаре",
                on_click=lambda e: self.open_calendar(),
            ),
        )

    # ---------- ввод с клавиатуры ----------

    def _on_change(self, e) -> None:
        fixed = format_digits(self.field.value or "")
        if fixed != (self.field.value or ""):
            self.field.value = fixed
            self.field.update()

    def parse(self) -> date | None:
        """Пустое поле -> None. Неполную или несуществующую дату и дату вне диапазона -> ValueError."""
        raw = (self.field.value or "").strip()
        if not raw:
            return None
        try:
            parsed = datetime.strptime(raw, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Дата рождения: ДД.ММ.ГГГГ, например 12.05.2000") from None
        if parsed < MIN_DATE:
            raise ValueError("Дата рождения не может быть раньше 1900 года")
        if parsed > self.max_date:
            raise ValueError("Дата рождения не может быть в будущем")
        return parsed

    # ---------- календарь ----------

    def open_calendar(self) -> None:
        try:
            current = self.parse()
        except ValueError:
            current = None
        start = current or date(2000, 1, 1)
        picker = ft.DatePicker(
            value=datetime(start.year, start.month, start.day),
            first_date=datetime(MIN_DATE.year, MIN_DATE.month, MIN_DATE.day),
            last_date=datetime(self.max_date.year, self.max_date.month, self.max_date.day),
            help_text="Дата рождения",
            cancel_text="Отмена",
            confirm_text="Готово",
            field_label_text="Дата",
            field_hint_text=MASK_HINT,
            error_format_text="Введите дату как ДД.ММ.ГГГГ",
            error_invalid_text="Дата вне допустимого диапазона",
            on_change=self._picked,
        )
        self.app.page.open(picker)

    def _picked(self, e) -> None:
        chosen = e.control.value
        if chosen:
            self.field.value = chosen.strftime("%d.%m.%Y")
            self.field.error_text = None
            self.field.update()
