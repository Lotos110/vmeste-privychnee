"""Импорт всех моделей в одном месте, чтобы Alembic и create_all видели все таблицы."""

from app.models.community import PartnerPost, PostResponse, Report, UserBlock
from app.models.habit import (
    Article,
    CheckIn,
    Habit,
    HabitMember,
    HabitTemplate,
    Nudge,
)
from app.models.user import Friendship, User

__all__ = [
    "Article",
    "CheckIn",
    "Friendship",
    "Habit",
    "HabitMember",
    "HabitTemplate",
    "Nudge",
    "PartnerPost",
    "PostResponse",
    "Report",
    "User",
    "UserBlock",
]
