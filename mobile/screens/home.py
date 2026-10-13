"""Главная: профиль, мои привычки, итог за сегодня, приглашения."""

import flet as ft

import theme
from components import common as ui
from components.habit_card import habit_card
from core import Screen


class HomeScreen(Screen):
    tab_index = 0

    def body(self):
        app, api = self.app, self.app.api
        me = api.get("/me")
        app.me = me
        habits = api.get("/habits")
        invites = api.get("/invites")
        nudges = api.get("/nudges")
        has_unread = any(not n["read"] for n in nudges)

        from screens.create_habit import TemplatePickerScreen
        from screens.habit import HabitScreen
        from screens.notifications import NotificationsScreen
        from screens.sos import SosScreen

        controls: list[ft.Control] = [self._header(has_unread, NotificationsScreen)]

        controls.append(
            ui.card(
                ft.Row(
                    [
                        ui.avatar(app, me["name"], me.get("avatar_url"), 28),
                        ft.Column(
                            [
                                ui.txt(me["name"], 18, ui.W_BOLD),
                                ui.muted(f"Твой код: {ui.format_code(me['friend_code'])}"),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Icon(ui.icon("CHEVRON_RIGHT"), color=theme.MUTED),
                    ],
                    spacing=12,
                ),
                padding=14,
                on_click=lambda e: app.open_tab(2),
            )
        )

        controls.append(
            ft.Container(
                bgcolor=theme.GREEN_SOFT,
                border_radius=20,
                padding=ft.padding.only(left=16, top=8, bottom=8, right=8),
                content=ft.Row(
                    [
                        ft.Text("Маленькие шаги вместе приводят к большим результатам 💚",
                                size=14, weight=ui.W_SEMI, color=theme.TEXT, expand=True),
                        ft.Text("🙌", size=56),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        )

        for invite in invites:
            controls.append(self._invite_card(invite))

        controls.append(
            ft.Row(
                [
                    ui.txt("Мои привычки", 18, ui.W_BOLD),
                    ft.IconButton(
                        icon=ui.icon("ADD_CIRCLE"),
                        icon_color=theme.PRIMARY,
                        tooltip="Новая привычка",
                        on_click=lambda e: app.push(TemplatePickerScreen(app)),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

        if not habits:
            controls.append(ui.empty_state("Пока нет привычек. Начните с одной маленькой, лучше вместе с другом."))
            controls.append(ui.primary_button("Создать привычку", lambda e: app.push(TemplatePickerScreen(app))))
        for habit in habits:
            controls.append(
                habit_card(
                    app,
                    habit,
                    on_open=lambda e, h=habit: app.push(HabitScreen(app, h["id"])),
                    on_toggle=app.guard(lambda h=habit: self.toggle(h)),
                )
            )

        if habits:
            controls.append(self._today_card(habits))

        if any(h["today_status"] == "missed" for h in habits):
            controls.append(
                ui.card(
                    ft.Column(
                        [
                            ui.txt("Был трудный день?", 16, ui.W_BOLD),
                            ui.muted("Один срыв не отменяет прогресс. SOS-бот поможет вернуться без чувства вины.", 13),
                            ui.soft_button("Открыть SOS-бота", lambda e: app.push(SosScreen(app))),
                        ],
                        spacing=8,
                    ),
                    bgcolor=theme.PRIMARY_SOFT,
                )
            )
        controls.append(ui.spacer(8))
        return controls

    # ---------- части экрана ----------

    def _header(self, has_unread: bool, notifications_screen) -> ft.Row:
        app = self.app
        bell = ft.Stack(
            [
                ft.IconButton(
                    icon=ui.icon("NOTIFICATIONS_OUTLINED"),
                    icon_color=theme.TEXT,
                    on_click=lambda e: app.push(notifications_screen(app)),
                )
            ],
            width=48,
            height=48,
        )
        if has_unread:
            bell.controls.append(
                ft.Container(width=10, height=10, border_radius=5, bgcolor=theme.RED, right=10, top=10)
            )
        return ft.Row(
            [
                ft.Container(
                    width=44,
                    height=44,
                    border_radius=14,
                    alignment=ft.alignment.center,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                        colors=theme.PRIMARY_GRADIENT,
                    ),
                    content=ft.Icon(ui.icon("FAVORITE"), color=theme.WHITE, size=24),
                ),
                ft.Column(
                    [ui.txt("Вместе привычнее", 20, ui.W_BOLD), ui.muted("Полезные привычки. Вместе.", 12)],
                    spacing=0,
                    expand=True,
                ),
                bell,
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _invite_card(self, invite: dict) -> ft.Container:
        app = self.app
        who = ", ".join(m["name"] for m in invite["members"] if not m["is_me"] and m["status"] == "active")
        habit_id = invite["id"]

        def accept():
            app.api.post(f"/habits/{habit_id}/accept")
            app.toast("Привычка добавлена")
            self.refresh()

        def decline():
            app.api.post(f"/habits/{habit_id}/decline")
            self.refresh()

        return ui.card(
            ft.Column(
                [
                    ui.txt(f"{who or 'Друг'} зовёт вас вместе", 14, ui.W_SEMI),
                    ui.txt(f"«{invite['title']}»", 17, ui.W_BOLD),
                    ft.Row(
                        [
                            ui.small_button("Принять", app.guard(accept)),
                            ui.small_button("Позже", app.guard(decline), filled=False),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=6,
            ),
            bgcolor=theme.GREEN_SOFT,
        )

    def _today_card(self, habits: list[dict]) -> ft.Container:
        scheduled = [h for h in habits if h["today_status"] != "off"]
        done = [h for h in scheduled if h["today_status"] == "done"]
        pending = [h for h in scheduled if h["today_status"] in ("pending", "missed")]
        percent = round(100 * len(done) / len(scheduled)) if scheduled else 0

        parts: list[ft.Control] = [ui.txt("Сегодня", 18, ui.W_BOLD)]
        if not scheduled:
            parts.append(ui.muted("Сегодня привычек по расписанию нет. Отдыхайте! 🌿", 13))
        else:
            parts.append(
                ft.Row(
                    [ui.muted(f"Выполнено {len(done)} из {len(scheduled)}", 14), ui.muted(f"{percent}%", 12)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )
            parts.append(ui.progress(percent))
            if pending:
                parts.append(ui.primary_button("Отметить привычки", lambda e: self.mark_dialog(pending)))
            else:
                parts.append(ui.txt("Всё отмечено, так держать! 🎉", 14, ui.W_SEMI, theme.GREEN))
        return ui.card(ft.Column(parts, spacing=10))

    # ---------- действия ----------

    def toggle(self, habit: dict) -> None:
        api = self.app.api
        status = habit["today_status"]
        if status == "off":
            return self.app.toast("По расписанию сегодня отдых. Отметить можно на странице привычки.")
        if status == "done":
            api.delete(f"/habits/{habit['id']}/check-ins/{habit['today']}")
        else:
            api.post(f"/habits/{habit['id']}/check-ins", {"status": "done"})
        self.refresh()

    def mark_dialog(self, pending: list[dict]) -> None:
        boxes = [(h, ft.Checkbox(label=h["title"], value=True)) for h in pending]

        def apply():
            for habit, box in boxes:
                if box.value:
                    self.app.api.post(f"/habits/{habit['id']}/check-ins", {"status": "done"})
            self.refresh()

        self.app.dialog(
            "Что вы сегодня сделали?",
            ft.Column([box for _, box in boxes], tight=True, scroll=ft.ScrollMode.AUTO),
            [("Отмена", None), ("Отметить", apply)],
        )
