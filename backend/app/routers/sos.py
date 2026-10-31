"""Помощник Тишка (SOS): кнопочный сценарий из JSON, без нейросети. Предсказуем и не скажет лишнего."""

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser
from app.schemas.content import SosButton, SosNextIn, SosOut, SosScene

router = APIRouter(prefix="/sos", tags=["sos"])

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "content" / "sos.json"


@lru_cache
def load_script() -> dict:
    return json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))


def _scene(script: dict, scene_id: str) -> SosOut:
    raw = script["scenes"][scene_id]
    return SosOut(
        scene=SosScene(
            id=scene_id,
            text=raw["text"],
            buttons=[SosButton(**button) for button in raw["buttons"]],
            kind=raw.get("kind", "chat"),
            mood=raw.get("mood", "smile"),
            hint=raw.get("hint"),
        ),
        disclaimer=script["disclaimer"],
        partner_message=script.get("partner_message") or SosOut.model_fields["partner_message"].default,
    )


@router.get("/start", response_model=SosOut)
def start(user: CurrentUser):
    script = load_script()
    return _scene(script, script["start"])


@router.post("/next", response_model=SosOut)
def next_scene(data: SosNextIn, user: CurrentUser):
    script = load_script()
    scene = script["scenes"].get(data.scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Сцена не найдена")
    button = next((b for b in scene["buttons"] if b["id"] == data.button_id), None)
    if button is None or not button.get("next"):
        raise HTTPException(status_code=400, detail="Эта кнопка не ведёт к новой сцене")
    return _scene(script, button["next"])
