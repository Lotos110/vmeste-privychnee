"""Напоминания и сообщения от напарников."""

from datetime import datetime

import flet as ft

import theme
from components import common as ui
from core import Screen

KIND_ICONS = {
    "partner": ("FAVORITE", theme.PRIMARY_SOFT, theme.PRIMARY),
    "reminder": ("ALARM", theme.BLUE_SOFT, theme.BLUE),
    "risk": ("LOCAL_FIRE_DEPARTMENT", theme.ORANGE_SOFT, theme.ORANGE),
    "response": ("CHAT_BUBBLE_OUTLINE", theme.GREEN_SOFT, theme.GREEN),  # отклик на объявление в «Поиске»
    "accepted": ("GROUP_ADD", theme.GREEN_SOFT, theme.GREEN),  # автор принял ваш отклик
}


def format_moment(iso: str) -> str:
    try:
        moment = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return ""
    return moment.strftime("%d.%m %H:%M")


class NotificationsScreen(Screen):
    title = "Напоминания"

    def _opener(self, nudge: dict):
        """Отклик на объявление открывает «Мои объявления», принятый отклик ведёт к друзьям."""
        app = self.app
        if nudge["kind"] == "response":
            from screens.feed import MyPostsScreen

            return lambda e: app.push(MyPostsScreen(app))
        if nudge["kind"] == "accepted":
            from screens.friends import FriendsScreen

            return lambda e: app.push(FriendsScreen(app))
        return None

    def body(self):
        api = self.app.api
        nudges = api.get("/nudges")
        if any(not n["read"] for n in nudges):
            api.post("/nudges/read")  # показываем непрочитанные выделенными, но дальше они уже прочитаны
        if not nudges:
            return [ui.empty_state("Пока тихо. Здесь будут напоминания и поддержка от напарников.", art="bell")]

        controls: list[ft.Control] = []
        for nudge in nudges:
            icon_name, bg, fg = KIND_ICONS.get(nudge["kind"], KIND_ICONS["partner"])
            sender = nudge["sender"]["name"] if nudge.get("sender") else "Вместе привычнее"
            where = f" · «{nudge['habit_title']}»" if nudge.get("habit_title") else ""
            controls.append(
                ui.card(
                    ft.Row(
                        [
                            ui.circle_icon(icon_name, bg, fg, 40),
                            ft.Column(
                                [
                                    ui.txt(nudge["text"], 14, ui.W_SEMI if not nudge["read"] else None),
                                    ui.muted(f"{sender}{where} · {format_moment(nudge['created_at'])}", 11),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=12,
                    bgcolor=theme.CARD if nudge["read"] else theme.PRIMARY_SOFT,
                    radius=16,
                    on_click=self._opener(nudge),
                )
            )
        controls.append(ui.spacer(8))
        return controls
