"""Поиск напарника: лента объявлений, создание объявления, мои объявления и отклики.

Раздел открыт с 12 лет (подростки видят подростков, взрослые взрослых). Контакты в текстах нельзя:
сервер их не пропустит. Принятый отклик делает людей друзьями.
"""

from datetime import datetime

import flet as ft

import theme
from components import common as ui
from core import TAB_SEARCH, Screen

TIMES = [("any", "Любое время"), ("morning", "Утро"), ("day", "День"), ("evening", "Вечер")]
TIME_TITLES = dict(TIMES)
REASONS = [
    ("contacts", "Контакты, ссылки или реклама"),
    ("rude", "Грубость или оскорбления"),
    ("adult", "Неприличное содержание"),
    ("spam", "Спам"),
    ("other", "Другое"),
]
RULES = "Без ссылок, телефонов и @ников: общайтесь здесь, в приложении. Будьте вежливы."


def pill(text: str, bg: str, fg: str) -> ft.Container:
    return ft.Container(
        content=ui.txt(text, 12, ui.W_SEMI, fg),
        bgcolor=bg,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
    )


def days_left(iso: str) -> str:
    try:
        moment = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        days = max(0, (moment - datetime.now(moment.tzinfo)).days)
    except ValueError:
        return ""
    return f"ещё {ui.days_text(days)}" if days else "заканчивается сегодня"


def gate_view(app, me: dict) -> list[ft.Control]:
    """Что показать вместо ленты, если раздел закрыт (нет даты рождения или младше 12 лет)."""
    if me.get("community") == "too_young":
        return [ui.title("Поиск напарника", 24),
                ui.empty_state("Этот раздел доступен с 12 лет. Пока можно заниматься привычками с друзьями.",
                               art="friends")]

    def edit() -> None:
        from screens.profile import EditProfileScreen

        app.push(EditProfileScreen(app, me))

    return [
        ui.title("Поиск напарника", 24),
        ui.empty_state("Раздел открыт с 12 лет. Укажите дату рождения в профиле: она нужна только для проверки "
                       "возраста и никому не видна.", art="search"),
        ui.primary_button("Указать дату рождения", lambda e: edit()),
    ]


