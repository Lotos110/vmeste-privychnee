"""Автоматическая проверка текстов объявлений и откликов.

Ловит обмен контактами (ссылки, телефоны, @ники, мессенджеры), ругань и взрослые темы. Фильтр грубый:
он не заменяет жалобы и ручную проверку в админке, а только отсекает самое очевидное.
"""

import re

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"))
# латинские буквы, похожие на русские: «ху1», «пиzда» и прочие обходы
_LOOKALIKES = str.maketrans("abekmhopctyxz", "авекмнорстухз")

_URL = re.compile(r"(https?://|www\.|\b[\w-]+\.(?:ru|kz|com|net|org|me|io|su|by|ua|app|xyz|info|ly)\b|t\.me|wa\.me)", re.I)
_EMAIL = re.compile(r"[\w.+-]+\s?[@＠]\s?[\w-]+\s?\.\s?\w+")
_HANDLE = re.compile(r"(?<!\w)[@＠]\s?[\w.]{3,}")
_PHONE = re.compile(r"\+?\d[\d\s\-().]{5,}\d")
_MESSENGERS = re.compile(
    r"telegram|whatsapp|viber|instagram|snapchat|discord|tiktok|signal|"
    r"телег|вацап|ватсап|вотсап|вайбер|инстаграм|инста\b|снапчат|дискорд|тикток|"
    r"\bтг\b|\bвк\b|вконтакте|в\s?личку|в\s?лс\b|в\s?директ",
    re.I,
)
_BAD_WORDS = re.compile(
    r"хуй|хуе|хуя|пизд|(?<![а-я])еб(?:ал|ать|ан|ну|ут|и\b)|бляд|\bблят|\bсук[аи]\b|мудак|мудил|долбо[её]б|"
    r"гандон|залуп|шлюх|проститу|\bчмо\b|\bурод|дебил|"
    r"секс|интим|порно|эротик|голые|голая|нюдс|обнаж|18\+|"
    r"наркот|закладк|спайс|мефедрон|травк[ауе]\b|"
    r"убь[юе]|суицид|самоубий",
    re.I,
)

CONTACTS_MESSAGE = "Не указывайте контакты: ссылки, телефоны, почту, @ники и мессенджеры. Общайтесь здесь, в приложении"
WORDS_MESSAGE = "В тексте есть недопустимые слова. Пожалуйста, перефразируйте"


def _normalize(text: str) -> str:
    return text.translate(_ZERO_WIDTH).lower().replace("ё", "е")


def check_text(text: str) -> str | None:
    """Возвращает причину отказа для человека или None, если текст допустим."""
    plain = _normalize(text)
    if _URL.search(plain) or _EMAIL.search(plain) or _HANDLE.search(plain) or _MESSENGERS.search(plain):
        return CONTACTS_MESSAGE
    for match in _PHONE.finditer(plain):
        if sum(ch.isdigit() for ch in match.group()) >= 7:
            return CONTACTS_MESSAGE
    if _BAD_WORDS.search(plain) or _BAD_WORDS.search(plain.translate(_LOOKALIKES)):
        return WORDS_MESSAGE
    return None
