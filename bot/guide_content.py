"""Контент гайда, который бот отправляет пользователям с сайта."""

from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent / "content"
GUIDE_FILE = CONTENT_DIR / "guide.html"
GUIDE_FILENAME = "Как подготовиться к интервью на Product Manager.html"

GUIDE_TITLE = "Как подготовиться к интервью на Product Manager"

GUIDE_CAPTION = (
    "Гайд: подготовка к интервью на Product Manager.\n"
    "Откройте файл в браузере — там полный материал.\n\n"
    "Вопросы: @neradana"
)

WELCOME_FROM_SITE = (
    "Вы перешли с сайта — сейчас пришлю гайд по подготовке к интервью на Product Manager. "
    "Если файл не пришёл, отправьте /guide"
)

WELCOME_DEFAULT = (
    "Привет! Я бот Насти Нерадовских.\n\n"
    "Отправьте /guide — пришлю гайд по подготовке к интервью на Product Manager.\n"
    "Или напишите напрямую: @neradana"
)
