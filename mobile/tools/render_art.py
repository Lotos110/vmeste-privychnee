"""Превращает рисунки из tools/art/*.svg в PNG для приложения и собирает баннеры главного экрана.

Запуск (нужны Python-пакет playwright и браузер Chromium):  python tools/render_art.py [имя ...]
Без имён рисует всё. Размеры в пикселях заданы в SIZES; рисунки с прозрачным фоном сохраняются
с прозрачностью. Чтобы поменять рисунок, правьте SVG и запустите скрипт снова.

Рисунки лежат в assets/images/illustrations, баннеры в assets/images/banners. Баннер собирается из
цветного фона и одной из иллюстраций справа (слева остаётся место под текст, его рисует приложение).
"""

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SRC = HERE / "art"
ASSETS = HERE.parent / "assets" / "images"
OUT = ASSETS / "illustrations"
BANNERS = ASSETS / "banners"

# имя файла без .svg -> (ширина, высота) готового PNG
SIZES = {
    "welcome": (1080, 540),
    "sprout": (480, 480),
    "books": (480, 480),
    "friends": (480, 480),
    "bell": (480, 480),
    "tishka_smile": (510, 420),
    "tishka_calm": (510, 420),
}

# баннер -> (цвет слева, цвет справа, иллюстрация)
BANNER_ART = {
    "article": ("#2478DD", "#7DBBFF", "books"),
    "habit": ("#27976A", "#7FD7A8", "sprout"),
    "friends": ("#F07422", "#FDBF86", "friends"),
    "sos": ("#5B4BDD", "#A395F7", "tishka_smile"),
}
BANNER_W, BANNER_H = 720, 360


def inline(name: str) -> str:
    """Содержимое SVG для вставки в другой SVG: id градиентов получают приставку, чтобы не пересекались."""
    svg = (SRC / f"{name}.svg").read_text(encoding="utf-8")
    ids = set(re.findall(r'id="([^"]+)"', svg))
    for i in ids:
        svg = svg.replace(f'id="{i}"', f'id="{name}_{i}"').replace(f"url(#{i})", f"url(#{name}_{i})")
    return svg


def banner_svg(left: str, right: str, art: str) -> str:
    size = 270
    x, y = BANNER_W - size - 36, (BANNER_H - size) // 2
    inner = re.sub(r'(<svg[^>]*?) width="\d+" height="\d+"', r"\1", inline(art), count=1)
    inner = inner.replace("<svg ", f'<svg x="{x}" y="{y}" width="{size}" height="{size}" preserveAspectRatio="xMidYMid meet" ', 1)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BANNER_W} {BANNER_H}" width="{BANNER_W}" height="{BANNER_H}">
  <defs><linearGradient id="bg" x1="0" y1="0.2" x2="1" y2="0.8"><stop offset="0" stop-color="{left}"/><stop offset="1" stop-color="{right}"/></linearGradient></defs>
  <rect width="{BANNER_W}" height="{BANNER_H}" fill="url(#bg)"/>
  <circle cx="300" cy="10" r="70" fill="#fff" opacity="0.10"/>
  <circle cx="640" cy="20" r="150" fill="#fff" opacity="0.10"/>
  <circle cx="610" cy="360" r="130" fill="#fff" opacity="0.10"/>
  <circle cx="{x + size / 2}" cy="{y + size / 2}" r="{size / 2 + 22}" fill="#fff" opacity="0.18"/>
  {inner}
</svg>"""


def shoot(browser, svg: str, w: int, h: int, path: Path) -> None:
    svg = re.sub(r"<svg ", f"<svg style='width:{w}px;height:{h}px;display:block' ", svg, count=1)
    page = browser.new_page(viewport={"width": w, "height": h})
    page.set_content(f"<html><body style='margin:0;background:transparent'>{svg}</body></html>")
    page.screenshot(path=str(path), omit_background=True, clip={"x": 0, "y": 0, "width": w, "height": h})
    page.close()
    print("готово:", path.name)


def main(names: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    BANNERS.mkdir(parents=True, exist_ok=True)
    everything = not names
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name in names or list(SIZES):
            if name in SIZES:
                w, h = SIZES[name]
                shoot(browser, (SRC / f"{name}.svg").read_text(encoding="utf-8"), w, h, OUT / f"{name}.png")
        for name, (left, right, art) in BANNER_ART.items():
            if everything or f"banner_{name}" in names:
                shoot(browser, banner_svg(left, right, art), BANNER_W, BANNER_H, BANNERS / f"{name}.png")
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
