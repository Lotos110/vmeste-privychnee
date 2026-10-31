"""Каркас приложения: навигация, диалоги, обработка ошибок, базовый класс экрана."""

import logging

import flet as ft

import api as api_module
import theme
from api import Api, ApiError, Storage
from components import common as ui

log = logging.getLogger("vmeste")

# Вкладки нижнего меню. Номер вкладки (tab_index у экрана, аргумент open_tab) — место в этом списке:
# 0 Главная, 1 Поиск, 2 Рейтинг, 3 Статьи, 4 Профиль.
TAB_HOME, TAB_SEARCH, TAB_RATING, TAB_ARTICLES, TAB_PROFILE = range(5)
TABS = [
    ("Главная", "HOME_OUTLINED", "HOME"),
    ("Поиск", "PEOPLE_OUTLINE", "PEOPLE"),
    ("Рейтинг", "EMOJI_EVENTS_OUTLINED", "EMOJI_EVENTS"),
    ("Статьи", "ARTICLE_OUTLINED", "ARTICLE"),
    ("Профиль", "PERSON_OUTLINE", "PERSON"),
]


def visible_tabs(me: dict | None) -> list[int]:
    """Номера вкладок, которые видит человек: «Поиск» скрыт для младше 12 лет (раздел с 12)."""
    hidden = {TAB_SEARCH} if me and me.get("community") == "too_young" else set()
    return [i for i in range(len(TABS)) if i not in hidden]


