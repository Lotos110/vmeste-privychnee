"""Цвета и размеры из макетов: фиолетовый и зелёный на светлом фоне."""

# Шрифты (файлы лежат в assets/fonts, лицензия OFL). Сочетание: заголовки, кнопки и цифры
# набираются Comfortaa, основной текст — Nunito (он тоже округлый, но легче читается мелким).
# Каждое начертание — отдельное «семейство»: так Flet надёжно подбирает нужный файл.
FONT_BODY = "Nunito"
FONT_BODY_BOLD = "Nunito Bold"
FONT_HEAD = "Comfortaa"
FONT_HEAD_BOLD = "Comfortaa Bold"
FONT_FILES = {
    FONT_BODY: "fonts/Nunito-Regular.ttf",
    FONT_BODY_BOLD: "fonts/Nunito-Bold.ttf",
    FONT_HEAD: "fonts/Comfortaa-Regular.ttf",
    FONT_HEAD_BOLD: "fonts/Comfortaa-Bold.ttf",
}

PRIMARY = "#6C5CE7"
PRIMARY_DARK = "#5547D0"
PRIMARY_SOFT = "#EEEBFD"
PRIMARY_GRADIENT = ["#6C5CE7", "#8C7CF4"]

GREEN = "#3CB878"
GREEN_LIGHT = "#8FD9AE"
GREEN_SOFT = "#E3F6EB"

ORANGE = "#FF8A3D"
ORANGE_SOFT = "#FFF1E3"
BLUE = "#2E90FA"
BLUE_SOFT = "#E4F1FF"
RED = "#E5484D"
RED_SOFT = "#FDE8E9"

BG = "#F6F6FC"
CARD = "#FFFFFF"
TEXT = "#1F2340"
MUTED = "#8A8FA8"
BORDER = "#ECECF5"
WHITE = "#FFFFFF"
SHADOW = "#141F2340"  # формат #AARRGGBB: тень с прозрачностью около 8%

# категория привычки -> (цвет фона иконки, цвет иконки)
CATEGORY_COLORS = {
    "sleep": (PRIMARY_SOFT, PRIMARY),
    "water": (BLUE_SOFT, BLUE),
    "sport": (PRIMARY_SOFT, PRIMARY),
    "nutrition": (ORANGE_SOFT, ORANGE),
    "productivity": (ORANGE_SOFT, ORANGE),
    "mental": (GREEN_SOFT, GREEN),
    "health": (RED_SOFT, RED),
}
DEFAULT_CATEGORY_COLORS = (PRIMARY_SOFT, PRIMARY)

# цвет, который пользователь выбирает для своей привычки -> (фон иконки, цвет иконки)
HABIT_COLORS = {
    "purple": (PRIMARY_SOFT, PRIMARY),
    "green": (GREEN_SOFT, GREEN),
    "orange": (ORANGE_SOFT, ORANGE),
    "blue": (BLUE_SOFT, BLUE),
    "red": (RED_SOFT, RED),
}

# иконки на выбор для своей привычки (имена Material)
HABIT_ICONS = [
    "CHECK_CIRCLE_OUTLINE", "MENU_BOOK", "SCHOOL", "LANGUAGE", "CODE", "BRUSH",
    "MUSIC_NOTE", "FITNESS_CENTER", "DIRECTIONS_RUN", "SELF_IMPROVEMENT", "WATER_DROP", "BEDTIME",
    "RESTAURANT", "LOCAL_CAFE", "SPA", "PETS", "SAVINGS", "CLEANING_SERVICES",
]  # fmt: skip

CATEGORY_TITLES = {
    "sleep": "Сон",
    "nutrition": "Питание",
    "sport": "Спорт",
    "water": "Вода",
    "productivity": "Продуктивность",
    "mental": "Ментальное здоровье",
    "relapse": "Срывы",
    "health": "Здоровье",
}

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]  # fmt: skip

CATEGORY_ICONS = {
    "sleep": "BEDTIME",
    "nutrition": "RESTAURANT",
    "sport": "FITNESS_CENTER",
    "water": "WATER_DROP",
    "productivity": "BOLT",
    "mental": "SELF_IMPROVEMENT",
    "relapse": "FAVORITE",
    "health": "HEALTH_AND_SAFETY",
}
