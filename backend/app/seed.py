"""Стартовое наполнение: 9 шаблонов привычек и несколько статей. Запуск безопасно повторять."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.articles import ARTICLES
from app.models import Article, HabitTemplate
from app.services import timeutil

log = logging.getLogger(__name__)

ALL = [0, 1, 2, 3, 4, 5, 6]

# (название, иконка Material, категория, цель по умолчанию, дни недели, время)
TEMPLATES = [
    ("Сон", "BEDTIME", "sleep", "Ложиться вовремя", ALL, "22:30"),
    ("Завтрак", "BREAKFAST_DINING", "nutrition", "Завтракать каждый день", ALL, "08:00"),
    ("Обед", "RESTAURANT", "nutrition", "Обедать вовремя", ALL, "13:00"),
    ("Вода", "WATER_DROP", "water", "2 литра воды в день", ALL, "10:00"),
    ("Спорт", "FITNESS_CENTER", "sport", "3 тренировки в неделю", [0, 2, 4], "18:00"),
    ("Чтение", "MENU_BOOK", "productivity", "20 страниц в день", ALL, "21:00"),
    ("Прогулка", "DIRECTIONS_WALK", "sport", "30 минут на свежем воздухе", ALL, "19:00"),
    ("Медитация", "SELF_IMPROVEMENT", "mental", "10 минут тишины", ALL, "07:30"),
    ("Отказ от вредного", "SMOKE_FREE", "health", "День без вредной привычки", ALL, None),
]


def seed_content(db: Session) -> None:
    for position, (title, icon, category, goal, schedule, at) in enumerate(TEMPLATES):
        template = db.scalar(select(HabitTemplate).where(HabitTemplate.title == title))
        if template is None:
            db.add(
                HabitTemplate(
                    title=title,
                    icon=icon,
                    category=category,
                    default_goal=goal,
                    default_schedule=list(schedule),
                    default_time=at,
                    position=position,
                )
            )
    db.flush()

    templates = {t.title: t.id for t in db.scalars(select(HabitTemplate))}
    for item in ARTICLES:
        exists = db.scalar(select(Article.id).where(Article.title == item["title"]))
        if exists is not None:
            continue
        db.add(
            Article(
                title=item["title"],
                category=item["category"],
                summary=item["summary"],
                body_md=item["body_md"],
                habit_template_id=templates.get(item["template"]) if item["template"] else None,
                published_at=timeutil.utcnow(),
            )
        )
    db.commit()
    log.info("Стартовые шаблоны и статьи проверены")
