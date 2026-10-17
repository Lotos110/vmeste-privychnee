"""Рисует логотип «Вместе привычнее» (знак, иконка приложения, фавикон) в mobile/assets.

Запуск (нужны Pillow и numpy):  python tools/make_logo.py
Это временный рисованный вариант: когда будет готов авторский логотип, достаточно заменить
файлы logo_mark.png (знак на прозрачном фоне, от 256×256), icon.png (1024×1024) и favicon.png.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets"
SCALE = 3  # во сколько раз рисуем крупнее, чтобы края были гладкими
# рабочая область в «единицах» чертежа (центр знака по горизонтали: x = 627)
OX, OY, W, H = 330, 250, 600, 540
CX = 627


def bez(p0, p1, p2, p3, n=48):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3


def heart(notch, peak, wide, tip, c_np, c_pw, c_wt):
    """Сердце, симметричное относительно x=CX. Возвращает замкнутый контур (массив точек)."""

    def mirror(p):
        return (2 * CX - p[0], p[1])

    right = np.vstack(
        [
            bez(notch, c_np[0], c_np[1], peak),
            bez(peak, c_pw[0], c_pw[1], wide),
            bez(wide, c_wt[0], c_wt[1], tip),
        ]
    )
    left = np.array([mirror(p) for p in right[::-1]])
    return np.vstack([right, left])


OUTER = heart(
    (CX, 548), (818, 466), (892, 572), (CX, 758),
    ((660, 500), (740, 466)), ((868, 466), (892, 512)), ((892, 670), (775, 722)),
)
INNER = heart(
    (CX, 575), (705, 528), (775, 595), (CX, 722),
    ((650, 535), (675, 528)), ((745, 528), (775, 555)), ((775, 650), (690, 700)),
)


def to_px(points):
    pts = np.asarray(points, dtype=float)
    return [((x - OX) * SCALE, (y - OY) * SCALE) for x, y in pts]


def poly_mask(points) -> np.ndarray:
    img = Image.new("L", (W * SCALE, H * SCALE), 0)
    ImageDraw.Draw(img).polygon(to_px(points), fill=255)
    return np.asarray(img, dtype=np.float32) / 255.0


def circle_mask(cx, cy, r) -> np.ndarray:
    img = Image.new("L", (W * SCALE, H * SCALE), 0)
    (x0, y0), (x1, y1) = to_px([(cx - r, cy - r), (cx + r, cy + r)])
    ImageDraw.Draw(img).ellipse([x0, y0, x1, y1], fill=255)
    return np.asarray(img, dtype=np.float32) / 255.0


def stroke_mask(points, width) -> np.ndarray:
    """Ломаная с круглыми концами и скруглёнными стыками."""
    img = Image.new("L", (W * SCALE, H * SCALE), 0)
    draw = ImageDraw.Draw(img)
    px = to_px(points)
    w = width * SCALE
    draw.line(px, fill=255, width=int(w))
    for x, y in px:
        draw.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=255)
    return np.asarray(img, dtype=np.float32) / 255.0


def hex_rgb(value: str):
    value = value.lstrip("#")
    return np.array([int(value[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


_YY, _XX = np.mgrid[0 : H * SCALE, 0 : W * SCALE]
UX = _XX / SCALE + OX
UY = _YY / SCALE + OY


def gradient(p0, p1, c0: str, c1: str) -> np.ndarray:
    """Линейный градиент от точки p0 (цвет c0) до p1 (цвет c1) в координатах чертежа."""
    d = np.array(p1, dtype=np.float32) - np.array(p0, dtype=np.float32)
    t = ((UX - p0[0]) * d[0] + (UY - p0[1]) * d[1]) / float(d @ d)
    t = np.clip(t, 0, 1)[..., None]
    return hex_rgb(c0) * (1 - t) + hex_rgb(c1) * t


class Canvas:
    def __init__(self):
        self.rgb = np.zeros((H * SCALE, W * SCALE, 3), dtype=np.float32)
        self.a = np.zeros((H * SCALE, W * SCALE), dtype=np.float32)

    def paint(self, color, mask, opacity=1.0):
        """Кладёт цвет поверх уже нарисованного (обычное наложение с прозрачностью)."""
        if isinstance(color, str):
            color = np.broadcast_to(hex_rgb(color), self.rgb.shape)
        m = (mask * opacity)[..., None]
        out_a = m[..., 0] + self.a * (1 - m[..., 0])
        safe = np.maximum(out_a, 1e-6)[..., None]
        self.rgb = (color * m + self.rgb * self.a[..., None] * (1 - m)) / safe
        self.a = out_a

    def image(self) -> Image.Image:
        rgba = np.dstack([np.clip(self.rgb, 0, 255), self.a * 255]).astype(np.uint8)
        return Image.fromarray(rgba, "RGBA")


def draw_mark() -> Image.Image:
    outer = poly_mask(OUTER)
    inner = poly_mask(INNER)
    # граница между телами: вверху они заходят друг на друга, к низу расходятся щелью
    d = np.where(UY <= 560, 28.0, 28.0 - (UY - 560.0) * (37.0 / 198.0))
    left_region = (UX <= CX + d).astype(np.float32)
    right_region = (UX >= CX - d).astype(np.float32)
    body_l = outer * left_region * (1 - inner)
    body_r = outer * right_region * (1 - inner)
    overlap = body_l * body_r

    cv = Canvas()
    cv.paint(gradient((780, 470), (480, 750), "#8C9BFF", "#5042E6"), body_l)
    cv.paint(gradient((780, 470), (760, 750), "#6BDDA6", "#3A9E7C"), body_r)
    cv.paint("#46A9A0", overlap, 0.92)

    cv.paint(gradient((430, 335), (520, 465), "#9186F8", "#4A3EE2"), circle_mask(CX - 156, 399, 66))
    cv.paint(gradient((730, 335), (835, 465), "#6FE0A9", "#3AA57B"), circle_mask(CX + 156, 399, 66))

    check = stroke_mask([(573, 631), (607, 664), (688, 586)], 30)
    cv.paint(gradient((573, 586), (688, 664), "#5568F0", "#7E9AFF"), check)

    rays = np.maximum.reduce(
        [
            stroke_mask([(CX, 268), (CX, 306)], 24),
            stroke_mask([(546, 296), (574, 332)], 24),
            stroke_mask([(CX * 2 - 546, 296), (CX * 2 - 574, 332)], 24),
        ]
    )
    cv.paint("#A39BF3", rays, 0.95)
    return cv.image()


def fit(mark: Image.Image, side: int, fill: float) -> Image.Image:
    """Знак по центру квадрата side×side на прозрачном фоне; fill — доля стороны."""
    box = mark.getbbox()
    mark = mark.crop(box)
    scale = side * fill / max(mark.size)
    mark = mark.resize((max(1, round(mark.width * scale)), max(1, round(mark.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(mark, ((side - mark.width) // 2, (side - mark.height) // 2))
    return canvas


def tile(side: int, mark: Image.Image, fill: float, radius: float = 0.0) -> Image.Image:
    """Плитка с мягким сиренево-голубым фоном; radius — доля стороны для скругления (0 — квадрат)."""
    y = np.linspace(0, 1, side)[:, None]
    x = np.linspace(0, 1, side)[None, :]
    t = np.clip(0.5 * x + 0.5 * y, 0, 1)[..., None]
    rgb = hex_rgb("#F1EFFF") * (1 - t) + hex_rgb("#E1EEFF") * t
    img = Image.fromarray(np.broadcast_to(rgb, (side, side, 3)).astype(np.uint8), "RGB").convert("RGBA")
    img.alpha_composite(fit(mark, side, fill))
    if radius:
        mask = Image.new("L", (side * 4, side * 4), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, side * 4 - 1, side * 4 - 1], radius=side * 4 * radius, fill=255)
        img.putalpha(mask.resize((side, side), Image.LANCZOS))
    return img


def main() -> None:
    images = OUT / "images"
    images.mkdir(parents=True, exist_ok=True)
    mark = draw_mark()
    fit(mark, 512, 0.94).save(images / "logo_mark.png")
    tile(512, mark, 0.62, radius=0.27).save(images / "logo_tile.png")
    tile(1024, mark, 0.62).save(OUT / "icon.png")  # иконка приложения: квадрат на всю площадь
    tile(128, mark, 0.7, radius=0.22).save(OUT / "favicon.png")
    print("готово:", sorted(p.name for p in OUT.rglob("*.png")))


if __name__ == "__main__":
    main()
