"""Мелкие повторно используемые элементы интерфейса."""

import flet as ft

import theme

W_BOLD = ft.FontWeight.BOLD
W_SEMI = ft.FontWeight.W_600


def icon(name: str, fallback: str = "CIRCLE") -> str:
    """Иконка по имени Material (например, 'WATER_DROP'). Неизвестное имя не ломает экран."""
    return getattr(ft.Icons, name, None) or getattr(ft.Icons, fallback)


def plural(n: int, forms: tuple[str, str, str]) -> str:
    """plural(5, ('день', 'дня', 'дней')) -> 'дней'"""
    n = abs(n) % 100
    if 11 <= n <= 19:
        return forms[2]
    last = n % 10
    if last == 1:
        return forms[0]
    if 2 <= last <= 4:
        return forms[1]
    return forms[2]


def days_text(n: int) -> str:
    return f"{n} {plural(n, ('день', 'дня', 'дней'))}"


def txt(value, size=14, weight=None, color=theme.TEXT, **kwargs) -> ft.Text:
    return ft.Text(value, size=size, weight=weight, color=color, **kwargs)


def title(value: str, size=24) -> ft.Text:
    return txt(value, size, W_BOLD)


def muted(value: str, size=13, **kwargs) -> ft.Text:
    return txt(value, size, color=theme.MUTED, **kwargs)


def card(content, padding=16, on_click=None, bgcolor=theme.CARD, radius=20, **kwargs) -> ft.Container:
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=bgcolor,
        border_radius=radius,
        on_click=on_click,
        ink=on_click is not None,
        shadow=ft.BoxShadow(blur_radius=16, color=theme.SHADOW, offset=ft.Offset(0, 4)),
        **kwargs,
    )


def _button(label, on_click, bgcolor, color, side=None, height=52) -> ft.Row:
    button = ft.ElevatedButton(
        content=ft.Text(label, size=15, weight=W_SEMI),
        on_click=on_click,
        height=height,
        expand=True,
        style=ft.ButtonStyle(
            color=color,
            bgcolor=bgcolor,
            elevation=0,
            side=side,
            shape=ft.RoundedRectangleBorder(radius=16),
        ),
    )
    return ft.Row([button])


def primary_button(label, on_click) -> ft.Row:
    return _button(label, on_click, theme.PRIMARY, theme.WHITE)


def soft_button(label, on_click) -> ft.Row:
    return _button(label, on_click, theme.PRIMARY_SOFT, theme.PRIMARY)


def outline_button(label, on_click) -> ft.Row:
    return _button(label, on_click, theme.CARD, theme.PRIMARY, side=ft.BorderSide(1.5, theme.PRIMARY_SOFT))


def danger_button(label, on_click) -> ft.Row:
    return _button(label, on_click, theme.RED_SOFT, theme.RED)


def small_button(label, on_click, filled=True, color=theme.PRIMARY) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        content=ft.Text(label, size=13, weight=W_SEMI),
        on_click=on_click,
        height=36,
        style=ft.ButtonStyle(
            color=theme.WHITE if filled else color,
            bgcolor=color if filled else theme.PRIMARY_SOFT,
            elevation=0,
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.padding.symmetric(horizontal=16),
        ),
    )


def link(label, on_click, color=theme.PRIMARY, size=14) -> ft.Container:
    return ft.Container(
        content=ft.Text(label, size=size, weight=W_SEMI, color=color),
        on_click=on_click,
        padding=ft.padding.symmetric(horizontal=4, vertical=4),
    )


def field(
    label,
    value="",
    password=False,
    keyboard=None,
    prefix=None,
    multiline=False,
    hint=None,
    max_length=None,
    on_submit=None,
) -> ft.TextField:
    kwargs = {}
    if keyboard is not None:
        kwargs["keyboard_type"] = keyboard
    if prefix:
        kwargs["prefix_icon"] = icon(prefix)
    if multiline:
        kwargs["multiline"] = True
        kwargs["min_lines"] = 3
        kwargs["max_lines"] = 5
    if max_length:
        kwargs["max_length"] = max_length
    if on_submit:
        kwargs["on_submit"] = on_submit
    return ft.TextField(
        label=label,
        value=value or "",
        hint_text=hint,
        password=password,
        can_reveal_password=password,
        border_radius=14,
        filled=True,
        bgcolor=theme.CARD,
        border_color=theme.BORDER,
        focused_border_color=theme.PRIMARY,
        text_size=15,
        **kwargs,
    )


