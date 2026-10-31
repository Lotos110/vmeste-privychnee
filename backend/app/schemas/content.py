from datetime import datetime

from pydantic import BaseModel

from app.schemas.habit import TemplateOut


class ArticleListItem(BaseModel):
    id: int
    title: str
    category: str
    summary: str
    cover_url: str | None = None
    reading_minutes: int
    published_at: datetime | None = None


class ArticleOut(ArticleListItem):
    body_md: str
    template: TemplateOut | None = None  # для кнопки «Начать формирование привычки»


class SosButton(BaseModel):
    id: str
    label: str
    next: str | None = None
    action: str | None = None  # "home" — к привычкам, "partner" — написать напарнику


class SosScene(BaseModel):
    id: str
    text: str
    buttons: list[SosButton]
    kind: str = "chat"  # chat | breathing | write | care: как приложение рисует сцену
    mood: str = "smile"  # smile | calm: настроение Тишки
    hint: str | None = None  # подсказка в поле ввода (kind write)


class SosOut(BaseModel):
    scene: SosScene
    disclaimer: str
    partner_message: str = "Мне сегодня непросто. Поддержи меня, пожалуйста."


class SosNextIn(BaseModel):
    scene_id: str
    button_id: str
