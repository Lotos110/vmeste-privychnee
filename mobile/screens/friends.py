"""Друзья: мой код, добавление по коду, заявки и список друзей."""

import flet as ft

import theme
from components import common as ui
from core import Screen


class FriendsScreen(Screen):
    title = "Друзья"

    def __init__(self, app):
        super().__init__(app)
        self.code_field = ui.field("Код друга", hint="Например, K7M2-QX9R", max_length=12,
                                   on_submit=app.guard(self.add))

    def body(self):
        app, api = self.app, self.app.api
        me = api.get("/me")
        data = api.get("/friends")
        code = ui.format_code(me["friend_code"])

        controls: list[ft.Control] = [
            ui.card(
                ft.Column(
                    [
                        ui.muted("Ваш код", 12),
                        ft.Row(
                            [
                                ui.txt(code, 28, ui.W_BOLD, theme.PRIMARY),
                                ft.IconButton(icon=ui.icon("CONTENT_COPY"), icon_color=theme.PRIMARY,
                                              tooltip="Скопировать", on_click=lambda e: app.copy(code)),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ui.muted("Отправьте код другу: он введёт его у себя, и вы сможете формировать привычки вместе.", 12),
                    ],
                    spacing=4,
                ),
                bgcolor=theme.PRIMARY_SOFT,
            ),
            ui.txt("Добавить по коду", 18, ui.W_BOLD),
            self.code_field,
            ui.primary_button("Добавить", app.guard(self.add)),
        ]

        if data["incoming"]:
            controls.append(ui.txt("Хотят дружить", 18, ui.W_BOLD))
            for person in data["incoming"]:
                controls.append(self._person_row(person, accept=True))
        controls.append(ui.txt("Мои друзья", 18, ui.W_BOLD))
        if not data["friends"]:
            controls.append(ui.empty_state("Друзей пока нет. Добавьте первого по коду.", "🤝"))
        for person in data["friends"]:
            controls.append(self._person_row(person))
        if data["outgoing"]:
            controls.append(ui.txt("Ждут ответа", 18, ui.W_BOLD))
            for person in data["outgoing"]:
                controls.append(self._person_row(person, pending=True))
        controls.append(ui.spacer(8))
        return controls

    def _person_row(self, person: dict, accept=False, pending=False) -> ft.Container:
        app = self.app
        actions: list[ft.Control] = []
        if accept:
            actions.append(ui.small_button("Принять", app.guard(lambda: self.accept(person))))
            actions.append(ft.IconButton(icon=ui.icon("CLOSE"), icon_color=theme.MUTED,
                                         on_click=app.guard(lambda: self.remove(person, ask=False))))
        elif pending:
            actions.append(ui.muted("Заявка отправлена", 12))
            actions.append(ft.IconButton(icon=ui.icon("CLOSE"), icon_color=theme.MUTED,
                                         on_click=app.guard(lambda: self.remove(person, ask=False))))
        else:
            actions.append(ft.IconButton(icon=ui.icon("DELETE_OUTLINE"), icon_color=theme.MUTED,
                                         tooltip="Удалить из друзей",
                                         on_click=app.guard(lambda: self.remove(person, ask=True))))
        return ui.card(
            ft.Row(
                [
                    ui.avatar(app, person["name"], person.get("avatar_url"), 22),
                    ui.txt(person["name"], 15, ui.W_SEMI, expand=True),
                    *actions,
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=10,
            radius=16,
        )

    def add(self) -> None:
        code = (self.code_field.value or "").strip()
        if not code:
            return self.app.toast("Введите код друга", error=True)
        result = self.app.api.post("/friends/by-code", {"code": code})
        name = result["person"]["name"]
        if result["status"] == "accepted":
            self.app.toast(f"{name} теперь в друзьях 🎉")
        else:
            self.app.toast(f"Заявка отправлена: {name}")
        self.code_field.value = ""
        self.refresh()

    def accept(self, person: dict) -> None:
        self.app.api.post(f"/friends/{person['id']}/accept")
        self.app.toast(f"{person['name']} теперь в друзьях 🎉")
        self.refresh()

    def remove(self, person: dict, ask: bool) -> None:
        def do():
            self.app.api.delete(f"/friends/{person['id']}")
            self.refresh()

        if ask:
            self.app.confirm("Удалить из друзей?", f"{person['name']} пропадёт из списка друзей. Совместные привычки останутся.",
                             "Удалить", do)
        else:
            do()