class FeedScreen(Screen):
    tab_index = TAB_SEARCH
    title = "Поиск напарника"

    def __init__(self, app):
        self.template_id: int | None = None
        self.time_pref = "any"
        super().__init__(app)

    def body(self):
        app, api = self.app, self.app.api
        me = api.get("/me")
        app.me = me
        if me.get("community") != "ok":
            return gate_view(app, me)

        templates = api.get("/templates")
        params = {}
        if self.template_id is not None:
            params["template_id"] = self.template_id
        if self.time_pref != "any":
            params["time_pref"] = self.time_pref
        posts = api.get("/partner-posts", params=params or None)
        mine = api.get("/partner-posts/mine")
        waiting = sum(1 for p in mine for r in p["responses"] if r["status"] == "pending")

        controls: list[ft.Control] = [
            ui.title("Поиск напарника", 24),
            ui.muted("Найдите человека, с которым привычки получаются легче", 13),
            ft.Row(
                [
                    ft.Container(expand=1, content=ui.primary_button("Создать объявление", lambda e: self.create())),
                ]
            ),
            ui.menu_row(
                "FORUM_OUTLINED",
                "Мои объявления",
                lambda e: app.push(MyPostsScreen(app)),
                f"Новых откликов: {waiting}" if waiting else "Отклики на ваши объявления",
                theme.GREEN,
                theme.GREEN_SOFT,
            ),
            ft.Row(
                [ui.chip("Все привычки", self.template_id is None, lambda e: self.set_template(None))]
                + [
                    ui.chip(t["title"], self.template_id == t["id"], lambda e, i=t["id"]: self.set_template(i))
                    for t in templates
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=8,
            ),
            ft.Row(
                [ui.chip(label, self.time_pref == key, lambda e, k=key: self.set_time(k)) for key, label in TIMES],
                scroll=ft.ScrollMode.AUTO,
                spacing=8,
            ),
        ]
        if not posts:
            controls.append(
                ui.empty_state("Пока нет подходящих объявлений. Создайте своё: возможно, напарник уже ищет вас.",
                               art="search")
            )
        for post in posts:
            controls.append(self._post_card(post))
        controls.append(ui.muted(RULES, 11, text_align=ft.TextAlign.CENTER))
        controls.append(ui.spacer(8))
        return controls

    # ---------- фильтры ----------

    def set_template(self, template_id: int | None) -> None:
        self.template_id = template_id
        self.refresh()

    def set_time(self, key: str) -> None:
        self.time_pref = key
        self.refresh()

    def create(self) -> None:
        self.app.push(CreatePostScreen(self.app))

    # ---------- карточка объявления ----------

    def _post_card(self, post: dict) -> ft.Control:
        author = post["author"]
        menu = ft.PopupMenuButton(
            icon=ui.icon("MORE_VERT"),
            icon_color=theme.MUTED,
            items=[
                ft.PopupMenuItem(text="Пожаловаться", on_click=lambda e, p=post: self.report(p)),
                ft.PopupMenuItem(text="Заблокировать автора", on_click=lambda e, p=post: self.block(p)),
            ],
        )
        if post["responded"]:
            action: ft.Control = ui.muted("Вы откликнулись", 13)
        else:
            action = ui.small_button("Откликнуться", lambda e, p=post: self.respond(p))
        return ui.card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ui.avatar(self.app, author["name"], author.get("avatar_url"), 20),
                            ft.Column(
                                [ui.txt(author["name"], 15, ui.W_SEMI), ui.muted(days_left(post["expires_at"]), 11)],
                                spacing=0,
                                expand=True,
                            ),
                            menu,
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            pill(post["topic"], theme.PRIMARY_SOFT, theme.PRIMARY),
                            pill(TIME_TITLES.get(post["time_pref"], ""), theme.BLUE_SOFT, theme.BLUE),
                        ],
                        spacing=6,
                        wrap=True,
                    ),
                    ui.txt(post["text"], 14),
                    ft.Row([action], alignment=ft.MainAxisAlignment.END),
                ],
                spacing=10,
            ),
            padding=14,
        )

    # ---------- действия ----------

    def respond(self, post: dict) -> None:
        app = self.app
        text = ui.field("Сообщение автору", multiline=True, max_length=200,
                        hint="Например: давайте бегать вместе по вторникам")

        def send() -> None:
            message = (text.value or "").strip()
            if len(message) < 2:
                return app.toast("Напишите пару слов автору", error=True)
            app.api.post(f"/partner-posts/{post['id']}/respond", {"text": message})
            app.toast("Отклик отправлен. Автор увидит его в уведомлениях.")
            self.refresh()

        app.dialog(
            f"Отклик: {post['topic']}",
            ft.Column([ui.muted(RULES, 12), text], tight=True, spacing=10),
            [("Отмена", None), ("Отправить", send)],
        )

    def report(self, post: dict) -> None:
        report_dialog(self.app, f"/partner-posts/{post['id']}/report", "Спасибо, мы проверим объявление",
                      after=self.refresh)

    def block(self, post: dict) -> None:
        author = post["author"]

        def do_block() -> None:
            self.app.api.post(f"/users/{author['id']}/block")
            self.app.toast(f"{author['name']} заблокирован(а). Объявления этого человека вы больше не увидите.")
            self.refresh()

        self.app.confirm(
            "Заблокировать автора?",
            f"{author['name']} пропадёт из ленты, а вы пропадёте из ленты у этого человека. "
            "Если вы дружили, дружба закончится. Разблокировать можно в профиле.",
            "Заблокировать",
            do_block,
        )


def report_dialog(app, url: str, thanks: str, after=None) -> None:
    group = ft.RadioGroup(
        value=REASONS[0][0],
        content=ft.Column([ft.Radio(value=key, label=label) for key, label in REASONS], tight=True, spacing=0),
    )

    def send() -> None:
        app.api.post(url, {"reason": group.value or "other"})
        app.toast(thanks)
        if after:
            after()

    app.dialog("На что жалоба?", group, [("Отмена", None), ("Отправить", send)])


