"""Полезные статьи: список с фильтром по темам и страница статьи."""

import flet as ft

import theme
from api import ApiError
from components import common as ui
from components.habit_card import category_colors
from core import Screen

CATEGORIES = ["sleep", "nutrition", "sport", "water", "productivity", "mental", "relapse"]


def pill(icon_name: str | None, text: str, bg: str, fg: str) -> ft.Container:
    """Небольшая плашка: «Сон», «⏱ 7 мин»."""
    parts: list[ft.Control] = []
    if icon_name:
        parts.append(ft.Icon(ui.icon(icon_name), color=fg, size=14))
    parts.append(ui.txt(text, 12, ui.W_SEMI, fg))
    return ft.Container(
        content=ft.Row(parts, spacing=4, tight=True),
        bgcolor=bg,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
    )


def minutes_text(article: dict) -> str:
    return f"{article['reading_minutes']} мин"


def article_thumb(app, article: dict, size: int = 64) -> ft.Container:
    """Обложка-миниатюра: своя картинка, а если её нет — цветной круг с иконкой темы."""
    bg, fg = category_colors(article["category"])
    cover = app.api.media_url(article.get("cover_url"))
    if cover:
        return ft.Container(
            width=size,
            height=size,
            border_radius=18,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            bgcolor=bg,
            content=ft.Image(src=cover, width=size, height=size, fit=ft.ImageFit.COVER),
        )
    return ui.circle_icon(theme.CATEGORY_ICONS.get(article["category"], "ARTICLE"), bg, fg, size)


def article_card(app, article: dict, on_click) -> ft.Container:
    bg, fg = category_colors(article["category"])
    return ui.card(
        ft.Row(
            [
                article_thumb(app, article),
                ft.Column(
                    [
                        ui.txt(article["title"], 15, ui.W_BOLD, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ui.muted(article["summary"], 12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row(
                            [
                                pill(None, theme.CATEGORY_TITLES.get(article["category"], ""), bg, fg),
                                pill("SCHEDULE", minutes_text(article), theme.BG, theme.MUTED),
                            ],
                            spacing=6,
                        ),
                    ],
                    spacing=5,
                    expand=True,
                ),
                ft.Icon(ui.icon("CHEVRON_RIGHT"), color=theme.MUTED),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
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
            controls.append(article_card(app, article, lambda e, a=article: app.push(ArticleScreen(app, a["id"]))))
        controls.append(ui.spacer(8))
        return controls

    def set_category(self, key: str | None) -> None:
        self.category = key
        self.refresh()


def markdown_style() -> ft.MarkdownStyleSheet:
    """Оформление текста статьи: Comfortaa в заголовках, Nunito в тексте, цитаты как выноски."""

    def style(size, family, color=theme.TEXT, height=1.5):
        return ft.TextStyle(size=size, font_family=family, color=color, height=height)

    return ft.MarkdownStyleSheet(
        p_text_style=style(15, theme.FONT_BODY),
        h1_text_style=style(24, theme.FONT_HEAD_BOLD, height=1.3),
        h2_text_style=style(20, theme.FONT_HEAD_BOLD, height=1.3),
        h3_text_style=style(17, theme.FONT_HEAD_BOLD, height=1.3),
        strong_text_style=style(15, theme.FONT_BODY_BOLD),
        a_text_style=style(15, theme.FONT_BODY_BOLD, theme.PRIMARY),
        list_bullet_text_style=style(15, theme.FONT_BODY),
        blockquote_text_style=style(14, theme.FONT_BODY),
        blockquote_padding=ft.padding.all(14),
        blockquote_decoration=ft.BoxDecoration(bgcolor=theme.PRIMARY_SOFT, border_radius=ft.border_radius.all(14)),
        block_spacing=12,
    )


class ArticleScreen(Screen):
    title = "Статья"
    refresh_on_return = False

    def __init__(self, app, article_id: int):
        self.article_id = article_id
        super().__init__(app)

    def _cover(self, article: dict) -> ft.Container:
        bg, fg = category_colors(article["category"])
        cover = self.app.api.media_url(article.get("cover_url"))
        if cover:
            return ft.Container(
                height=190,
                border_radius=24,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                bgcolor=bg,
                content=ft.Image(src=cover, width=float("inf"), height=190, fit=ft.ImageFit.COVER),
            )
        icon_name = theme.CATEGORY_ICONS.get(article["category"], "ARTICLE")
        return ft.Container(
            height=150,
            border_radius=24,
            bgcolor=bg,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Stack(
                [
                    ft.Container(width=170, height=170, border_radius=85, bgcolor=theme.WHITE, opacity=0.35,
                                 right=-30, top=-50),
                    ft.Container(width=90, height=90, border_radius=45, bgcolor=theme.WHITE, opacity=0.35,
                                 left=-20, bottom=-30),
                    ft.Container(alignment=ft.alignment.center, expand=True,
                                 content=ft.Icon(ui.icon(icon_name), color=fg, size=64)),
                ],
            ),
        )

    def _body_markdown(self, article: dict) -> str:
        """Картинки в тексте можно писать как ![подпись](/media/файл.png): адрес дополняется адресом сервера."""
        base = self.app.api.base_url.rstrip("/")
        return article["body_md"].replace("](/media/", f"]({base}/media/")

    def _related(self, article: dict) -> list[ft.Control]:
        app = self.app
        try:
            same = app.api.get("/articles", params={"category": article["category"]})
        except ApiError:
            return []
        others = [a for a in same if a["id"] != article["id"]][:2]
        if not others:
            return []
        controls: list[ft.Control] = [ui.txt("Читайте также", 18, ui.W_BOLD)]
        for other in others:
            controls.append(article_card(app, other, lambda e, a=other: app.push(ArticleScreen(app, a["id"]))))
        return controls

    def body(self):
        app = self.app
        article = app.api.get(f"/articles/{self.article_id}")
        bg, fg = category_colors(article["category"])

        controls: list[ft.Control] = [
            self._cover(article),
            ft.Row(
                [
                    pill(None, theme.CATEGORY_TITLES.get(article["category"], ""), bg, fg),
                    pill("SCHEDULE", f"{minutes_text(article)} чтения", theme.CARD, theme.MUTED),
                ],
                spacing=8,
            ),
            ui.title(article["title"], 24),
        ]
        if article.get("summary"):
            controls.append(ui.txt(article["summary"], 15, color=theme.MUTED))
        controls.append(
            ft.Markdown(
                self._body_markdown(article),
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                md_style_sheet=markdown_style(),
                on_tap_link=lambda e: app.open_url(e.data),
            )
        )
        template = article.get("template")
        if template:
            from screens.create_habit import CreateDetailsScreen

            controls.append(
                ui.primary_button("Начать формирование привычки", lambda e: app.push(CreateDetailsScreen(app, template)))
            )
        elif article["category"] == "relapse":
            from screens.sos import SosScreen

            controls.append(ui.primary_button("Открыть SOS-бота", lambda e: app.push(SosScreen(app))))
        controls += self._related(article)
        controls.append(ui.spacer(8))
        return controls