def progress(percent, color=theme.GREEN, height=8) -> ft.Container:
    percent = max(0, min(100, int(percent or 0)))
    parts = []
    if percent > 0:
        parts.append(ft.Container(expand=percent, height=height, bgcolor=color, border_radius=height))
    if percent < 100:
        parts.append(ft.Container(expand=100 - percent, height=height))
    return ft.Container(
        height=height,
        bgcolor=theme.BORDER,
        border_radius=height,
        content=ft.Row(parts, spacing=0),
    )


def circle_icon(name: str, bg: str, fg: str, size=48) -> ft.Container:
    return ft.Container(
        width=size,
        height=size,
        border_radius=size / 2,
        bgcolor=bg,
        alignment=ft.alignment.center,
        content=ft.Icon(icon(name), color=fg, size=size * 0.5),
    )


def avatar(app, name: str, url: str | None, radius=24) -> ft.Container:
    size = radius * 2
    initial = (name or "?")[:1].upper()
    content = ft.Text(initial, size=radius * 0.8, weight=W_BOLD, color=theme.PRIMARY)
    image_url = app.api.media_url(url)
    if image_url:
        content = ft.Image(src=image_url, width=size, height=size, fit=ft.ImageFit.COVER)
    return ft.Container(
        width=size,
        height=size,
        border_radius=radius,
        bgcolor=theme.PRIMARY_SOFT,
        alignment=ft.alignment.center,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=content,
    )


def chip(label, selected, on_click) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            label, size=13, weight=W_SEMI, color=theme.WHITE if selected else theme.TEXT
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        border_radius=20,
        bgcolor=theme.PRIMARY if selected else theme.CARD,
        border=ft.border.all(1, theme.PRIMARY if selected else theme.BORDER),
        on_click=on_click,
    )


def segmented(labels: list[str], selected: int, on_select) -> ft.Container:
    """Переключатель вида «Неделя | Месяц | Все время». on_select(index)."""
    items = []
    for index, label in enumerate(labels):
        active = index == selected
        items.append(
            ft.Container(
                expand=1,
                alignment=ft.alignment.center,
                padding=ft.padding.symmetric(vertical=10),
                border_radius=12,
                bgcolor=theme.CARD if active else None,
                content=ft.Text(
                    label,
                    size=13,
                    weight=W_SEMI,
                    color=theme.PRIMARY if active else theme.MUTED,
                ),
                on_click=lambda e, i=index: on_select(i),
            )
        )
    return ft.Container(
        content=ft.Row(items, spacing=4),
        bgcolor=theme.PRIMARY_SOFT,
        border_radius=16,
        padding=4,
    )


def section_header(label: str, action: str | None = None, on_action=None) -> ft.Row:
    controls = [txt(label, 18, W_BOLD)]
    if action:
        controls.append(link(action + " ›", on_action))
    return ft.Row(controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)


def loading() -> ft.Container:
    return ft.Container(
        content=ft.ProgressRing(color=theme.PRIMARY),
        alignment=ft.alignment.center,
        padding=40,
    )


def empty_state(message: str, emoji="🌱") -> ft.Container:
    return ft.Container(
        alignment=ft.alignment.center,
        padding=24,
        content=ft.Column(
            [ft.Text(emoji, size=40), muted(message, 14, text_align=ft.TextAlign.CENTER)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
    )


def error_box(message: str, on_retry) -> ft.Container:
    return ft.Container(
        alignment=ft.alignment.center,
        padding=24,
        content=ft.Column(
            [
                ft.Icon(icon("CLOUD_OFF"), color=theme.MUTED, size=40),
                txt(message, 14, color=theme.TEXT, text_align=ft.TextAlign.CENTER),
                small_button("Повторить", on_retry),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
    )


def spacer(height=8) -> ft.Container:
    return ft.Container(height=height)


def centered_text(value, size=14, weight=None, color=theme.TEXT, **kwargs) -> ft.Row:
    return ft.Row(
        [ft.Text(value, size=size, weight=weight, color=color, expand=True,
                 text_align=ft.TextAlign.CENTER, **kwargs)]
    )


def format_code(code: str) -> str:
    """K7M2QX9R -> K7M2-QX9R (так код легче читать и диктовать)."""
    return f"{code[:4]}-{code[4:]}" if code and len(code) > 4 else code or ""


def menu_row(icon_name: str, label: str, on_click, subtitle: str | None = None,
             color=theme.PRIMARY, bg=theme.PRIMARY_SOFT) -> ft.Container:
    texts = [txt(label, 15, W_SEMI)]
    if subtitle:
        texts.append(muted(subtitle, 12))
    return card(
        ft.Row(
            [
                circle_icon(icon_name, bg, color, 40),
                ft.Column(texts, spacing=2, expand=True),
                ft.Icon(icon("CHEVRON_RIGHT"), color=theme.MUTED),
            ],
            spacing=12,
        ),
        padding=12,
        on_click=on_click,
        radius=16,
    )