class CreatePostScreen(Screen):
    title = "Новое объявление"
    refresh_on_return = False

    def __init__(self, app):
        super().__init__(app)
        self.templates: list[dict] = []
        self.template_id: int | None = None
        self.custom = False
        self.time_pref = "any"
        self.topic = ui.field("Своя тема", max_length=60, hint="Например: учить английский")
        self.text = ui.field("О чём вы ищете напарника", multiline=True, max_length=300,
                             hint="Например: хочу бегать по утрам три раза в неделю, ищу того, кто подтянет")
        self.topics_row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=8)
        self.times_row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=8)
        self.topic_holder = ft.Container()

    def body(self):
        self.templates = self.app.api.get("/templates")
        if self.template_id is None and not self.custom and self.templates:
            self.template_id = self.templates[0]["id"]
        self._render_choices()
        return [
            ui.muted("Расскажите, какую привычку хотите делать вместе. Объявление увидят люди вашей возрастной "
                     "группы, оно живёт 30 дней.", 13),
            ui.txt("Привычка", 14, ui.W_SEMI),
            self.topics_row,
            self.topic_holder,
            ui.txt("Удобное время", 14, ui.W_SEMI),
            self.times_row,
            self.text,
            ui.muted(RULES + " Не больше 3 активных объявлений.", 12),
            ui.primary_button("Опубликовать", self.app.guard(self.publish)),
            ui.spacer(8),
        ]

    def _render_choices(self) -> None:
        self.topics_row.controls = [
            ui.chip(t["title"], not self.custom and self.template_id == t["id"],
                    lambda e, i=t["id"]: self.pick_template(i))
            for t in self.templates
        ] + [ui.chip("Своя тема", self.custom, lambda e: self.pick_custom())]
        self.topic_holder.content = self.topic if self.custom else None
        self.times_row.controls = [
            ui.chip(label, self.time_pref == key, lambda e, k=key: self.pick_time(k)) for key, label in TIMES
        ]

    def _redraw(self) -> None:
        self._render_choices()
        self.app.page.update()

    def pick_template(self, template_id: int) -> None:
        self.template_id, self.custom = template_id, False
        self._redraw()

    def pick_custom(self) -> None:
        self.template_id, self.custom = None, True
        self._redraw()

    def pick_time(self, key: str) -> None:
        self.time_pref = key
        self._redraw()

    def publish(self) -> None:
        text = (self.text.value or "").strip()
        topic = (self.topic.value or "").strip()
        if self.custom and not topic:
            return self.app.toast("Впишите свою тему", error=True)
        if len(text) < 10:
            return self.app.toast("Расскажите чуть подробнее: не меньше 10 символов", error=True)
        self.app.api.post(
            "/partner-posts",
            {
                "template_id": None if self.custom else self.template_id,
                "topic": topic if self.custom else None,
                "text": text,
                "time_pref": self.time_pref,
            },
        )
        self.app.toast("Объявление опубликовано")
        self.app.pop()


