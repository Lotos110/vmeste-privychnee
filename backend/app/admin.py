"""Админка SQLAdmin на /admin: статьи, шаблоны привычек, блокировка пользователей.

Включается, когда задан ADMIN_PASSWORD. Если SQLAdmin не удалось подключить (например,
несовместимая версия), сервер всё равно запускается, а в журнале будет предупреждение.
"""

import hmac
import logging

from fastapi import FastAPI

from app.config import get_settings
from app.db import engine

log = logging.getLogger(__name__)


def setup_admin(app: FastAPI) -> None:
    settings = get_settings()
    if not settings.admin_password:
        log.info("Админка выключена: ADMIN_PASSWORD не задан")
        return
    try:
        from sqladmin import Admin, ModelView
        from sqladmin.authentication import AuthenticationBackend
        from starlette.requests import Request

        from app.models import Article, HabitTemplate, User

        class AdminAuth(AuthenticationBackend):
            async def login(self, request: Request) -> bool:
                form = await request.form()
                # сравниваем байты: compare_digest для str падает на не-ASCII символах
                ok_user = hmac.compare_digest(
                    str(form.get("username", "")).encode(), settings.admin_username.encode()
                )
                ok_pass = hmac.compare_digest(
                    str(form.get("password", "")).encode(), settings.admin_password.encode()
                )
                if ok_user and ok_pass:
                    request.session.update({"admin": True})
                    return True
                return False

            async def logout(self, request: Request) -> bool:
                request.session.clear()
                return True

            async def authenticate(self, request: Request) -> bool:
                return bool(request.session.get("admin"))

        class ArticleAdmin(ModelView, model=Article):
            name, name_plural = "Статья", "Статьи"
            icon = "fa-solid fa-book"
            column_list = [Article.id, Article.title, Article.category, Article.published_at]
            column_searchable_list = [Article.title]
            form_columns = [
                Article.title,
                Article.category,
                Article.summary,
                Article.body_md,
                Article.habit_template,
                Article.published_at,
            ]

        class TemplateAdmin(ModelView, model=HabitTemplate):
            name, name_plural = "Шаблон привычки", "Шаблоны привычек"
            icon = "fa-solid fa-list-check"
            column_list = [HabitTemplate.id, HabitTemplate.title, HabitTemplate.category]
            form_columns = [
                HabitTemplate.title,
                HabitTemplate.icon,
                HabitTemplate.category,
                HabitTemplate.default_goal,
                HabitTemplate.default_time,
                HabitTemplate.position,
            ]

        class UserAdmin(ModelView, model=User):
            name, name_plural = "Пользователь", "Пользователи"
            icon = "fa-solid fa-user"
            can_create = False
            can_delete = False
            column_list = [User.id, User.name, User.email, User.is_banned, User.created_at]
            column_searchable_list = [User.email, User.name]
            # в карточке пользователя не показываем хеш пароля и дату рождения
            column_details_list = [User.id, User.name, User.email, User.is_banned, User.created_at]
            form_columns = [User.is_banned]  # только блокировка; личные данные не правим

        admin = Admin(
            app,
            engine,
            authentication_backend=AdminAuth(secret_key=settings.secret_key),
            title="Вместе привычнее",
        )
        admin.add_view(ArticleAdmin)
        admin.add_view(TemplateAdmin)
        admin.add_view(UserAdmin)
        log.info("Админка доступна на /admin")
    except Exception:
        log.exception("Не удалось подключить админку, продолжаем без неё")
