"""Рейтинг: «Серия» и «Неделя», списки «Друзья», «Все» и «По привычке».

Сервер сам считает места (GET /ratings). Общий список и список по привычке видят только те, кто сам
включил участие, и только свою возрастную группу; друзья видны друг другу всегда.
"""

import flet as ft

import theme
from components import common as ui
from core import TAB_RATING, Screen

METRICS = [("streak", "Серия"), ("week", "Неделя")]
SCOPES = [("friends", "Друзья"), ("global", "Все"), ("habit", "По привычке")]

MEDALS = {1: "#F2B93B", 2: "#A9B1C6", 3: "#D98B55"}  # золото, серебро, бронза


def value_text(metric: str, value: int) -> str:
    if metric == "streak":
        return ui.days_text(value)
    return f"{value} {ui.plural(value, ('отметка', 'отметки', 'отметок'))}"


def rank_badge(rank: int, size: int = 30) -> ft.Container:
    color = MEDALS.get(rank)
    return ft.Container(
        width=size,
        height=size,
        border_radius=size / 2,
        bgcolor=color or theme.BG,
        alignment=ft.alignment.center,
        content=ui.txt(str(rank), size * 0.45, ui.W_BOLD, theme.WHITE if color else theme.MUTED),
    )


class RatingScreen(Screen):
    tab_index = TAB_RATING
    title = "Рейтинг"

    def __init__(self, app):
        self.metric = "streak"
        self.scope = "friends"
        self.template_id: int | None = None
        super().__init__(app)

    # ---------- данные ----------

    def body(self):
        app, api = self.app, self.app.api
        me = api.get("/me")
        app.me = me
        access = me.get("community", "ok")

        controls: list[ft.Control] = [
            ui.title("Рейтинг", 24),
            ui.segmented([label for _, label in METRICS], self._index(METRICS, self.metric), self.set_metric),
        ]
        if access == "too_young":  # младше 12: только друзья, общих списков нет
            self.scope = "friends"
        else:
            controls.append(
                ui.segmented([label for _, label in SCOPES], self._index(SCOPES, self.scope), self.set_scope)
            )

        if self.scope != "friends" and access == "need_birth_date":
            controls += [
                ui.empty_state("Общий рейтинг открыт с 12 лет. Укажите дату рождения в профиле: "
                               "она нужна только для возраста и не видна другим.", art="trophy"),
                ui.primary_button("Указать дату рождения", lambda e: self.edit_profile(me)),
            ]
            return controls

        if self.scope == "habit":
            templates = api.get("/templates")
            if self.template_id is None or all(t["id"] != self.template_id for t in templates):
                self.template_id = templates[0]["id"] if templates else None
            controls.append(
                ft.Row(
                    [ui.chip(t["title"], t["id"] == self.template_id, lambda e, i=t["id"]: self.set_template(i))
                     for t in templates],
                    scroll=ft.ScrollMode.AUTO,
                    spacing=8,
                )
            )

        params = {"metric": self.metric, "scope": self.scope}
        if self.scope == "habit":
            params["template_id"] = self.template_id
        data = api.get("/ratings", params=params)

        controls.append(self._my_card(data))
        items = data["items"]
        if self.scope == "friends" and len(items) <= 1:
            controls.append(ui.empty_state("Пока вы здесь одни. Добавьте друзей по коду в профиле, "
                                           "и рейтинг станет интереснее.", art="friends"))
        elif not items:
            controls.append(ui.empty_state("Пока в списке никого. Отметьте привычку, и вы можете оказаться первым.",
                                           art="trophy"))
        if len(items) >= 3:
            controls.append(self._podium(items[:3]))
            items = items[3:]
        for item in items:
            controls.append(self._row(item))
        controls.append(ui.muted(self._footnote(), 11, text_align=ft.TextAlign.CENTER))
        controls.append(ui.spacer(8))
        return controls

    @staticmethod
    def _index(options, key: str) -> int:
        return next(i for i, (k, _) in enumerate(options) if k == key)

    # ---------- переключатели ----------

    def set_metric(self, index: int) -> None:
        self.metric = METRICS[index][0]
        self.refresh()

    def set_scope(self, index: int) -> None:
        self.scope = SCOPES[index][0]
        self.refresh()

    def set_template(self, template_id: int) -> None:
        self.template_id = template_id
        self.refresh()

    def edit_profile(self, me: dict) -> None:
        from screens.profile import EditProfileScreen

        self.app.push(EditProfileScreen(self.app, me))

    def join(self) -> None:
        self.app.me = self.app.api.patch("/me", {"is_public": True})
        self.app.toast("Вы участвуете в общем рейтинге")
        self.refresh()

    # ---------- части экрана ----------

    def _footnote(self) -> str:
        if self.metric == "streak":
            base = "Серия: дни подряд, в которые выполнена хотя бы одна привычка."
        else:
            base = "Неделя: сколько отметок «выполнено» за последние 7 дней."
        if self.scope == "friends":
            return base + " Отметки задним числом больше чем на день не считаются."
        return base + (" Общий список обновляется раз в несколько минут. В нём люди вашей возрастной группы, "
                       "которые сами включили участие. Отметки задним числом больше чем на день не считаются.")

    def _my_card(self, data: dict) -> ft.Control:
        me = data["me"]
        metric = data["metric"]
        if me["rank"] is not None:
            return ui.card(
                ft.Row(
                    [
                        rank_badge(me["rank"], 40),
                        ft.Column(
                            [ui.txt("Ваше место", 14, ui.W_SEMI), ui.muted(value_text(metric, me["value"]), 13)],
                            spacing=0,
                            expand=True,
                        ),
                        ui.txt(f"из {data['total']}", 13, color=theme.MUTED),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=14,
                bgcolor=theme.PRIMARY_SOFT,
                radius=18,
            )
        if not me["joined"]:  # общий список, а вы в нём не участвуете
            return ui.card(
                ft.Column(
                    [
                        ui.txt("Вас нет в общем списке", 15, ui.W_SEMI),
                        ui.muted("Участие добровольное: другие увидят ваше имя и аватар. "
                                 "Отключить можно в профиле в любой момент.", 12),
                        ui.small_button("Участвовать в рейтинге", self.app.guard(self.join)),
                    ],
                    spacing=8,
                ),
                padding=14,
                bgcolor=theme.PRIMARY_SOFT,
                radius=18,
            )
        return ui.card(
            ft.Column(
                [
                    ui.txt("Вы пока не в списке", 15, ui.W_SEMI),
                    ui.muted("Отметьте привычку сегодня, и вы появитесь здесь.", 12),
                ],
                spacing=4,
            ),
            padding=14,
            bgcolor=theme.PRIMARY_SOFT,
            radius=18,
        )

    def _podium(self, top: list[dict]) -> ft.Control:
        """Три первых места: второе слева, первое в центре и выше, третье справа."""
        metric = self.metric

        def column(item: dict, height: int, avatar_radius: int) -> ft.Column:
            person = item["person"]
            name = person["name"] + (" (вы)" if item["is_me"] else "")
            return ft.Column(
                [
                    ui.avatar(self.app, person["name"], person.get("avatar_url"), avatar_radius),
                    ui.txt(name, 12, ui.W_SEMI, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                           text_align=ft.TextAlign.CENTER),
                    ui.muted(value_text(metric, item["value"]), 11, text_align=ft.TextAlign.CENTER),
                    ft.Container(
                        height=height,
                        alignment=ft.alignment.top_center,
                        padding=ft.padding.only(top=8),
                        border_radius=ft.border_radius.only(top_left=14, top_right=14),
                        bgcolor=MEDALS[item["rank"]] if item["rank"] in MEDALS else theme.PRIMARY_SOFT,
                        content=ui.txt(str(item["rank"]), 20, ui.W_BOLD, theme.WHITE),
                    ),
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.END,
                expand=1,
            )

        first, second, third = top
        return ui.card(
            ft.Row(
                [column(second, 56, 24), column(first, 80, 30), column(third, 40, 24)],
                vertical_alignment=ft.CrossAxisAlignment.END,
                spacing=8,
            ),
            padding=ft.padding.only(left=12, right=12, top=16, bottom=0),
            radius=22,
        )

    def _row(self, item: dict) -> ft.Control:
        person = item["person"]
        mine = item["is_me"]
        return ui.card(
            ft.Row(
                [
                    rank_badge(item["rank"]),
                    ui.avatar(self.app, person["name"], person.get("avatar_url"), 20),
                    ui.txt(person["name"] + (" (вы)" if mine else ""), 14, ui.W_SEMI if mine else None,
                           expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ui.txt(value_text(self.metric, item["value"]), 13, ui.W_SEMI, theme.PRIMARY),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=10,
            radius=16,
            bgcolor=theme.PRIMARY_SOFT if mine else theme.CARD,
        )
