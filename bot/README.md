# Telegram-бот для гайда с сайта

Бот отправляет гайд «Первые шаги к стажировке или junior-роли в IT» пользователям, которые заполнили форму на сайте.

## Как это работает

1. Пользователь вводит @username на сайте и соглашается на обработку данных.
2. Сайт отправляет заявку на API бота (`POST /api/guide`).
3. Пользователю открывается ссылка `https://t.me/ВАШ_БОТ?start=guide`.
4. После нажатия **Start** в Telegram бот автоматически присылает гайд.

> Telegram не позволяет боту писать первым — пользователь обязательно должен нажать Start.

## Быстрый старт

### 1. Создайте бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram.
2. Команда `/newbot` → задайте имя и username (например, `nastya_it_guide_bot`).
3. Скопируйте токен.

### 2. Настройте окружение

```bash
cd bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполните `.env`:

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен от BotFather |
| `BOT_USERNAME` | Username бота без `@` |
| `BOT_MODE` | `polling` — локально, `webhook` — на сервере |
| `ALLOWED_ORIGINS` | URL сайта для CORS |

### 3. Запуск локально

```bash
python main.py
```

Проверка: откройте `http://localhost:8080/health` → `{"status":"ok"}`.

В Telegram: `/start guide` или `/guide` — должен прийти гайд.

### 4. Подключите сайт

В `index.html` у формы гайда задайте URL API:

```html
<form
  id="guide-form"
  data-guide-api="https://ВАШ-СЕРВЕР/api/guide"
  data-bot-username="ваш_бот"
>
```

Если `data-guide-api` пустой, форма просто откроет бота в Telegram (без сохранения заявки).

## Деплой (webhook)

Подойдут Railway, Render, Fly.io, VPS с Docker.

1. Установите `BOT_MODE=webhook`.
2. Укажите `WEBHOOK_URL=https://ваш-домен` (без слэша в конце).
3. Задайте случайный `WEBHOOK_SECRET`.
4. Откройте порт `PORT` (по умолчанию 8080).

Пример Dockerfile:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## API

### `POST /api/guide`

```json
{
  "telegram": "@username",
  "consent": true
}
```

Ответ:

```json
{
  "ok": true,
  "bot_url": "https://t.me/your_bot?start=guide",
  "message": "Откройте бота в Telegram и нажмите «Start»..."
}
```

## Админ-бот для уведомлений

События основного бота (гайд, старт записи, успешная заявка, отмена) уходят в отдельный бот `@career67_bot`.

Доступ только у аккаунтов из `ALLOWED_ADMIN_USERNAMES` (по умолчанию `@neradana` и `@koolesoo`).

После деплоя каждый админ один раз пишет `/start` в `@career67_bot` — бот сохранит chat id и начнёт присылать уведомления.

| Переменная | Описание |
|------------|----------|
| `ADMIN_BOT_TOKEN` | Токен админ-бота от BotFather |
| `ADMIN_BOT_USERNAME` | Username без `@` (`career67_bot`) |
| `ALLOWED_ADMIN_USERNAMES` | Список username через запятую |
| `ADMIN_CHAT_IDS` | Опционально: chat id через запятую |

## Редактирование гайда

Текст в `guide_content.py`. Можно добавить PDF:

```python
await message.reply_document(document=open("content/guide.pdf", "rb"))
```

## Команды бота

| Команда | Действие |
|---------|----------|
| `/start guide` | Приветствие + гайд (переход с сайта) |
| `/start` | Приветствие + гайд |
| `/guide` | Повторно отправить гайд |

Заявки с сайта сохраняются в `data/guide.db`.
