"""Превращает рисунки из tools/art/*.svg в PNG для приложения (assets/images/illustrations).

Запуск (нужны Python-пакет playwright и браузер Chromium):  python tools/render_art.py [имя ...]
Без имён рисует все. Размеры в пикселях заданы в SIZES; рисунки с прозрачным фоном
сохраняются с прозрачностью. Чтобы поменять рисунок, правьте SVG и запустите скрипт снова.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SRC = HERE / "art"
OUT = HERE.parent / "assets" / "images" / "illustrations"

# имя файла без .svg -> (ширина, высота) готового PNG
SIZES = {
    "welcome": (1080, 540),
    "sprout": (480, 480),
}


def main(names: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    names = names or list(SIZES)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name in names:
            w, h = SIZES[name]
            svg = (SRC / f"{name}.svg").read_text(encoding="utf-8")
            page = browser.new_page(viewport={"width": w, "height": h})
            page.set_content(
                "<html><body style='margin:0;background:transparent'>"
                f"<div style='width:{w}px;height:{h}px'>"
                + svg.replace("<svg ", f"<svg style='width:{w}px;height:{h}px;display:block' ", 1)
                + "</div></body></html>"
            )
            page.screenshot(path=str(OUT / f"{name}.png"), omit_background=True, clip={"x": 0, "y": 0, "width": w, "height": h})
            page.close()
            print("готово:", name)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
