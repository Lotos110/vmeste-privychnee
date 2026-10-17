"""Профиль и редактирование профиля."""

from datetime import datetime

import flet as ft

import theme
from components import common as ui
from components.date_input import DateInput
from core import Screen


class ProfileScreen(Screen):
    tab_index = 2

    def body(self):
        app, api = self.app, self.app.api
        me = api.get("/me")
        app.me = me

        from screens.friends import FriendsScreen
        from screens.notifications import NotificationsScreen
        from screens.sos import SosScreen
        from screens.stats import StatsScreen

        code = ui.format_code(me["friend_code"])
        full_name = f"{me['name']} {me.get('last_name') or ''}".strip()

        def stat(value, label):
            return ft.Container(
                expand=1,
                bgcolor=theme.CARD,
                border_radius=16,
                padding=ft.padding.symmetric(vertical=12),
                content=ft.Column(
                    [ui.txt(str(value), 22, ui.W_BOLD), ui.muted(label, 12)],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                ),
            )

        controls: list[ft.Control] = [
            ft.Row(
                [
                    ui.avatar(app, me["name"], me.get("avatar_url"), 38),
                    ft.Column(
                        [
                            ui.txt(full_name, 20, ui.W_BOLD),
                            ft.Row(
                                [
                                    ui.muted(f"Код: {code}", 13),
                                    ft.IconButton(icon=ui.icon("CONTENT_COPY"), icon_size=16, icon_color=theme.PRIMARY,
                                                  tooltip="Скопировать код", on_click=lambda e: app.copy(code)),
                                ],
                                spacing=0,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=14,
            ),
        ]
        if me.get("bio"):
            controls.append(ui.txt(me["bio"], 14))
        controls.append(
            ft.Row(
                [
                    stat(me["friends_count"], "друзей"),
                    stat(me["habits_count"], "привычек"),
                    stat(me["streak"], "дней подряд"),
                ],
                spacing=10,
            )
        )
        controls += [
            ui.menu_row("PEOPLE", "Друзья", lambda e: app.push(FriendsScreen(app)), "Добавить по коду, заявки"),
            ui.menu_row("BAR_CHART", "Статистика", lambda e: app.push(StatsScreen(app)), "Прогресс, серии, графики",
                        theme.GREEN, theme.GREEN_SOFT),
            ui.menu_row("NOTIFICATIONS_OUTLINED", "Напоминания", lambda e: app.push(NotificationsScreen(app)),
                        "Сообщения от напарников", theme.BLUE, theme.BLUE_SOFT),
            ui.menu_row("SMART_TOY", "SOS-бот", lambda e: app.push(SosScreen(app)), "Если трудно или сорвались",
                        theme.ORANGE, theme.ORANGE_SOFT),
            ui.spacer(4),
            ui.soft_button("Редактировать профиль", lambda e: app.push(EditProfileScreen(app, me))),
            ui.danger_button("Выйти", lambda e: app.confirm("Выйти из аккаунта?", "Вы сможете войти снова в любой момент.",
                                                            "Выйти", app.logout)),
            ft.Row([ui.muted(f"Сервер: {app.api.base_url}", 11)], alignment=ft.MainAxisAlignment.CENTER),
            ui.spacer(8),
        ]
        return controls


class EditProfileScreen(Screen):
    title = "Редактировать профиль"
    refresh_on_return = False

    def __init__(self, app, me: dict):
        self.me = me
        super().__init__(app)
        birth = None
        if me.get("birth_date"):
            birth = datetime.strptime(me["birth_date"], "%Y-%m-%d").date()
        self.gender = me.get("gender")
        self.name = ui.field("Имя", me["name"], max_length=60)
        self.last_name = ui.field("Фамилия", me.get("last_name") or "", max_length=60)
        self.bio = ui.field("О себе", me.get("bio") or "", multiline=True, max_length=300)
        self.birth = DateInput(app, "Дата рождения", birth)
        self.avatar_holder = ft.Container(content=ui.avatar(app, me["name"], me.get("avatar_url"), 48))
        self.gender_row = ft.Row(spacing=10)
        self.picker = ft.FilePicker(on_result=self.on_picked)

    def body(self):
        page = self.app.page
        # один FilePicker на экран: убираем «осиротевшие» от прошлых открытий
        page.overlay[:] = [c for c in page.overlay if not isinstance(c, ft.FilePicker)]
        page.overlay.append(self.picker)
        self._render_gender()
        return [
            ft.Row(
                [
                    ft.Stack(
                        [
                            self.avatar_holder,
                            ft.Container(
                                right=0,
                                bottom=0,
                                width=30,
                                height=30,
                                border_radius=15,
                                bgcolor=theme.PRIMARY,
                                alignment=ft.alignment.center,
                                content=ft.Icon(ui.icon("CAMERA_ALT"), color=theme.WHITE, size=16),
                                on_click=lambda e: self.pick_photo(),
                            ),
                        ],
                        width=96,
                        height=96,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            self.name,
            self.last_name,
            self.bio,
            self.birth.field,
            ui.txt("Пол", 14, ui.W_SEMI),
            self.gender_row,
            ui.spacer(4),
            ui.primary_button("Сохранить изменения", self.app.guard(self.save)),
            ui.spacer(8),
        ]

    # ---------- пол ----------

    def _render_gender(self) -> None:
        self.gender_row.controls = [
            ft.Container(
                content=ui.chip(label, self.gender == value, lambda e, v=value: self.set_gender(v)),
                expand=1,
            )
            for label, value in (("Женский", "female"), ("Мужской", "male"))
        ]

    def set_gender(self, value: str) -> None:
        self.gender = None if self.gender == value else value  # повторное нажатие снимает выбор
        self._render_gender()
        self.gender_row.update()

    # ---------- фото ----------

    def pick_photo(self) -> None:
        self.picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)

    def on_picked(self, e) -> None:
        if not e.files:
            return

        def upload():
            path = e.files[0].path
            if not path:
                return self.app.toast("На этой платформе выбрать фото из файла нельзя", error=True)
            self.me = self.app.api.upload_avatar(path)
            self.avatar_holder.content = ui.avatar(self.app, self.me["name"], self.me.get("avatar_url"), 48)
            self.app.page.update()
            self.app.toast("Фото обновлено")

        self.app.guard(upload)()

    # ---------- сохранение ----------

    def save(self) -> None:
        name = (self.name.value or "").strip()
        if not name:
            return self.app.toast("Имя не может быть пустым", error=True)
        try:
            parsed = self.birth.parse()
        except ValueError as err:
            return self.app.toast(str(err), error=True)
        birth_iso = parsed.isoformat() if parsed else None
        self.app.me = self.app.api.patch(
            "/me",
            {
                "name": name,
                "last_name": (self.last_name.value or "").strip() or None,
                "bio": (self.bio.value or "").strip() or None,
                "birth_date": birth_iso,
                "gender": self.gender,
            },
        )
        self.app.toast("Изменения сохранены")
        self.app.pop()
