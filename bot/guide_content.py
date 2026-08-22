"""Контент гайда и тексты бота."""

from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent / "content"
GUIDE_FILE = CONTENT_DIR / "guide.html"
GUIDE_FILENAME = "Как подготовиться к интервью на Product Manager.html"

GUIDE_TITLE = "Как подготовиться к интервью на Product Manager"

GUIDE_CAPTION = (
    "Гайд: подготовка к интервью на Product Manager.\n"
    "Откройте файл в браузере – там полный материал.\n\n"
    "Запись на консультацию: /book"
)

WELCOME_FROM_SITE = (
    "Ты перешёл с сайта – сейчас пришлю гайд по подготовке к интервью на Product Manager."
)

WELCOME_DEFAULT = (
    "Привет! Я бот карьерных консультаций.\n\n"
    "Здесь можно получить гайд или записаться к ментору."
)

BOOKING_INTRO = "Выбери эксперта:"
BOOKING_SUCCESS = (
    "✅ <b>Заявка принята!</b>\n\n"
    "Мы получили твой выбор и свяжемся с тобой в Telegram, чтобы уточнить детали записи."
)
