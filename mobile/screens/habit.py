"""Страница привычки: отметка дня, участники, поддержка напарника, календарь."""

from datetime import date

import flet as ft

import theme
from components import common as ui
from components.habit_card import habit_colors, partners_of, streak_text
from components.icon_picker import IconPicker
from components.schedule import ScheduleSelector, normalize_time, schedule_label
from core import Screen

NUDGE_PRESETS = ["Не прерывай серию 🔥", "Ты сможешь 💪", "Я уже отметился ✅"]
MISS_REASONS = [
    "Не было времени",
    "Забыл(а)",
    "Плохо себя чувствовал(а)",
    "Не было настроения",
    "Другое",
]


class HabitScreen(Screen):
    title = "Привычка"

    def __init__(self, app, habit_id: int):
        self.habit_id = habit_id
        self.habit: dict | None = None
        self.month: str | None = None  # «ГГГГ-ММ», None — текущий месяц
        super().__init__(app)

    def appbar_actions(self):
        return [
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(text="Редактировать", on_click=lambda e: self.edit_dialog()),
                    ft.PopupMenuItem(text="Выйти из привычки", on_click=lambda e: self.leave_confirm()),
                ]
            )
        ]

    # ---------- построение экрана ----------

    def body(self):
        api = self.app.api
        habit = api.get(f"/habits/{self.habit_id}")
        self.habit = habit
        if habit["my_status"] == "invited":
            return self._invited_view(habit)

        params = {"month": self.month} if self.month else None
        calendar_data = api.get(f"/habits/{self.habit_id}/calendar", params=params)

        controls = [self._header(habit)]
        controls.append(self._stats_row(habit))
        controls += self._today_block(habit)
        controls.append(self._members_card(habit))
        if partners_of(habit):
            controls.append(self._support_card(habit))
        controls.append(self._calendar_card(calendar_data))
        controls.append(ui.spacer(8))
        return controls

    def _header(self, habit: dict) -> ft.Control:
        bg, fg = habit_colors(habit)
        details = [schedule_label(habit["schedule"])]
        if habit.get("remind_time"):
            details.append(f"напоминание в {habit['remind_time']}")
        texts = [ui.txt(habit["title"], 22, ui.W_BOLD)]
        if habit.get("goal"):
            texts.append(ui.txt(f"Цель: {habit['goal']}", 14))
        texts.append(ui.muted(" · ".join(details), 12))
        return ft.Row(
            [ui.circle_icon(habit.get("icon") or "CHECK_CIRCLE_OUTLINE", bg, fg, 64),
             ft.Column(texts, spacing=2, expand=True)],
            spacing=14,
        )

    def _stat_tile(self, value: int, label: str, color=theme.PRIMARY) -> ft.Container:
        return ft.Container(
            expand=1,
            bgcolor=theme.CARD,
            border_radius=16,
            padding=ft.padding.symmetric(vertical=12),
            content=ft.Column(
                [ui.txt(str(value), 24, ui.W_BOLD, color), ui.muted(label, 12)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
        )

    def _stats_row(self, habit: dict) -> ft.Row:
        tiles = [
            self._stat_tile(habit["current_streak"], "Серия, дн."),
            self._stat_tile(habit["best_streak"], "Рекорд, дн.", theme.ORANGE),
        ]
        if habit.get("shared_streak") is not None:
            tiles.append(self._stat_tile(habit["shared_streak"], "Общая серия", theme.GREEN))
        return ft.Row(tiles, spacing=10)

    def _today_block(self, habit: dict) -> list[ft.Control]:
        status = habit["today_status"]
        if status == "done":
            return [
                ft.Container(
                    bgcolor=theme.GREEN_SOFT,
                    border_radius=16,
                    padding=14,
                    content=ui.txt("Сегодня выполнено. " + streak_text(habit["current_streak"]), 14, ui.W_SEMI, theme.GREEN),
                ),
                ui.outline_button("Отменить отметку", self.app.guard(self.undo)),
            ]
        if status == "missed":
            return [
                ft.Container(
                    bgcolor=theme.RED_SOFT,
                    border_radius=16,
                    padding=14,
                    content=ui.txt("Сегодня не получилось. Один срыв не отменяет прогресс, вернуться можно в любой момент.", 13, color=theme.TEXT),
                ),
                ui.primary_button("Всё-таки выполнено", self.app.guard(self.mark_done)),
                ui.soft_button("Заглянуть к Тишке", lambda e: self.open_sos()),
            ]
        controls: list[ft.Control] = []
        if status == "off":
            controls.append(ui.muted("По расписанию сегодня отдых. Можно отметить выполнение и в этот день.", 13))
        controls.append(ui.primary_button("Выполнено", self.app.guard(self.mark_done)))
        controls.append(ui.soft_button("Не получилось", lambda e: self.miss_dialog()))
        return controls

    def _members_card(self, habit: dict) -> ft.Container:
        labels = {
            "done": ("Выполнил(а)", theme.GREEN),
            "missed": ("Пропуск", theme.RED),
            "pending": ("Ждёт отметки", theme.MUTED),
            "off": ("Отдыхает", theme.MUTED),
        }
        rows: list[ft.Control] = [ui.txt("Участники", 18, ui.W_BOLD)]
        for member in habit["members"]:
            if member["status"] == "invited":
                label, color = "Приглашён(а)", theme.MUTED
            else:
                label, color = labels[member["today_status"]]
            name = member["name"] + (" (вы)" if member["is_me"] else "")
            rows.append(
                ft.Row(
                    [
                        ui.avatar(self.app, member["name"], member.get("avatar_url"), 20),
                        ft.Column(
                            [ui.txt(name, 15, ui.W_SEMI), ui.muted(streak_text(member["current_streak"]), 12)],
                            spacing=0,
                            expand=True,
                        ),
                        ui.txt(label, 12, ui.W_SEMI, color),
                    ],
                    spacing=12,
                )
            )
        rows.append(ui.soft_button("Позвать друга", lambda e: self.app.guard(self.invite_dialog)()))
        return ui.card(ft.Column(rows, spacing=12))

    def _support_card(self, habit: dict) -> ft.Container:
        chips = ft.Row(
            [ui.chip(text, False, self.app.guard(lambda t=text: self.send_nudge(t))) for text in NUDGE_PRESETS],
            wrap=True,
            spacing=8,
            run_spacing=8,
        )
        return ui.card(
            ft.Column(
                [ui.txt("Поддержать напарника", 18, ui.W_BOLD),
                 ui.muted("Короткое сообщение подбодрит и не даст прервать серию", 12), chips],
                spacing=8,
            )
        )

    def _calendar_card(self, data: dict) -> ft.Container:
        year, month = int(data["month"][:4]), int(data["month"][5:])
        today = date.today()
        first_weekday = date(year, month, 1).weekday()
        cells: list[ft.Control] = [ft.Container(expand=1, height=36) for _ in range(first_weekday)]
        for day in data["days"]:
            number = int(day["date"][8:])
            is_today = day["date"] == today.isoformat()
            bg, color = None, theme.TEXT if day["scheduled"] else theme.MUTED
            if day["status"] == "done":
                bg, color = theme.GREEN, theme.WHITE
            elif day["status"] == "missed":
                bg, color = theme.RED_SOFT, theme.RED
            cells.append(
                ft.Container(
                    expand=1,
                    height=36,
                    alignment=ft.alignment.center,
                    content=ft.Container(
                        width=32,
                        height=32,
                        border_radius=16,
                        bgcolor=bg,
                        border=ft.border.all(1.5, theme.PRIMARY) if is_today and bg is None else None,
                        alignment=ft.alignment.center,
                        content=ui.txt(str(number), 13, ui.W_SEMI if bg else None, color),
                    ),
                )
            )
        while len(cells) % 7:
            cells.append(ft.Container(expand=1, height=36))
        weeks = [ft.Row(cells[i : i + 7], spacing=0) for i in range(0, len(cells), 7)]

        header = ft.Row(
            [
                ft.IconButton(icon=ui.icon("CHEVRON_LEFT"), on_click=lambda e: self.shift_month(data, -1)),
                ui.txt(f"{theme.MONTHS[month - 1]} {year}", 16, ui.W_BOLD),
                ft.IconButton(icon=ui.icon("CHEVRON_RIGHT"), on_click=lambda e: self.shift_month(data, 1)),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        weekdays = ft.Row(
            [ft.Container(expand=1, alignment=ft.alignment.center,
                          content=ui.muted(name, 12)) for name in theme.WEEKDAYS],
            spacing=0,
        )
        legend = ft.Row(
            [
                ft.Icon(ui.icon("CIRCLE"), color=theme.GREEN, size=10), ui.muted("выполнено", 11),
                ft.Icon(ui.icon("CIRCLE"), color=theme.RED, size=10), ui.muted("срыв", 11),
            ],
            spacing=6,
        )
        return ui.card(ft.Column([ui.txt("Календарь", 18, ui.W_BOLD), header, weekdays, *weeks, legend], spacing=4))

    def _invited_view(self, habit: dict) -> list[ft.Control]:
        who = ", ".join(m["name"] for m in habit["members"] if not m["is_me"] and m["status"] == "active")
        return [
            self._header(habit),
            ui.card(
                ft.Column(
                    [
                        ui.txt(f"{who or 'Друг'} зовёт вас делать эту привычку вместе", 15, ui.W_SEMI),
                        ui.muted("Вы будете видеть отметки друг друга и вести общую серию.", 13),
                    ],
                    spacing=6,
                ),
                bgcolor=theme.GREEN_SOFT,
            ),
            ui.primary_button("Принять приглашение", self.app.guard(self.accept)),
            ui.outline_button("Отклонить", self.app.guard(self.decline)),
        ]

    # ---------- действия ----------

    def shift_month(self, data: dict, delta: int) -> None:
        year, month = int(data["month"][:4]), int(data["month"][5:])
        month += delta
        if month == 0:
            year, month = year - 1, 12
        elif month == 13:
            year, month = year + 1, 1
        self.month = f"{year:04d}-{month:02d}"
        self.refresh()

    def mark_done(self) -> None:
        self.app.api.post(f"/habits/{self.habit_id}/check-ins", {"status": "done"})
        self.refresh()

    def undo(self) -> None:
        self.app.api.delete(f"/habits/{self.habit_id}/check-ins/{self.habit['today']}")
        self.refresh()

    def accept(self) -> None:
        self.app.api.post(f"/habits/{self.habit_id}/accept")
        self.refresh()

    def decline(self) -> None:
        self.app.api.post(f"/habits/{self.habit_id}/decline")
        self.app.pop()

    def open_sos(self) -> None:
        from screens.sos import SosScreen

        self.app.push(SosScreen(self.app))

    def miss_dialog(self) -> None:
        group = ft.RadioGroup(
            value=MISS_REASONS[0],
            content=ft.Column([ft.Radio(value=reason, label=reason) for reason in MISS_REASONS], tight=True),
        )

        def save():
            self.app.api.post(
                f"/habits/{self.habit_id}/check-ins", {"status": "missed", "miss_reason": group.value}
            )
            self.refresh()
            self.app.dialog(
                "Ничего страшного",
                ft.Text("Один срыв не отменяет прогресс. Хотите заглянуть к помощнику Тишке, чтобы вернуться без чувства вины?"),
                [("Не сейчас", None), ("Заглянуть к Тишке", self.open_sos)],
            )

        self.app.dialog("Что помешало?", group, [("Отмена", None), ("Сохранить", save)])

    def send_nudge(self, text: str) -> None:
        partners = partners_of(self.habit)
        for partner in partners:
            self.app.api.post(
                f"/habits/{self.habit_id}/nudges", {"to_user_id": partner["user_id"], "text": text}
            )
        self.app.toast("Отправлено")

    def invite_dialog(self) -> None:
        in_habit = {m["user_id"] for m in self.habit["members"]}
        friends = [f for f in self.app.api.get("/friends")["friends"] if f["id"] not in in_habit]
        if not friends:
            from screens.friends import FriendsScreen

            self.app.toast("Некого приглашать. Добавьте друга по коду.")
            return self.app.push(FriendsScreen(self.app))
        boxes = [(f, ft.Checkbox(label=f["name"], value=False)) for f in friends]

        def invite():
            sent = 0
            for friend, box in boxes:
                if box.value:
                    self.app.api.post(f"/habits/{self.habit_id}/invite", {"friend_id": friend["id"]})
                    sent += 1
            if sent:
                self.app.toast("Приглашение отправлено")
            self.refresh()

        self.app.dialog(
            "Позвать друга",
            ft.Column([box for _, box in boxes], tight=True, scroll=ft.ScrollMode.AUTO),
            [("Отмена", None), ("Пригласить", invite)],
        )

    def edit_dialog(self) -> None:
        habit = self.habit
        title = ui.field("Название", habit["title"], max_length=80)
        goal = ui.field("Цель", habit.get("goal") or "", max_length=120)
        schedule = ScheduleSelector(habit["schedule"])
        remind = ui.field("Напоминание (ЧЧ:ММ)", habit.get("remind_time") or "")
        picker = IconPicker(habit.get("icon"), habit.get("color"))

        def save():
            try:
                remind_time = normalize_time(remind.value)
            except ValueError as err:
                return self.app.toast(str(err), error=True)
            name = (title.value or "").strip()
            if not name:
                return self.app.toast("Укажите название привычки", error=True)
            self.app.api.patch(
                f"/habits/{self.habit_id}",
                {
                    "title": name,
                    "goal": (goal.value or "").strip() or None,
                    "schedule": schedule.value,
                    "remind_time": remind_time,
                    **picker.changes,
                },
            )
            self.refresh()

        self.app.dialog(
            "Редактировать привычку",
            ft.Column(
                [title, goal, ui.txt("Иконка и цвет", 14, ui.W_SEMI), ft.Container(picker.control, width=300),
                 schedule.row, remind],
                tight=True, spacing=12, scroll=ft.ScrollMode.AUTO,
            ),
            [("Отмена", None), ("Сохранить", save)],
        )

    def leave_confirm(self) -> None:
        def leave():
            self.app.api.delete(f"/habits/{self.habit_id}/membership")
            self.app.toast("Вы вышли из привычки")
            self.app.pop()

        self.app.confirm(
            "Выйти из привычки?",
            "Привычка пропадёт из вашего списка. Напарники останутся в ней.",
            "Выйти",
            leave,
        )
