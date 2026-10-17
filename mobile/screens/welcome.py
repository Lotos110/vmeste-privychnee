"""Приветствие, регистрация и вход."""

import re

import flet as ft

import theme
from components import common as ui
from core import Screen

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def logo(size=120) -> ft.Image:
    return ui.logo_tile(size)


def legal_text(app) -> ft.Text:
    base = app.api.base_url
    link_style = ft.TextStyle(color=theme.PRIMARY)
    return ft.Text(
        value="Продолжая, вы соглашаетесь с ",
        size=12,
        font_family=theme.FONT_BODY,
        color=theme.MUTED,
        text_align=ft.TextAlign.CENTER,
        spans=[
            ft.TextSpan(text="Пользовательским соглашением", style=link_style, url=f"{base}/legal/terms"),
            ft.TextSpan(text=" и "),
            ft.TextSpan(text="Политикой конфиденциальности", style=link_style, url=f"{base}/legal/privacy"),
        ],
    )


class WelcomeScreen(Screen):
    show_appbar = False
    refresh_on_return = False

    def __init__(self, app, offline_message: str | None = None):
        self.offline_message = offline_message
        super().__init__(app)

    def body(self):
        app = self.app
        controls = [
            ui.spacer(24),
            ft.Row([logo()], alignment=ft.MainAxisAlignment.CENTER),
            ui.centered_text("Вместе", 38, ft.FontWeight.W_800, theme.PRIMARY_DARK),
            ui.centered_text("привычнее", 30, ft.FontWeight.W_800, theme.PRIMARY),
            ui.centered_text("Полезные привычки вместе с теми, кто поддерживает", 14, color=theme.MUTED),
            ft.Container(
                bgcolor=theme.GREEN_SOFT,
                border_radius=24,
                padding=16,
                alignment=ft.alignment.center,
                content=ft.Text("🙌", size=84),
            ),
        ]
        if self.offline_message:
            controls += [
                ui.centered_text(self.offline_message, 13, color=theme.RED),
                ft.Row([ui.small_button("Повторить", lambda e: app.start())], alignment=ft.MainAxisAlignment.CENTER),
            ]
        controls += [
            ui.primary_button("Зарегистрироваться", lambda e: app.push(RegisterScreen(app))),
            ui.outline_button("Войти", lambda e: app.push(LoginScreen(app))),
            ft.Row([legal_text(app)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(
                [ui.link(f"Сервер: {app.api.base_url}", lambda e: self.server_dialog(), theme.MUTED, 12)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ]
        return controls

    def server_dialog(self):
        app = self.app
        field = ui.field("Адрес сервера", app.api.base_url, hint="http://192.168.0.10:8000")

        def save():
            app.api.set_base_url(field.value or "")
            app.toast("Адрес сохранён")
            app.start()

        app.dialog(
            "Адрес сервера",
            ft.Column([ui.muted("Для телефона укажите IP-адрес компьютера с сервером.", 12), field], tight=True),
            [("Отмена", None), ("Сохранить", save)],
        )


class RegisterScreen(Screen):
    title = "Регистрация"
    refresh_on_return = False

    def __init__(self, app):
        super().__init__(app)
        self.email = ui.field("Электронная почта", prefix="MAIL_OUTLINE", keyboard=ft.KeyboardType.EMAIL)
        self.name = ui.field("Имя", prefix="PERSON_OUTLINE")
        self.password = ui.field(
            "Пароль (не менее 8 символов)", password=True, prefix="LOCK_OUTLINE",
            on_submit=app.guard(self.submit),
        )

    def body(self):
        app = self.app
        return [
            ui.title("Регистрация", 28),
            ui.muted("Создайте аккаунт, чтобы начать формировать полезные привычки вместе с друзьями", 14),
            ui.spacer(4),
            self.email,
            self.name,
            self.password,
            ui.spacer(4),
            ui.primary_button("Зарегистрироваться", app.guard(self.submit)),
            ft.Row(
                [
                    ui.muted("Уже есть аккаунт?"),
                    ui.link("Войти", lambda e: self.go_login()),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
            ),
            ft.Row([legal_text(app)], alignment=ft.MainAxisAlignment.CENTER),
        ]

    def go_login(self):
        self.app.pop()
        self.app.push(LoginScreen(self.app))

    def submit(self):
        email = (self.email.value or "").strip()
        name = (self.name.value or "").strip()
        password = self.password.value or ""
        if not EMAIL_RE.match(email):
            return self.app.toast("Проверьте адрес электронной почты", error=True)
        if not name:
            return self.app.toast("Укажите имя", error=True)
        if len(password) < 8:
            return self.app.toast("Пароль: не менее 8 символов", error=True)
        user = self.app.api.register(email, password, name)
        self.app.after_auth(user)


class LoginScreen(Screen):
    title = "Вход"
    refresh_on_return = False

    def __init__(self, app):
        super().__init__(app)
        self.email = ui.field("Электронная почта", prefix="MAIL_OUTLINE", keyboard=ft.KeyboardType.EMAIL)
        self.password = ui.field(
            "Пароль", password=True, prefix="LOCK_OUTLINE", on_submit=app.guard(self.submit)
        )

    def body(self):
        return [
            ui.title("С возвращением!", 28),
            ui.muted("Войдите, чтобы продолжить серию", 14),
            ui.spacer(4),
            self.email,
            self.password,
            ui.spacer(4),
            ui.primary_button("Войти", self.app.guard(self.submit)),
            ft.Row(
                [
                    ui.muted("Ещё нет аккаунта?"),
                    ui.link("Зарегистрироваться", lambda e: self.go_register()),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
            ),
        ]

    def go_register(self):
        self.app.pop()
        self.app.push(RegisterScreen(self.app))

    def submit(self):
        email = (self.email.value or "").strip()
        password = self.password.value or ""
        if not email or not password:
            return self.app.toast("Введите email и пароль", error=True)
        user = self.app.api.login(email, password)
        self.app.after_auth(user)
