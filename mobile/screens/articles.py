"""Полезные статьи: список с фильтром по темам и страница статьи."""

import flet as ft

import theme
from components import common as ui
from components.habit_card import category_colors
from core import Screen

CATEGORIES = ["sleep", "nutrition", "sport", "water", "productivity", "mental", "relapse"]


def article_card(article: dict, on_click) -> ft.Container:
    bg, fg = category_colors(article["category"])
    icon_name = theme.CATEGORY_ICONS.get(article["category"], "ARTICLE")
    return ui.card(
        ft.Row(
            [
                ui.circle_icon(icon_name, bg, fg, 64),
                ft.Column(
                    [
                        ui.txt(article["title"], 15, ui.W_BOLD, max_lines=2,
                               overflow=ft.TextOverflow.ELLIPSIS),
                        ui.muted(article["summary"], 12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ui.muted(f"{theme.CATEGORY_TITLES.get(article['category'], '')} · {article['reading_minutes']} мин", 11),
                    ],
                    spacing=3,
                    expand=True,
                ),
                ft.Icon(ui.icon("CHEVRON_RIGHT"), color=theme.MUTED),
            ],
            spacing=12,
        ),
        padding=12,
        on_click=on_click,
    )


class ArticlesScreen(Screen):
    """Корневая вкладка «Статьи». С as_page=True открывается обычным экраном с кнопкой «назад»."""

    title = "Полезные статьи"
    refresh_on_return = False

    def __init__(self, app, as_page: bool = False):
        self.category: str | None = None
        if not as_page:
            self.tab_index = 1  # переопределяем атрибут класса только у этого экземпляра
        super().__init__(app)

    def body(self):
        app = self.app
        articles = app.api.get("/articles", params={"category": self.category} if self.category else None)
        controls: list[ft.Control] = []
        if self.tab_index is not None:
            controls.append(ui.title("Полезные статьи", 24))
        chips = [ui.chip("Все", self.category is None, lambda e: self.set_category(None))]
        for key in CATEGORIES:
            chips.append(
                ui.chip(theme.CATEGORY_TITLES[key], self.category == key, lambda e, k=key: self.set_category(k))
            )
        controls.append(ft.Row(chips, scroll=ft.ScrollMode.AUTO, spacing=8))
        if not articles:
            controls.append(ui.empty_state("В этой теме пока нет статей", "📚"))
        for article in articles:
            controls.append(article_card(article, lambda e, a=article: app.push(ArticleScreen(app, a["id"]))))
        controls.append(ui.spacer(8))
        return controls

    def set_category(self, key: str | None) -> None:
        self.category = key
        self.refresh()


class ArticleScreen(Screen):
    title = "Статья"
    refresh_on_return = False

    def __init__(self, app, article_id: int):
        self.article_id = article_id
        super().__init__(app)

    def body(self):
        app = self.app
        article = app.api.get(f"/articles/{self.article_id}")
        bg, fg = category_colors(article["category"])
        icon_name = theme.CATEGORY_ICONS.get(article["category"], "ARTICLE")

        controls: list[ft.Control] = [
            ft.Container(
                bgcolor=bg,
                border_radius=24,
                height=120,
                alignment=ft.alignment.center,
                content=ft.Icon(ui.icon(icon_name), color=fg, size=56),
            ),
            ui.title(article["title"], 24),
            ui.muted(f"{theme.CATEGORY_TITLES.get(article['category'], '')} · {article['reading_minutes']} мин чтения", 12),
            ft.Markdown(
                article["body_md"],
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                on_tap_link=lambda e: app.open_url(e.data),
            ),
        ]
        template = article.get("template")
        if template:
            from screens.create_habit import CreateDetailsScreen

            controls.append(
                ui.primary_button("Начать формирование привычки", lambda e: app.push(CreateDetailsScreen(app, template)))
            )
        elif article["category"] == "relapse":
            from screens.sos import SosScreen

            controls.append(ui.primary_button("Открыть SOS-бота", lambda e: app.push(SosScreen(app))))
        controls.append(ui.spacer(8))
        return controls
