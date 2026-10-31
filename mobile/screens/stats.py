"""Моя статистика: серии, график выполнения, статьи и помощник Тишка."""

import flet as ft

import theme
from components import common as ui
from core import Screen

PERIODS = ["week", "month", "all"]
PERIOD_LABELS = ["Неделя", "Месяц", "Все время"]
CHART_HEIGHT = 110


def bar_chart(points: list[dict]) -> ft.Row:
    count = len(points)
    bar_width = 22 if count <= 7 else (14 if count <= 12 else 6)
    columns = []
    for index, point in enumerate(points):
        percent = point["percent"]
        if percent is None:
            height, color = 4, theme.BORDER
        else:
            height = max(4, int(CHART_HEIGHT * percent / 100))
            color = theme.GREEN if percent >= 100 else theme.GREEN_LIGHT
        show_value = count <= 12
        show_label = count <= 12 or index % 5 == 0 or index == count - 1
        columns.append(
            ft.Column(
                [
                    ui.muted(f"{percent}%" if (show_value and percent is not None) else " ", 10),
                    ft.Container(width=bar_width, height=height, bgcolor=color, border_radius=bar_width / 2),
                    ui.muted(point["label"] if show_label else " ", 11),
                ],
                expand=1,
                spacing=4,
                alignment=ft.MainAxisAlignment.END,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    return ft.Row(
        columns,
        height=CHART_HEIGHT + 50,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )


class StatsScreen(Screen):
    title = "Моя статистика"

    def __init__(self, app):
        self.period = 0
        super().__init__(app)

    def body(self):
        app, api = self.app, self.app.api
        stats = api.get("/stats", params={"period": PERIODS[self.period]})
        try:
            articles = api.get("/articles")[:2]
        except Exception:  # статьи не критичны для экрана статистики
            articles = []

        from screens.articles import ArticleScreen, ArticlesScreen, article_card
        from screens.sos import SosScreen

        banner = ft.Container(
            border_radius=24,
            padding=20,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=theme.PRIMARY_GRADIENT
            ),
            content=ft.Row(
                [
                    ft.Icon(ui.icon("LOCAL_FIRE_DEPARTMENT"), color=theme.ORANGE, size=44),
                    ft.Column(
                        [
                            ui.txt(ui.days_text(stats["current_streak"]), 22, ui.W_BOLD, theme.WHITE),
                            ui.txt("Текущая серия", 12, color="#D9D3FF"),
                        ],
                        spacing=0,
                        expand=1,
                    ),
                    ft.Container(width=1, height=40, bgcolor="#55FFFFFF"),
                    ft.Column(
                        [
                            ui.txt(ui.days_text(stats["best_streak"]), 18, ui.W_BOLD, theme.WHITE),
                            ui.txt("Рекордная серия", 12, color="#D9D3FF"),
                        ],
                        spacing=0,
                        expand=1,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        summary = (
            f"Выполнено {stats['total_done']} · {stats['completion_percent']}% от плана"
            if stats["points"]
            else "Данных пока нет"
        )
        controls = [
            banner,
            ui.segmented(PERIOD_LABELS, self.period, self.set_period),
            ui.card(
                ft.Column(
                    [ui.txt("Выполнение привычек", 18, ui.W_BOLD), ui.muted(summary, 12), bar_chart(stats["points"])],
                    spacing=8,
                )
            ),
        ]
        if articles:
            controls.append(ui.section_header("Полезные статьи", "Все", lambda e: app.push(ArticlesScreen(app, as_page=True))))
            for article in articles:
                controls.append(article_card(app, article, lambda e, a=article: app.push(ArticleScreen(app, a["id"]))))
        controls.append(
            ui.card(
                ft.Row(
                    [
                        ui.tishka("smile", 84),
                        ft.Column(
                            [
                                ui.txt("Тишка рядом", 16, ui.W_BOLD),
                                ui.muted("Тяжело или хочется сорваться? Можно подышать, написать, что на душе, и вернуться.", 12),
                                ui.small_button("Заглянуть", lambda e: app.push(SosScreen(app))),
                            ],
                            spacing=6,
                            expand=True,
                        ),
                    ],
                    spacing=12,
                ),
                bgcolor=theme.PRIMARY_SOFT,
            )
        )
        controls.append(ui.spacer(8))
        return controls

    def set_period(self, index: int) -> None:
        self.period = index
        self.refresh()
