"""Админка SQLAdmin на /admin: статьи, шаблоны привычек, блокировка пользователей, модерация ленты.

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

        from app.models import Article, HabitTemplate, PartnerPost, PostResponse, Report, User

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

        class PostAdmin(ModelView, model=PartnerPost):
            name, name_plural = "Объявление", "Объявления: поиск напарника"
            icon = "fa-solid fa-people-arrows"
            can_create = False
            column_list = [
                PartnerPost.id, PartnerPost.topic, PartnerPost.text, PartnerPost.status,
                PartnerPost.age_group, PartnerPost.created_at,
            ]
            column_searchable_list = [PartnerPost.text, PartnerPost.topic]
            column_default_sort = [(PartnerPost.id, True)]
            # модератор меняет только статус: open (показать), hidden (скрыть), closed (закрыть)
            form_columns = [PartnerPost.status]

        class ResponseAdmin(ModelView, model=PostResponse):
            name, name_plural = "Отклик", "Отклики"
            icon = "fa-solid fa-comments"
            can_create = False
            column_list = [PostResponse.id, PostResponse.post_id, PostResponse.text, PostResponse.status]
            column_default_sort = [(PostResponse.id, True)]
            form_columns = [PostResponse.status]  # pending, accepted, declined, hidden

        class ReportAdmin(ModelView, model=Report):
            name, name_plural = "Жалоба", "Жалобы"
            icon = "fa-solid fa-flag"
            can_create = False
            column_list = [
                Report.id, Report.target_type, Report.target_id, Report.reason, Report.status, Report.created_at,
            ]
            column_default_sort = [(Report.id, True)]
            form_columns = [Report.status]  # new или done: пометить разобранной

        admin = Admin(
            app,
            engine,
            authentication_backend=AdminAuth(secret_key=settings.secret_key),
            title="Вместе привычнее",
        )
        admin.add_view(ArticleAdmin)
        admin.add_view(TemplateAdmin)
        admin.add_view(UserAdmin)
        admin.add_view(ReportAdmin)
        admin.add_view(PostAdmin)
        admin.add_view(ResponseAdmin)
        log.info("Админка доступна на /admin")
    except Exception:
        log.exception("Не удалось подключить админку, продолжаем без неё")