class Screen:
    """Экран = View + загрузка данных. Наследник переопределяет body()."""

    title = ""
    tab_index: int | None = None  # у корневых вкладок: их номер в TABS
    show_appbar = True
    refresh_on_return = True  # перезагружать данные, когда пользователь вернулся на экран

    def __init__(self, app: "App"):
        self.app = app
        self.content = ft.Column(
            controls=[ui.loading()],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        self.view = ft.View(
            route=f"/{type(self).__name__.lower()}",
            bgcolor=theme.BG,
            padding=0,
            spacing=0,
            appbar=self._build_appbar(),
            navigation_bar=self._build_nav(),
            controls=[
                ft.SafeArea(
                    expand=True,
                    content=ft.Container(
                        expand=True,
                        padding=ft.padding.only(left=16, right=16, top=8),
                        content=self.content,
                    ),
                )
            ],
        )
        self.view.data = self

    # ---------- что переопределяют экраны ----------

    def body(self) -> list[ft.Control]:
        raise NotImplementedError

    def appbar_actions(self) -> list[ft.Control]:
        return []

    # ---------- общая часть ----------

    def _build_appbar(self):
        if self.tab_index is not None or not self.show_appbar:
            return None
        return ft.AppBar(
            title=ui.txt(self.title, 18, ui.W_SEMI),
            center_title=True,
            bgcolor=theme.BG,
            elevation=0,
            leading=ft.IconButton(
                icon=ui.icon("ARROW_BACK_IOS_NEW"),
                icon_size=18,
                icon_color=theme.TEXT,
                on_click=lambda e: self.app.pop(),
            ),
            actions=self.appbar_actions(),
        )

    def _build_nav(self):
        if self.tab_index is None:
            return None
        shown = visible_tabs(self.app.me)
        if self.tab_index not in shown:
            shown.append(self.tab_index)
            shown.sort()
        return ft.NavigationBar(
            selected_index=shown.index(self.tab_index),
            bgcolor=theme.CARD,
            indicator_color=theme.PRIMARY_SOFT,
            on_change=lambda e: self.app.open_tab(shown[int(e.control.selected_index)]),
            destinations=[
                ft.NavigationBarDestination(
                    icon=ui.icon(TABS[i][1]), selected_icon=ui.icon(TABS[i][2]), label=TABS[i][0]
                )
                for i in shown
            ],
        )

    def refresh(self) -> None:
        """Загружает данные и перерисовывает экран. Безопасно вызывать из потока."""
        try:
            controls = self.body()
        except ApiError as err:
            if err.status == 401:  # сессия потеряна, приложение уже вернуло на экран входа
                return
            controls = [ui.error_box(err.message, lambda e: self.refresh())]
        except Exception:
            log.exception("Ошибка при построении экрана %s", type(self).__name__)
            controls = [ui.error_box("Что-то пошло не так.", lambda e: self.refresh())]
        self.content.controls = controls
        self.app.page.update()


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.api = Api(Storage(self._client_storage(page)), on_auth_lost=self._auth_lost)
        self.me: dict | None = None

    @staticmethod
    def _client_storage(page):
        try:
            return page.client_storage
        except Exception:
            return None

    # ---------- запуск ----------

    def start(self) -> None:
        page = self.page
        page.title = "Вместе привычнее"
        page.bgcolor = theme.BG
        page.padding = 0
        page.theme_mode = ft.ThemeMode.LIGHT
        page.fonts = dict(theme.FONT_FILES)
        page.theme = ft.Theme(color_scheme_seed=theme.PRIMARY, font_family=theme.FONT_BODY)
        # русская локаль: календарь, системные подписи и клавиатура по-русски
        page.locale_configuration = ft.LocaleConfiguration(
            supported_locales=[ft.Locale("ru", "RU")],
            current_locale=ft.Locale("ru", "RU"),
        )
        try:  # размер окна важен только для запуска на компьютере
            page.window.width = 390
            page.window.height = 800
        except Exception:
            pass
        page.on_view_pop = lambda e: self.pop()

        page.views.clear()
        page.views.append(ft.View(route="/", bgcolor=theme.BG, controls=[ui.loading()]))
        page.update()

        from screens.welcome import WelcomeScreen

        if not self.api.has_session():
            self.show_root(WelcomeScreen(self))
            return
        try:
            self.me = self.api.get("/me")
        except ApiError as err:
            if err.status == 0:  # сервер недоступен: не разлогиниваем, а даём повторить
                self.show_root(WelcomeScreen(self, offline_message=err.message))
            elif err.status != 401:  # при 401 экран приветствия уже показал on_auth_lost
                self.show_root(WelcomeScreen(self))
            return
        self.sync_timezone()
        self.open_tab(0)

    def sync_timezone(self) -> None:
        """Если пользователь переехал в другой часовой пояс, сообщаем серверу: день считается по нему."""
        try:
            tz = api_module.detect_timezone()
            if self.me and tz and tz != self.me.get("timezone"):
                self.me = self.api.patch("/me", {"timezone": tz})
        except Exception:
            log.info("Не удалось обновить часовой пояс", exc_info=True)

    # ---------- навигация ----------

    def show_root(self, screen: Screen) -> None:
        self.page.views.clear()
        self.page.views.append(screen.view)
        self.page.update()
        self.page.run_thread(screen.refresh)

    def open_tab(self, index: int) -> None:
        from screens.articles import ArticlesScreen
        from screens.feed import FeedScreen
        from screens.home import HomeScreen
        from screens.profile import ProfileScreen
        from screens.rating import RatingScreen

        screens = [HomeScreen, FeedScreen, RatingScreen, ArticlesScreen, ProfileScreen]
        self.show_root(screens[index](self))

    def push(self, screen: Screen) -> None:
        self.page.views.append(screen.view)
        self.page.update()
        self.page.run_thread(screen.refresh)

    def pop(self) -> None:
        if len(self.page.views) <= 1:
            return
        self.page.views.pop()
        top = self.page.views[-1]
        self.page.update()
        screen = top.data
        if isinstance(screen, Screen) and screen.refresh_on_return:
            self.page.run_thread(screen.refresh)

    def pop_to_root(self) -> None:
        while len(self.page.views) > 1:
            self.page.views.pop()
        top = self.page.views[-1]
        self.page.update()
        screen = top.data
        if isinstance(screen, Screen):
            self.page.run_thread(screen.refresh)

    def after_auth(self, user: dict) -> None:
        self.me = user
        self.open_tab(0)

    def logout(self) -> None:
        self.api.logout()
        self._auth_lost()

    def _auth_lost(self) -> None:
        from screens.welcome import WelcomeScreen

        self.me = None
        self.show_root(WelcomeScreen(self))

    # ---------- обработка ошибок и уведомления ----------

    def guard(self, action):
        """Оборачивает обработчик: ошибки API показываются сообщением, а не роняют приложение."""

        def handler(e=None):
            try:
                action()
            except ApiError as err:
                if err.status != 401:
                    self.toast(err.message, error=True)
            except Exception:
                log.exception("Ошибка в обработчике")
                self.toast("Что-то пошло не так. Попробуйте ещё раз.", error=True)

        return handler

    def toast(self, message: str, error: bool = False) -> None:
        self.page.open(
            ft.SnackBar(
                content=ui.txt(message, 14, color=theme.WHITE),
                bgcolor=theme.RED if error else theme.TEXT,
            )
        )

    def copy(self, text: str) -> None:
        self.page.set_clipboard(text)
        self.toast("Скопировано")

    def open_url(self, url: str) -> None:
        self.page.launch_url(url)

    # ---------- диалоги ----------

    def dialog(self, title: str, content: ft.Control | None, actions: list[tuple[str, object]]):
        """actions: [(подпись, функция)]. Диалог закрывается перед вызовом функции."""
        dlg = ft.AlertDialog(modal=True, title=ui.txt(title, 18, ui.W_BOLD), content=content)

        def wrap(fn):
            def handler(e):
                self.page.close(dlg)
                if fn:
                    self.guard(fn)(e)

            return handler

        dlg.actions = [ft.TextButton(label, on_click=wrap(fn)) for label, fn in actions]
        dlg.actions_alignment = ft.MainAxisAlignment.END
        self.page.open(dlg)
        return dlg

    def confirm(self, title: str, text: str, yes_label: str, on_yes) -> None:
        self.dialog(title, ft.Text(text), [("Отмена", None), (yes_label, on_yes)])
