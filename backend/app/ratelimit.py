"""Простое ограничение частоты запросов в памяти процесса.

Достаточно для MVP с одним процессом uvicorn. При нескольких воркерах счётчики не
общие: тогда переносим их в Redis (план v2).
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_ALL: list["RateLimiter"] = []


class RateLimiter:
    def __init__(self, calls: int, period_seconds: int, message: str = "Слишком много попыток"):
        self.calls = calls
        self.period = period_seconds
        self.message = message
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        _ALL.append(self)

    def hit(self, key: str) -> None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.period:
            hits.popleft()
        if len(hits) >= self.calls:
            retry_after = max(1, int(self.period - (now - hits[0])))
            raise HTTPException(
                status_code=429,
                detail=f"{self.message}. Попробуйте через {retry_after} сек.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)

    def by_ip(self, scope: str):
        """Зависимость FastAPI: ограничение по IP-адресу клиента."""

        def dependency(request: Request) -> None:
            ip = request.client.host if request.client else "unknown"
            self.hit(f"{scope}:{ip}")

        return dependency

    def reset(self) -> None:
        self._hits.clear()


def reset_all() -> None:
    for limiter in _ALL:
        limiter.reset()


login_limiter = RateLimiter(10, 300, "Слишком много попыток входа")
register_limiter = RateLimiter(10, 3600, "Слишком много регистраций")
code_limiter = RateLimiter(20, 600, "Слишком много запросов по коду")
reset_limiter = RateLimiter(10, 900, "Слишком много попыток восстановления")
reset_email_limiter = RateLimiter(8, 3600, "Слишком много попыток восстановления для этого адреса")
recovery_code_limiter = RateLimiter(10, 900, "Слишком много запросов нового кода")
