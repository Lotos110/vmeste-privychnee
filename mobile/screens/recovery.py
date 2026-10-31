"""Забытый пароль: показ кода восстановления и сброс пароля по коду."""

import re

import flet as ft

import theme
from components import common as ui
from core import Screen

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RecoveryCodeScreen(Screen):
    """Показывает код восстановления один раз. user задан, когда экран открыт сразу после регистрации
    или сброса (тогда это корневой экран и «Продолжить» ведёт на главную); без user экран открыт из профиля."""

    title = "Код восстановления"
    refresh_on_return = False

    def __init__(self, app, code: str, user: dict | None = None, after_reset: bool = False):
        self.code = code
        self.user = user
        self.after_reset = after_reset
        self.show_appbar = user is None  # сразу после входа возвращаться назад некуда
        super().__init__(app)
        self.saved = ft.Checkbox(label="Я сохранил(а) код", value=False)

    def body(self):
        app = self.app
        intro = (
            "Пароль изменён. Прежний код больше не работает: сохраните новый."
            if self.after_reset
            else "Если забудете пароль, по этому коду вы сможете задать новый."
        )
        return [
            ui.spacer(8),
            ui.title("Сохраните код восстановления", 24),
            ui.muted(intro, 14),
            ui.muted(
                "Мы показываем код один раз и храним только его защищённый отпечаток. "
                "Запишите код или сохраните в надёжном месте. Потеряете и код, и пароль: "
                "вернуть доступ будет нельзя.",
                13,
            ),
            ui.card(
                ui.centered_text(self.code, 26, ui.W_BOLD, theme.PRIMARY_DARK),
                padding=22,
                bgcolor=theme.PRIMARY_SOFT,
                radius=22,
            ),
            ui.soft_button("Скопировать код", lambda e: app.copy(self.code)),
            self.saved,
            ui.primary_button("Продолжить" if self.user else "Готово", app.guard(self.done)),
            ui.spacer(8),
        ]

    def done(self) -> None:
        if not self.saved.value:
            return self.app.toast("Отметьте, что сохранили код", error=True)
        if self.user is not None:
            self.app.after_auth(self.user)
        else:
            self.app.pop()


class ResetPasswordScreen(Screen):
    title = "Новый пароль"
    refresh_on_return = False

    def __init__(self, app, email: str = ""):
        super().__init__(app)
        self.email = ui.field("Электронная почта", email, prefix="MAIL_OUTLINE", keyboard=ft.KeyboardType.EMAIL)
        self.code = ui.field("Код восстановления", prefix="VPN_KEY", hint="K7M2-QX9R-4TPD")
        self.password = ui.field(
            "Новый пароль (не менее 8 символов)", password=True, prefix="LOCK_OUTLINE",
            on_submit=app.guard(self.submit),
        )

    def body(self):
        return [
            ui.title("Забыли пароль?", 28),
            ui.muted("Введите почту, код восстановления из регистрации и новый пароль.", 14),
            ui.spacer(4),
            self.email,
            self.code,
            self.password,
            ui.spacer(4),
            ui.primary_button("Задать новый пароль", self.app.guard(self.submit)),
            ui.muted(
                "Нет кода? Тогда пароль восстановить нельзя: код нужен, чтобы подтвердить, что аккаунт ваш.",
                12,
                text_align=ft.TextAlign.CENTER,
            ),
        ]

    def submit(self) -> None:
        email = (self.email.value or "").strip()
        code = (self.code.value or "").strip()
        password = self.password.value or ""
        if not EMAIL_RE.match(email):
            return self.app.toast("Проверьте адрес электронной почты", error=True)
        if len(code) < 8:
            return self.app.toast("Введите код восстановления целиком", error=True)
        if len(password) < 8:
            return self.app.toast("Пароль: не менее 8 символов", error=True)
        data = self.app.api.reset_password(email, code, password)
        self.app.show_root(RecoveryCodeScreen(self.app, data["recovery_code"], data["user"], after_reset=True))
