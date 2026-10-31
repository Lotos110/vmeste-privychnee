"""Помощник Тишка (SOS): кнопочный сценарий поддержки. Сервер присылает сцену, приложение её рисует.

Сцена приходит из backend/app/content/sos.json: text, buttons, kind (chat, breathing, write, care),
mood (smile, calm), hint. Без нейросети: человек только выбирает кнопки.
"""

import logging
import threading
import time

import flet as ft

import theme
from components import common as ui
from components.habit_card import partners_of
from core import Screen

log = logging.getLogger("vmeste")

BREATH_CYCLES = 6  # вдох 4 с + выдох 6 с = 10 с, шесть раз: около минуты
BREATH_PHASES = (("Вдох", 1.18, 4), ("Выдох", 0.9, 6))  # подпись, размер Тишки, секунды


class SosScreen(Screen):
    title = "Тишка"
    refresh_on_return = False

    def __init__(self, app):
        self.state: dict | None = None  # {"scene": {...}, "disclaimer": "...", "partner_message": "..."}
        self._breath_token: object | None = None  # метка текущего упражнения: старое само останавливается
        self._breath_parts: tuple[ft.Container, ft.Text] | None = None
        super().__init__(app)

    def body(self):
        if self.state is None:
            self.state = self.app.api.get("/sos/start")
        return self.render()

    def refresh(self) -> None:
        super().refresh()
        self._after_render()

    # ---------- рисование сцены ----------

    def render(self) -> list[ft.Control]:
        scene = self.state["scene"]
        kind = scene.get("kind") or "chat"
        mood = scene.get("mood") or "smile"
        self._breath_token = None  # прежнее упражнение (если было) прекращается
        self._breath_parts = None

        controls: list[ft.Control] = []
        if kind == "breathing":
            mascot = ft.Container(
                content=ui.tishka(mood, 170),
                scale=1,
                animate_scale=ft.Animation(1000, ft.AnimationCurve.EASE_IN_OUT),
            )
            label = ui.txt("Приготовься", 18, ui.W_SEMI, theme.PRIMARY, text_align=ft.TextAlign.CENTER)
            self._breath_parts = (mascot, label)
            controls.append(ft.Row([mascot], alignment=ft.MainAxisAlignment.CENTER))
            controls.append(ft.Row([label], alignment=ft.MainAxisAlignment.CENTER))
        else:
            controls.append(ft.Row([ui.tishka(mood, 150)], alignment=ft.MainAxisAlignment.CENTER))

        controls.append(ui.card(ui.txt(scene["text"], 15), padding=18))

        if kind == "write":
            # текст остаётся только на экране: он не читается кодом, не отправляется и не сохраняется
            controls.append(ui.field(scene.get("hint") or "Что у тебя на душе?", multiline=True, max_length=1000))

        for index, button in enumerate(scene["buttons"]):
            handler = self.app.guard(lambda b=button: self.choose(b))
            controls.append(
                ui.primary_button(button["label"], handler) if index == 0 else ui.soft_button(button["label"], handler)
            )
        controls.append(ui.spacer(8))
        controls.append(ui.muted(self.state["disclaimer"], 12, text_align=ft.TextAlign.CENTER))
        return controls

    def show_scene(self) -> None:
        self.content.controls = self.render()
        self.app.page.update()
        self._after_render()

    def _after_render(self) -> None:
        if self._breath_parts:
            self._start_breathing(*self._breath_parts)

    # ---------- выбор кнопки ----------

    def choose(self, button: dict) -> None:
        action = button.get("action")
        if action == "home":
            return self.app.open_tab(0)
        if action == "partner":
            return self.contact_partner()
        self.state = self.app.api.post(
            "/sos/next", {"scene_id": self.state["scene"]["id"], "button_id": button["id"]}
        )
        self.show_scene()

    # ---------- минута дыхания ----------

    def _start_breathing(self, mascot: ft.Container, label: ft.Text) -> None:
        page = self.app.page
        token = self._breath_token = object()

        def alive() -> bool:
            return self._breath_token is token and bool(page.views) and page.views[-1] is self.view

        def loop() -> None:
            try:
                for _ in range(BREATH_CYCLES):
                    for text, scale, seconds in BREATH_PHASES:
                        if not alive():
                            return
                        label.value = text
                        mascot.animate_scale = ft.Animation(seconds * 1000, ft.AnimationCurve.EASE_IN_OUT)
                        mascot.scale = scale
                        page.update()
                        time.sleep(seconds)
                if alive():
                    label.value = "Можно остановиться"
                    mascot.animate_scale = ft.Animation(1000, ft.AnimationCurve.EASE_IN_OUT)
                    mascot.scale = 1
                    page.update()
            except Exception:
                log.info("Упражнение на дыхание остановлено", exc_info=True)

        threading.Thread(target=loop, daemon=True).start()

    # ---------- «Написать напарнику» ----------

    def contact_partner(self) -> None:
        habits = [h for h in self.app.api.get("/habits") if partners_of(h)]
        if not habits:
            self.app.toast("У тебя пока нет напарника по привычке. Друга можно добавить в профиле, в разделе «Друзья».")
            return
        if len(habits) == 1:
            return self.confirm_send(habits[0])
        # несколько привычек с напарниками: даём выбрать, кому написать
        self._breath_token = None
        controls: list[ft.Control] = [
            ft.Row([ui.tishka("smile", 120)], alignment=ft.MainAxisAlignment.CENTER),
            ui.card(ui.txt("Кому написать? Выбери привычку, с напарником по которой хочешь связаться.", 15), padding=18),
        ]
        for habit in habits:
            names = ", ".join(p["name"] for p in partners_of(habit))
            controls.append(ui.soft_button(f"{habit['title']}: {names}", lambda e, h=habit: self.confirm_send(h)))
        controls.append(ui.outline_button("Назад", lambda e: self.show_scene()))
        self.content.controls = controls
        self.app.page.update()

    def confirm_send(self, habit: dict) -> None:
        message = self.state.get("partner_message") or "Мне сегодня непросто. Поддержи меня, пожалуйста."
        names = ", ".join(p["name"] for p in partners_of(habit))

        def send():
            for partner in partners_of(habit):
                self.app.api.post(
                    f"/habits/{habit['id']}/nudges", {"to_user_id": partner["user_id"], "text": message}
                )
            self.app.toast("Отправлено. Ты не один(а).")

        self.app.dialog(
            "Написать напарнику?",
            ft.Text(f"{names} получит сообщение: «{message}»"),
            [("Отмена", None), ("Отправить", send)],
        )
