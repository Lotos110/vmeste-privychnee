"""Проверка сценария SOS-бота (app/content/sos.json): нет битых ссылок и тупиков."""

import json
from pathlib import Path

SCRIPT = json.loads(
    (Path(__file__).resolve().parent.parent / "app" / "content" / "sos.json").read_text("utf-8")
)
SCENES = SCRIPT["scenes"]


def test_start_exists_and_disclaimer_present():
    assert SCRIPT["start"] in SCENES
    assert "112" in SCRIPT["disclaimer"]


def test_every_button_has_valid_target():
    for scene_id, scene in SCENES.items():
        assert 1 <= len(scene["buttons"]) <= 4, scene_id
        ids = [b["id"] for b in scene["buttons"]]
        assert len(ids) == len(set(ids)), f"повторяющиеся id кнопок в {scene_id}"
        for button in scene["buttons"]:
            assert bool(button.get("next")) != bool(button.get("action")), (scene_id, button["id"])
            if button.get("next"):
                assert button["next"] in SCENES, (scene_id, button["next"])


def test_all_scenes_reachable_and_can_finish():
    reachable, stack = set(), [SCRIPT["start"]]
    while stack:
        scene_id = stack.pop()
        if scene_id in reachable:
            continue
        reachable.add(scene_id)
        stack += [b["next"] for b in SCENES[scene_id]["buttons"] if b.get("next")]
    assert reachable == set(SCENES), f"недостижимые сцены: {set(SCENES) - reachable}"

    # из любой сцены можно дойти до кнопки с action (выход на главный экран)
    can_finish = {sid for sid, s in SCENES.items() if any(b.get("action") for b in s["buttons"])}
    changed = True
    while changed:
        changed = False
        for sid, scene in SCENES.items():
            if sid not in can_finish and any(b.get("next") in can_finish for b in scene["buttons"]):
                can_finish.add(sid)
                changed = True
    assert can_finish == set(SCENES)
