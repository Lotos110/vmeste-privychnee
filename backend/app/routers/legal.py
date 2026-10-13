"""Заглушки страниц, на которые ссылаются экраны регистрации.

ВАЖНО: перед публичным запуском замените тексты на настоящие, проверенные юристом
(пользовательское соглашение, политика конфиденциальности, согласие на обработку данных).
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/legal", tags=["legal"], include_in_schema=False)

PAGE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}: Вместе привычнее</title>
<style>body{{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;
line-height:1.5;color:#1f2340}}</style></head>
<body><h1>{title}</h1>
<p><b>Черновик.</b> Здесь будет текст документа. Он должен быть подготовлен и проверен юристом
до публичного запуска приложения.</p></body></html>"""


@router.get("/terms", response_class=HTMLResponse)
def terms():
    return PAGE.format(title="Пользовательское соглашение")


@router.get("/privacy", response_class=HTMLResponse)
def privacy():
    return PAGE.format(title="Политика конфиденциальности")
