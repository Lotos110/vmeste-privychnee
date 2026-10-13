FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app
RUN pip install .

COPY alembic.ini ./
COPY alembic ./alembic

RUN useradd --create-home appuser && mkdir -p /srv/media && chown -R appuser /srv/media
USER appuser

EXPOSE 8000

# Миграции применяются при каждом старте; один процесс uvicorn (планировщик напоминаний внутри).
# --forwarded-allow-ips='*' безопасно, пока порт 8000 доступен только через Caddy (см. docker-compose.yml).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
