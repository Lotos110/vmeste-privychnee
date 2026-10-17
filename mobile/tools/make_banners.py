"""Рисует фоны баннеров главного экрана в assets/images/banners (без текста).

Запуск (нужны Pillow и numpy):  python tools/make_banners.py
Текст и кнопки накладываются в приложении, поэтому любую картинку можно заменить своей
(PNG или WebP, примерно 720×360, важное — справа, слева остаётся место под надпись).
Имена файлов задаются в screens/home.py (список BANNERS).
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "assets" / "images" / "banners"
LOGO = Path(__file__).resolve().parent.parent / "assets" / "images" / "logo_mark.png"
W, H, SS = 720, 360, 2  # размер в пикселях и коэффициент сглаживания


def rgb(value: str):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def background(left: str, right: str) -> Image.Image:
    t = np.linspace(0, 1, W * SS)[None, :, None] * 0.85 + np.linspace(0, 1, H * SS)[:, None, None] * 0.15
    arr = np.array(rgb(left)) * (1 - t) + np.array(rgb(right)) * t
    return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")


class Art:
    def __init__(self, left: str, right: str):
        self.img = background(left, right)

    def layer(self, draw_fn, blur: float = 0):
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(layer))
        if blur:
            layer = layer.filter(ImageFilter.GaussianBlur(blur * SS))
        self.img.alpha_composite(layer)

    def circle(self, cx, cy, r, color, alpha=255, blur=0):
        c = rgb(color) + (alpha,)
        self.layer(lambda d: d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=c), blur)

    def rrect(self, x0, y0, x1, y1, radius, color, alpha=255, outline=None, width=0):
        c = rgb(color) + (alpha,)
        o = rgb(outline) + (255,) if outline else None
        self.layer(
            lambda d: d.rounded_rectangle(
                [x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius * SS, fill=c, outline=o, width=int(width * SS)
            )
        )

    def line(self, points, width, color, alpha=255):
        c = rgb(color) + (alpha,)

        def draw(d):
            px = [(x * SS, y * SS) for x, y in points]
            d.line(px, fill=c, width=int(width * SS), joint="curve")
            r = width * SS / 2
            for x, y in px:
                d.ellipse([x - r, y - r, x + r, y + r], fill=c)

        self.layer(draw)

    def polygon(self, points, color, alpha=255):
        c = rgb(color) + (alpha,)
        self.layer(lambda d: d.polygon([(x * SS, y * SS) for x, y in points], fill=c))

    def paste(self, image: Image.Image, cx, cy, height):
        scale = height * SS / image.height
        img = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
        self.img.alpha_composite(img, (round(cx * SS - img.width / 2), round(cy * SS - img.height / 2)))

    def save(self, name: str):
        out = self.img.convert("RGB").resize((W, H), Image.LANCZOS)
        out.save(OUT / name, optimize=True)


def decor(art: Art, tone: str = "#FFFFFF"):
    """Мягкие круги на фоне: общий приём для всех баннеров."""
    art.circle(640, 60, 150, tone, 38)
    art.circle(560, 330, 120, tone, 30)
    art.circle(300, 20, 70, tone, 22)


def sos(path="sos.png"):
    art = Art("#5B4BDB", "#9B8CFA")
    decor(art)
    art.rrect(470, 80, 680, 230, 40, "#FFFFFF", 245)  # облачко сообщения
    art.polygon([(520, 224), (500, 275), (570, 226)], "#FFFFFF", 245)
    art.rrect(500, 112, 640, 128, 8, "#C9C3F7")
    art.rrect(500, 142, 610, 158, 8, "#E1DEFB")
    # сердечко в облачке
    art.circle(626, 190, 15, "#FF6F91")
    art.circle(654, 190, 15, "#FF6F91")
    art.polygon([(613, 197), (667, 197), (640, 226)], "#FF6F91")
    art.circle(440, 290, 22, "#FFFFFF", 70)
    art.circle(690, 300, 14, "#FFFFFF", 90)
    art.save(path)


def habit(path="habit.png"):
    art = Art("#23966A", "#7DDDAA")
    decor(art)
    art.circle(580, 180, 112, "#FFFFFF", 70)
    art.circle(580, 180, 84, "#FFFFFF", 235)
    # росток
    art.line([(580, 232), (580, 170)], 12, "#2FA36A")
    art.polygon([(580, 178), (540, 168), (524, 130), (568, 138)], "#43BF85")
    art.polygon([(582, 160), (622, 150), (638, 108), (594, 118)], "#6FD6A0")
    art.circle(580, 232, 8, "#2FA36A")
    # галочка-бейдж
    art.circle(655, 105, 28, "#FFFFFF")
    art.line([(642, 105), (652, 115), (670, 94)], 8, "#3CB878")
    art.save(path)


def friends(path="friends.png"):
    art = Art("#F2711F", "#FFBE7A")
    decor(art)
    art.circle(580, 190, 130, "#FFFFFF", 60)
    if LOGO.exists():
        art.paste(Image.open(LOGO).convert("RGBA"), 580, 188, 190)
    art.circle(470, 90, 12, "#FFFFFF", 150)
    art.circle(690, 280, 18, "#FFFFFF", 110)
    art.save(path)


def article(path="article.png"):
    art = Art("#1F76DB", "#79BDFF")
    decor(art)
    art.rrect(500, 70, 660, 290, 22, "#FFFFFF", 245)  # лист статьи
    art.rrect(522, 98, 600, 114, 8, "#2E90FA")
    for i, width in enumerate((120, 126, 96, 120)):
        art.rrect(522, 136 + i * 28, 522 + width, 148 + i * 28, 6, "#D5E7FB")
    art.polygon([(626, 70), (650, 70), (650, 118), (638, 106), (626, 118)], "#FF8A3D")  # закладка
    art.circle(470, 270, 20, "#FFFFFF", 80)
    art.save(path)


def soon(path="soon.png"):
    art = Art("#6F7594", "#B9BDD6")
    decor(art)
    # лупа
    art.line([(630, 220), (660, 252)], 16, "#FFFFFF")
    art.circle(574, 164, 58, "#FFFFFF", 255)
    art.circle(574, 164, 42, "#9CA2C4", 255)
    art.circle(574, 150, 13, "#FFFFFF", 235)  # голова человечка в лупе
    art.rrect(550, 168, 598, 202, 16, "#FFFFFF", 235)
    art.save(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (sos, habit, friends, article, soon):
        fn()
    print("готово:", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