class MyPostsScreen(Screen):
    title = "Мои объявления"

    def body(self):
        app = self.app
        posts = app.api.get("/partner-posts/mine")
        if not posts:
            return [
                ui.empty_state("У вас пока нет объявлений. Создайте первое на вкладке «Поиск».", art="search"),
            ]
        controls: list[ft.Control] = []
        for post in posts:
            controls.append(self._post_card(post))
        controls.append(ui.spacer(8))
        return controls

    def _post_card(self, post: dict) -> ft.Control:
        if post["status"] == "hidden":
            state = pill("Скрыто после жалоб", theme.RED_SOFT, theme.RED)
        elif post["expired"]:
            state = pill("Срок вышел", theme.BG, theme.MUTED)
        else:
            state = pill(days_left(post["expires_at"]), theme.GREEN_SOFT, theme.GREEN)
        column: list[ft.Control] = [
            ft.Row([pill(post["topic"], theme.PRIMARY_SOFT, theme.PRIMARY), state], spacing=6, wrap=True),
            ui.txt(post["text"], 14),
        ]
        if post["status"] == "hidden":
            column.append(ui.muted("Объявление проверяет модератор. Пока оно не видно в ленте.", 12))
        responses = post["responses"]
        if responses:
            column.append(ui.txt(f"Отклики: {len(responses)}", 14, ui.W_SEMI))
            column += [self._response(post, r) for r in responses]
        else:
            column.append(ui.muted("Откликов пока нет", 12))
        column.append(
            ft.Row(
                [ui.small_button("Закрыть объявление", lambda e, p=post: self.close(p), filled=False)],
                alignment=ft.MainAxisAlignment.END,
            )
        )
        return ui.card(ft.Column(column, spacing=10), padding=14)

    def _response(self, post: dict, response: dict) -> ft.Control:
        person = response["person"]
        status = response["status"]
        head = ft.Row(
            [
                ui.avatar(self.app, person["name"], person.get("avatar_url"), 18),
                ui.txt(person["name"], 14, ui.W_SEMI, expand=True),
                ft.PopupMenuButton(
                    icon=ui.icon("MORE_VERT"),
                    icon_color=theme.MUTED,
                    items=[
                        ft.PopupMenuItem(text="Пожаловаться", on_click=lambda e, r=response: self.report(r)),
                        ft.PopupMenuItem(text="Заблокировать", on_click=lambda e, p=person: self.block(p)),
                    ],
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        parts: list[ft.Control] = [head, ui.txt(response["text"], 13)]
        if status == "pending":
            parts.append(
                ft.Row(
                    [
                        ui.small_button("Принять", lambda e, p=post, r=response: self.accept(p, r)),
                        ui.small_button("Отклонить", lambda e, p=post, r=response: self.decline(p, r), filled=False),
                    ],
                    spacing=8,
                )
            )
        elif status == "accepted":
            parts.append(
                ft.Row(
                    [
                        pill("Принято: вы друзья", theme.GREEN_SOFT, theme.GREEN),
                        ui.small_button("Создать привычку вместе", lambda e: self.create_habit(), filled=False),
                    ],
                    spacing=8,
                    wrap=True,
                )
            )
        else:
            parts.append(ui.muted("Отклонено", 12))
        return ft.Container(
            content=ft.Column(parts, spacing=6),
            bgcolor=theme.BG,
            border_radius=14,
            padding=10,
        )

    # ---------- действия ----------

    def accept(self, post: dict, response: dict) -> None:
        name = response["person"]["name"]
        self.app.api.post(f"/partner-posts/{post['id']}/responses/{response['id']}/accept")
        self.app.toast(f"{name} теперь ваш друг. Можно создать общую привычку.")
        self.refresh()

    def decline(self, post: dict, response: dict) -> None:
        self.app.api.post(f"/partner-posts/{post['id']}/responses/{response['id']}/decline")
        self.refresh()

    def close(self, post: dict) -> None:
        def do_close() -> None:
            self.app.api.delete(f"/partner-posts/{post['id']}")
            self.refresh()

        self.app.confirm("Закрыть объявление?", "Оно пропадёт из ленты. Новые отклики приходить не будут.",
                         "Закрыть", do_close)

    def report(self, response: dict) -> None:
        report_dialog(self.app, f"/partner-responses/{response['id']}/report",
                      "Спасибо, отклик скрыт. Мы проверим его.", after=self.refresh)

    def block(self, person: dict) -> None:
        def do_block() -> None:
            self.app.api.post(f"/users/{person['id']}/block")
            self.app.toast(f"{person['name']} заблокирован(а)")
            self.refresh()

        self.app.confirm("Заблокировать человека?",
                         "Его отклики пропадут, а вы друг друга больше не увидите в ленте. "
                         "Если вы дружили, дружба закончится.", "Заблокировать", do_block)

    def create_habit(self) -> None:
        from screens.create_habit import TemplatePickerScreen

        self.app.push(TemplatePickerScreen(self.app))


class BlockedScreen(Screen):
    """Список заблокированных: здесь блокировку можно снять."""

    title = "Заблокированные"

    def body(self):
        people = self.app.api.get("/blocks")["blocked"]
        if not people:
            return [ui.empty_state("Вы никого не блокировали", art="friends")]
        controls: list[ft.Control] = []
        for person in people:
            controls.append(
                ui.card(
                    ft.Row(
                        [
                            ui.avatar(self.app, person["name"], person.get("avatar_url"), 20),
                            ui.txt(person["name"], 15, ui.W_SEMI, expand=True),
                            ui.small_button("Разблокировать", lambda e, p=person: self.unblock(p), filled=False),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=12,
                    radius=16,
                )
            )
        return controls

    def unblock(self, person: dict) -> None:
        self.app.api.delete(f"/users/{person['id']}/block")
        self.app.toast(f"{person['name']} разблокирован(а)")
        self.refresh()
