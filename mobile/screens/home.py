"""Главная: шапка, итог за сегодня, мои привычки, баннеры. Акцент сделан на привычках."""

from datetime import date, datetime

import flet as ft

import theme
from api import ApiError
from components import common as ui
from components.carousel import Carousel, banner
from components.habit_card import habit_card
from core import Screen

# порядок на главной: ждущие отметки сверху, затем «сегодня отдых», выполненные ниже
_STATUS_ORDER = {"pending": 0, "missed": 0, "off": 1, "done": 2}


class HomeScreen(Screen):
    tab_index = 0

    def __init__(self, app):
        super().__init__(app)
        self._carousel: Carousel | None = None
        self._pop: list[ft.Control] = []  # кнопки-отметки, которые нужно «выпрыгнуть» после показа
        self._popping_ids: set[int] = set()  # привычки, отмеченные только что (по нажатию на кружок)
        self.view.floating_action_button = ft.FloatingActionButton(
            icon=ui.icon("ADD"),
            bgcolor=theme.PRIMARY,
            foreground_color=theme.WHITE,
            tooltip="Новая привычка",
            on_click=lambda e: self.new_habit(),
        )

    def body(self):
        app, api = self.app, self.app.api
        me = api.get("/me")
        app.me = me
        habits = api.get("/habits")
        invites = api.get("/invites")
        nudges = api.get("/nudges")
        has_unread = any(not n["read"] for n in nudges)

        from screens.habit import HabitScreen
        from screens.notifications import NotificationsScreen

        self._pop = []

        controls: list[ft.Control] = [self._header(me, has_unread, NotificationsScreen)]

        for invite in invites:
            controls.append(self._invite_card(invite))

        if habits:
            controls.append(self._today_card(habits))

        controls.append(
            ft.Row(
                [
                    ui.txt("Мои привычки", 20, ui.W_BOLD),
                    ui.muted(str(len(habits)) if habits else "", 14),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        if not habits:
            controls.append(ui.empty_state("Пока нет привычек. Начните с одной маленькой, лучше вместе с другом."))
            controls.append(ui.primary_button("Создать привычку", lambda e: self.new_habit()))
        for habit in sorted(habits, key=lambda h: _STATUS_ORDER.get(h["today_status"], 1)):
            card, button = habit_card(
                app,
                habit,
                on_open=lambda e, h=habit: app.push(HabitScreen(app, h["id"])),
                on_toggle=app.guard(lambda h=habit: self.toggle(h)),
                pop=habit["id"] in self._popping_ids,
            )
            if habit["id"] in self._popping_ids:
                self._pop.append(button)
            controls.append(card)
        self._popping_ids = set()

        if any(h["today_status"] == "missed" for h in habits):
            controls.append(self._sos_card())

        controls.append(self._banners(me, habits))
        controls.append(ui.spacer(72))  # запас под плавающую кнопку «+»
        return controls

    def refresh(self) -> None:
        if self._carousel:
            self._carousel.stop()  # прежняя карусель больше не нужна: экран перестраивается
            self._carousel = None
        super().refresh()
        # после показа экрана: карусель начинает листать, а новая отметка «выпрыгивает»
        if self._carousel:
            self._carousel.start()
        if self._pop:
            for button in self._pop:
                button.scale = 1
            self._pop = []
            self.app.page.update()

    # ---------- части экрана ----------

    def _header(self, me: dict, has_unread: bool, notifications_screen) -> ft.Row:
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
        avatar = ft.Container(
            content=ui.avatar(app, me["name"], me.get("avatar_url"), 20),
            on_click=lambda e: app.open_tab(2),
            tooltip="Профиль",
        )
        return ft.Row(
            [
                ui.logo_mark(46),
                ft.Column(
                    [
                        ui.wordmark(18),
                        ui.muted(ui.greeting(me["name"], datetime.now().hour), 12, max_lines=1,
                                 overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                    spacing=0,
                    expand=True,
                ),
                bell,
                avatar,
            ],
            spacing=10,
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

        if not scheduled:
            return ui.card(
                ft.Row(
                    [
                        ui.illustration("sprout", 56),
                        ft.Column(
                            [ui.txt("Сегодня", 18, ui.W_BOLD),
                             ui.muted("Привычек по расписанию нет. Отдыхайте!", 13)],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=14,
                )
            )

        ring = ft.Stack(
            [
                ft.ProgressRing(value=percent / 100, width=76, height=76, stroke_width=9,
                                color=theme.GREEN, bgcolor=theme.BORDER),
                ft.Container(
                    width=76,
                    height=76,
                    alignment=ft.alignment.center,
                    content=ui.txt(f"{len(done)}/{len(scheduled)}", 17, ui.W_BOLD),
                ),
            ],
            width=76,
            height=76,
        )
        if pending:
            caption = f"Осталось отметить: {len(pending)}"
            action = ui.small_button("Отметить привычки", lambda e: self.mark_dialog(pending))
        else:
            caption = "Всё отмечено, так держать! 🎉"
            action = ui.muted("Завтра продолжим", 12)
        return ui.card(
            ft.Row(
                [
                    ring,
                    ft.Column(
                        [ui.txt("Сегодня", 20, ui.W_BOLD), ui.muted(caption, 13), action],
                        spacing=6,
                        expand=True,
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=18,
        )

    def _sos_card(self) -> ft.Container:
        from screens.sos import SosScreen

        app = self.app
        return ui.card(
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

    def _banners(self, me: dict, habits: list[dict]) -> ft.Control:
        """Карусель: подсказывает, что ещё умеет приложение. Первым идёт то, что сейчас нужнее."""
        from screens.articles import ArticleScreen
        from screens.sos import SosScreen

        app = self.app
        images = "images/banners/"
        code = ui.format_code(me["friend_code"])
        slides: list[tuple[str, ft.Container]] = []

        article = self._article_of_the_day()
        if article:
            slides.append((
                "article",
                banner(images + "article.png", "Статья дня",
                       f"{article['title']} · {article['reading_minutes']} мин", "Читать",
                       lambda e: app.push(ArticleScreen(app, article["id"])), theme.BLUE),
            ))
        slides.append((
            "habit",
            banner(images + "habit.png", "Своя привычка", "Создайте привычку под себя или выберите шаблон",
                   "Создать", lambda e: self.new_habit(), theme.GREEN),
        ))
        slides.append((
            "friends",
            banner(images + "friends.png", "Позови друга", f"Ваш код {code}. Вдвоём привычки получаются легче",
                   "Скопировать код", lambda e: app.copy(code), theme.ORANGE),
        ))
        slides.append((
            "sos",
            banner(images + "sos.png", "SOS-бот", "Тяжело или сорвались? Поддержим без осуждения",
                   "Открыть", lambda e: app.push(SosScreen(app)), theme.PRIMARY),
        ))
        slides.append((
            "soon",
            banner(images + "soon.png", "Скоро: поиск друзей", "Находите напарников с похожими целями",
                   "Скоро"),
        ))

        # что нужнее прямо сейчас — первым: после срыва SOS-бот, без друзей приглашение
        first = None
        if any(h["today_status"] == "missed" for h in habits):
            first = "sos"
        elif not me.get("friends_count"):
            first = "friends"
        if first:
            slides.sort(key=lambda item: item[0] != first)  # сортировка устойчивая: остальное в прежнем порядке

        page = app.page
        self._carousel = Carousel(
            page,
            [slide for _, slide in slides],
            is_alive=lambda: bool(page.views) and page.views[-1] is self.view,
        )
        return self._carousel.control

    def _article_of_the_day(self) -> dict | None:
        """Статья дня: меняется каждый день по кругу. Без статей или при сбое сети — без неё."""
        try:
            articles = self.app.api.get("/articles")
        except ApiError:
            return None
        if not articles:
            return None
        return articles[date.today().toordinal() % len(articles)]

    # ---------- действия ----------

    def new_habit(self) -> None:
        from screens.create_habit import TemplatePickerScreen

        self.app.push(TemplatePickerScreen(self.app))

    def toggle(self, habit: dict) -> None:
        api = self.app.api
        status = habit["today_status"]
        if status == "off":
            return self.app.toast("По расписанию сегодня отдых. Отметить можно на странице привычки.")
        if status == "done":
            api.delete(f"/habits/{habit['id']}/check-ins/{habit['today']}")
        else:
            api.post(f"/habits/{habit['id']}/check-ins", {"status": "done"})
            self._popping_ids = {habit["id"]}  # новая отметка «выпрыгнет» при перерисовке
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
