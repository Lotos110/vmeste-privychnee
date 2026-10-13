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
    action: str | None = None  # "home" — вернуться на главный экран


class SosScene(BaseModel):
    id: str
    text: str
    buttons: list[SosButton]


class SosOut(BaseModel):
    scene: SosScene
    disclaimer: str


class SosNextIn(BaseModel):
    scene_id: str
    button_id: str
