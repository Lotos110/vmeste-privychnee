"""Создание привычки: выбор шаблона или своей, затем детали и приглашение друзей."""

import flet as ft

import theme
from components import common as ui
from components.habit_card import category_colors
from components.schedule import ScheduleSelector, normalize_time
from core import Screen


class TemplatePickerScreen(Screen):
    title = "Создание привычки"
    refresh_on_return = False

    def __init__(self, app):
        self.templates: list[dict] | None = None
        self.tab = 0  # 0 — шаблоны, 1 — своя привычка
        self.selected: dict | None = None
        super().__init__(app)

    def body(self):
        if self.templates is None:
            self.templates = self.app.api.get("/templates")
        return self.render()

    def render(self) -> list[ft.Control]:
        controls: list[ft.Control] = [ui.segmented(["Шаблоны", "Своя привычка"], self.tab, self.set_tab)]
        if self.tab == 0:
            controls.append(ui.txt("Выберите шаблон", 20, ui.W_BOLD))
            controls += self._grid()
        controls.append(
            ui.card(
                ft.Row(
                    [
                        ft.Column(
                            [
                                ui.txt("Или создайте свою привычку", 15, ui.W_SEMI),
                                ui.muted("Например: «Учить английский» или «Больше времени на хобби»", 12),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ui.circle_icon("ADD", theme.PRIMARY, theme.WHITE, 40),
                    ],
                    spacing=12,
                ),
                bgcolor=theme.PRIMARY_SOFT,
                on_click=lambda e: self.set_tab(1),
            )
        )
        controls.append(ui.spacer(4))
        controls.append(ui.primary_button("Далее", self.app.guard(self.next)))
        controls.append(ui.spacer(8))
        return controls

    def _grid(self) -> list[ft.Control]:
        rows = []
        templates = self.templates or []
        for start in range(0, len(templates), 3):
            cells = [self._cell(t) for t in templates[start : start + 3]]
            while len(cells) < 3:  # добиваем пустыми ячейками, чтобы колонки были ровными
                cells.append(ft.Container(expand=1))
            rows.append(ft.Row(cells, spacing=12))
        return rows

    def _cell(self, template: dict) -> ft.Container:
        bg, fg = category_colors(template["category"])
        selected = self.selected is not None and self.selected["id"] == template["id"]
        return ft.Container(
            expand=1,
            padding=ft.padding.symmetric(vertical=14, horizontal=4),
            bgcolor=theme.CARD,
            border_radius=18,
            border=ft.border.all(2, theme.PRIMARY if selected else theme.BORDER),
            content=ft.Column(
                [
                    ui.circle_icon(template["icon"], bg, fg, 48),
                    ui.txt(template["title"], 12, text_align=ft.TextAlign.CENTER,
                           max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
            on_click=lambda e, t=template: self.select(t),
        )

    def _redraw(self) -> None:
        self.content.controls = self.render()
        self.app.page.update()

    def set_tab(self, index: int) -> None:
        self.tab = index
        if index == 1:
            self.selected = None
        self._redraw()

    def select(self, template: dict) -> None:
        self.selected = template
        self._redraw()

    def next(self) -> None:
        if self.tab == 0 and self.selected is None:
            return self.app.toast("Выберите шаблон или создайте свою привычку", error=True)
        self.app.push(CreateDetailsScreen(self.app, self.selected if self.tab == 0 else None))


class CreateDetailsScreen(Screen):
    title = "Новая привычка"
    refresh_on_return = False

    def __init__(self, app, template: dict | None = None):
        self.template = template
        self.friend_boxes: list[tuple[dict, ft.Checkbox]] = []
        self.sending = False
        super().__init__(app)
        template = template or {}
        self.title_field = ui.field("Название", template.get("title", ""), hint="Например: Учить английский", max_length=80)
        self.goal_field = ui.field("Цель", template.get("default_goal") or "", hint="Например: 30 дней подряд", max_length=120)
        self.schedule = ScheduleSelector(template.get("default_schedule"))
        self.time_field = ui.field("Напоминание (ЧЧ:ММ)", template.get("default_time") or "",
                                   prefix="ALARM", hint="18:00, можно оставить пустым")

    def body(self):
        friends = self.app.api.get("/friends")["friends"]
        self.friend_boxes = [(f, ft.Checkbox(label=f["name"], value=False)) for f in friends]

        controls: list[ft.Control] = [
            self.title_field,
            self.goal_field,
            ui.txt("Дни недели", 15, ui.W_SEMI),
            self.schedule.row,
            self.time_field,
            ui.txt("Позвать друга", 18, ui.W_BOLD),
        ]
        if self.friend_boxes:
            controls.append(ui.muted("Привычка станет совместной: вы увидите отметки друг друга и общую серию.", 12))
            controls.append(ui.card(ft.Column([box for _, box in self.friend_boxes], spacing=0), padding=8))
        else:
            from screens.friends import FriendsScreen

            controls.append(ui.muted("Пока нет друзей. Добавьте друга по коду, и привычку можно будет делать вместе.", 13))
            controls.append(ui.soft_button("Добавить друга", lambda e: self.app.push(FriendsScreen(self.app))))
        controls.append(ui.spacer(4))
        controls.append(ui.primary_button("Создать привычку", self.app.guard(self.create)))
        controls.append(ui.spacer(8))
        return controls

    def create(self) -> None:
        if self.sending:
            return
        title = (self.title_field.value or "").strip()
        if not title:
            return self.app.toast("Укажите название привычки", error=True)
        try:
            remind_time = normalize_time(self.time_field.value)
        except ValueError as err:
            return self.app.toast(str(err), error=True)

        payload = {
            "title": title,
            "goal": (self.goal_field.value or "").strip() or None,
            "schedule": self.schedule.value,
            "remind_time": remind_time,
            "template_id": self.template["id"] if self.template else None,
            "invite_friend_ids": [f["id"] for f, box in self.friend_boxes if box.value],
        }
        self.sending = True
        try:
            self.app.api.post("/habits", payload)
        finally:
            self.sending = False
        self.app.toast("Привычка создана! Первый шаг сделан 🌱")
        self.app.open_tab(0)
