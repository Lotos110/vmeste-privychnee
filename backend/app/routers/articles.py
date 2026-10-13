import math

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.deps import DB
from app.models import Article, HabitTemplate
from app.schemas.content import ArticleListItem, ArticleOut
from app.schemas.habit import TemplateOut
from app.services import timeutil

router = APIRouter(prefix="/articles", tags=["articles"])

WORDS_PER_MINUTE = 180


def _list_item(article: Article) -> dict:
    words = len(article.body_md.split())
    return {
        "id": article.id,
        "title": article.title,
        "category": article.category,
        "summary": article.summary,
        "cover_url": f"/media/{article.cover_path}" if article.cover_path else None,
        "reading_minutes": max(1, math.ceil(words / WORDS_PER_MINUTE)),
        "published_at": timeutil.as_utc(article.published_at),
    }


@router.get("", response_model=list[ArticleListItem])
def list_articles(db: DB, category: str | None = Query(default=None, max_length=20)):
    query = select(Article).where(Article.published_at.is_not(None))
    if category:
        query = query.where(Article.category == category)
    articles = db.scalars(query.order_by(Article.published_at.desc(), Article.id))
    return [_list_item(a) for a in articles]


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: DB):
    article = db.get(Article, article_id)
    if article is None or article.published_at is None:
        raise HTTPException(status_code=404, detail="Статья не найдена")
    template = db.get(HabitTemplate, article.habit_template_id) if article.habit_template_id else None
    return ArticleOut(
        **_list_item(article),
        body_md=article.body_md,
        template=(
            TemplateOut(
                id=template.id,
                title=template.title,
                icon=template.icon,
                category=template.category,
                default_goal=template.default_goal,
                default_schedule=list(template.default_schedule),
                default_time=template.default_time,
            )
            if template
            else None
        ),
    )
