"""SOS-бот: кнопочный сценарий поддержки. Сервер присылает сцену, клиент показывает кнопки."""

import flet as ft

import theme
from components import common as ui
from core import Screen


class SosScreen(Screen):
    title = "SOS-бот"
    refresh_on_return = False

    def __init__(self, app):
        self.state: dict | None = None  # {"scene": {...}, "disclaimer": "..."}
        super().__init__(app)

    def body(self):
        if self.state is None:
            self.state = self.app.api.get("/sos/start")
        return self.render()

    def render(self) -> list[ft.Control]:
        scene = self.state["scene"]
        controls: list[ft.Control] = [
            ft.Row(
                [
                    ft.Container(
                        width=48,
                        height=48,
                        border_radius=24,
                        bgcolor=theme.PRIMARY_SOFT,
                        alignment=ft.alignment.center,
                        content=ft.Text("🤖", size=26),
                    ),
                    ft.Container(
                        expand=True,
                        bgcolor=theme.CARD,
                        border_radius=ft.border_radius.only(top_right=20, bottom_left=20, bottom_right=20),
                        padding=16,
                        content=ft.Text(scene["text"], size=15, color=theme.TEXT),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
                spacing=10,
            )
        ]
        for index, button in enumerate(scene["buttons"]):
            handler = self.app.guard(lambda b=button: self.choose(b))
            controls.append(
                ui.primary_button(button["label"], handler) if index == 0 else ui.soft_button(button["label"], handler)
            )
        controls.append(ui.spacer(8))
        controls.append(ui.muted(self.state["disclaimer"], 12, text_align=ft.TextAlign.CENTER))
        return controls

    def choose(self, button: dict) -> None:
        if button.get("action") == "home":
            return self.app.open_tab(0)
        self.state = self.app.api.post(
            "/sos/next", {"scene_id": self.state["scene"]["id"], "button_id": button["id"]}
        )
        self.content.controls = self.render()
        self.app.page.update()
