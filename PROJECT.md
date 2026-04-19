# Документация проекта (лендинг консультаций PM / карьера в IT)

Внутренний справочник по устройству репозитория: стек, файлы, контракты `data-*`, состояние в `localStorage` и типичные сценарии правок.

---

## 1. Назначение

Одностраничный маркетинговый сайт на русском: консультации по product management и карьере в IT. Два сценария первого экрана («Для всех» / «Для студентов») с блоком «Об эксперте» (синяя плашка под hero) и дальше — услуги, выбор «дорожной карты», лид-магнит (форма гайда), отзывы, контакты.

**Бэкенда нет:** форма гайда в `js/site.js` только валидирует ввод и показывает сообщение; отправки на сервер не подключено.

---

## 2. Стек и ограничения

| Слой | Технология |
|------|------------|
| Разметка | Один `index.html` |
| Стили | `css/hero.css` (дизайн-токены, hero, база, тёмная тема, rail), `css/sections.css` (секции под `main`, первый экран, шторки) |
| Логика | `js/site.js` (один IIFE, без сборки) |
| Шрифты | Google Fonts: Archivo Black, Playfair Display; локально/CDN — Formular и Favorit Pro (см. комментарий в `<head>`) |

- **Сборки нет** — правки вносятся напрямую в файлы.
- Для локальной разработки страницу лучше открывать через **HTTP** (`python3 -m http.server`), а не `file://`: отдельные сценарии с медиа и путями ведут себя предсказуемее по HTTP.
- **Кэш-бастинг** (актуальные значения смотреть в `index.html`):
  - `css/hero.css?v=…`, `js/site.js?v=…` — при существенных правках CSS/JS версию увеличивать.
  - `css/sections.css?v=…` — то же для секций и первого экрана.

---

## 3. Структура репозитория

```
сайт/
├── index.html          # Вся страница + inline-скрипт табов отзывов
├── css/
│   ├── hero.css        # :root, сброс, hero, site-rail, liquid glass, тёмная тема
│   └── sections.css    # main-fold, шторки about, секции, path/gantt, services, guide, reviews, contact, reveal
├── js/
│   └── site.js         # Тема, rail, path, герой/видео, main-fold bleed, форма гайда, reveal
├── assets/             # Медиа (изображения, видео, исходники монтажа)
└── PROJECT.md          # Этот файл
```

**Медиа** (по ссылкам в HTML): портреты `hero-portrait*.png`, фон `hero-intern-background.png`, **видео смены персоны** `assets/hero-persona-swap.mp4` (в разметке один атрибут `src` на `<video>`). Дополнительно в репозитории может лежать `hero-persona-swap.webm` для ручного перекодирования; в проде на странице используется MP4. Исходник монтажа: `assets/test.mov` (ProRes и т.п.).

`.gitignore` игнорирует `.DS_Store` и `.cursor/`.

---

## 4. Каркас страницы (`index.html`)

Порядок сверху вниз:

1. **SVG-фильтр** `#liquid-glass` — «жидкое стекло» для `backdrop-filter` в Chromium (класс `liquid-glass` у блоков).
2. **`#about` → `.main-fold`** — первый экран:
   - **`.hero`** — `data-hero-persona="pro" | "intern"`, табы, медиа (два спикера + видео смены).
   - **`.about__curtain.about__curtain--fold`** — компактная **синяя плашка** (имя и теглайн спикера), скругление со всех сторон, не сливается с секцией «Обо мне».
   - **`.main-fold__blue-bleed`** — служебный блок, заполняющий **оставшуюся высоту до низа вьюпорта** синим (стыкуется с шторкой, в т.ч. под скруглением — без белых «ушек»). При скролле вниз на `body` вешается класс **`main-fold--content-revealed`** на `.main-fold`: хвост схлопывается, высота первого блока перестаёт быть «экранной», дальше идёт обычный фон и контент.
3. **`nav.site-rail`** — фиксированная навигация слева (`data-site-rail`), появляется после ухода hero с экрана.
4. **`main.main`** — секции с якорями:
   - **`section.section--about`** — текст «обо мне» на **фоне страницы** (не синяя «продолжение» шторки); обёртка `about__curtain--rest` без синего фона.
   - `#services` — карточки форматов + выбор пути (`data-path-pick`).
   - `#path` — Gantt-подобные схемы занятий (скрыты до выбора).
   - `#guide` — форма лида.
   - `#reviews` — табы отзывов.
   - `#contact` — контакты.

**Инлайн-скрипт в конце `index.html`** — только переключение табов отзывов (`[data-reviews-tabs]`). Остальная логика — в `site.js`.

---

## 5. CSS: разделение ответственности

### `hero.css`

- Глобальные **design tokens** в `:root` и переопределения в `html[data-theme="dark"]`.
- Явный **reset** (`box-sizing`, `body`, типографика, `text-wrap: pretty` где поддерживается).
- Компоненты **hero** (сетка, спикеры, видео-слой, переключатель темы).
- В контексте **`.main-fold`** — слегка ужатые `max-height` / `scale` медиа, чтобы чаще помещались hero + синяя шторка во вьюпорт.
- **Site rail** — позиционирование, соединители, активное состояние шагов.
- Утилиты вроде **liquid glass** и переменных для отступов с учётом `safe-area` и ширины rail.

### `sections.css`

- **`.main-fold`**: `min-height` на весь вьюпорт (`100svh` / `100dvh`), CSS-переменная **`--fold-curtain-radius`** для шторки и синего хвоста, стили **`.main-fold__blue-bleed`** и состояния **`.main-fold--content-revealed`**.
- Секции под **`main`**: about (светлый блок), услуги, path, guide, reviews, contact.
- **Reveal:** стили для `[data-reveal]`; анимации отключаются при `prefers-reduced-motion` (для синего хвоста при reduced motion хвост скрыт, класс «раскрытия» выставляется сразу в JS).

При добавлении новой секции: якорь `id` на `<section>`, стили — в `sections.css`, при необходимости расширить rail в HTML и логику видимости шага `#path`.

---

## 6. JavaScript (`js/site.js`)

Один самовызывающийся модуль (строгий режим). Крупные блоки:

### 6.1 Тема (`data-theme-toggle`)

- Клик переключает `data-theme="dark"` на `<html>`.
- **`localStorage` ключ:** `theme` → значение `"dark"` или отсутствует (светлая).
- Обновляются `aria-pressed` и `aria-label` кнопки.

### 6.2 Секция «Наш путь» (`#path`)

- Карточки в услугах: `.services__card--path-pick` с `data-path-pick="idle" | "coaching" | "interview"`.
- Состояние секции: атрибут **`data-path-state`** на `#path` (`idle` — секция скрыта через `hidden`, показываются подсказки «выберите карточку»).
- **`localStorage` ключ:** `pathFormat` — хранит `coaching` или `interview` (как и тема — для возврата пользователя к выбору).
- Элемент навигации с **`data-rail-path-step`** скрыт, пока путь в `idle` (чтобы не вести в пустую секцию).

### 6.3 Боковой rail (`[data-site-rail]`)

- После того как низ **`.hero`** уходит выше viewport, на `body` ставится **`data-site-rail-revealed="true"`**, у rail снимается `aria-hidden`.
- Скролл: по позиции «зонда» (~35% высоты окна) вычисляется активный пункт; шагам вешаются классы `is-active` / `is-passed`, ссылкам — `aria-current="location"`.
- **Коннекторы** (`[data-rail-connector]`) получают CSS-переменную **`--fill`** (0…1) для прогресс-линии между якорями.
- Учитываются только ссылки в **видимых** `[data-rail-step]` (важно для скрытого шага path).
- `ResizeObserver` на `main section[id]` пересчитывает позиции при изменении высоты контента.

### 6.4 Форма гайда (`#guide-form`)

- Поля: `#guide-name`, `#guide-telegram`, чекбокс согласия.
- Telegram: нормализация (убрать `@`), проверка regex латиницы/цифр/`_`, длина 4–32.
- По сабмиту: сообщение в `#guide-status`, сброс формы; **сетевых запросов нет**.

### 6.5 Герой: персоны и видео

- **`data-hero-persona`** на `.hero`: `pro` | `intern`.
- Табы: `[data-hero-persona-set]`, копии: `[data-persona-copy="pro|intern"]` (переключение `hidden`).
- Спикеры: `[data-hero-speaker="pro|intern"]` — клик/Enter/Space переключают персону; у неактивного спикера при hover/focus подставляются «активные» PNG для превью.
- Видео `#hero-persona-swap-video`: проигрывание вперёд/назад при смене персоны, защита от гонок через счётчик **`heroSwapEpoch`**, обработка `ended` / `timeupdate` для реверса.
- Стартовые стоп-кадры: для `pro` — первый кадр ролика (`initHeroVideoPosterFrame`), для `intern` — конец (`initHeroVideoEndFrame`).
- **`localStorage` ключ:** `heroPersona` → `intern` или по умолчанию pro.
- **URL:** `?persona=intern` или `?hero=intern` задаёт начальную персону без анимации (`skipVideo: true` при инициализации).

### 6.6 Первый экран: синий хвост (`.main-fold__blue-bleed`)

- При **`scrollY` выше порога** (десятки px, см. код) на **`.main-fold`** добавляется класс **`main-fold--content-revealed`**, иначе снимается — при возврате к верху страницы эффект снова активен.
- При **`prefers-reduced-motion: reduce`** класс выставляется сразу, отдельная анимация хвоста не показывается.

### 6.7 Reveal-on-scroll

- Элементы с **`[data-reveal]`** наблюдаются через `IntersectionObserver`; при появлении добавляется класс **`is-revealed`**, опционально **`data-reveal-delay`** (мс) задаёт CSS-переменную `--reveal-delay`.
- Fallback без `IntersectionObserver`: сразу `is-revealed` на всех.

---

## 7. Состояние и контракты данных

### Атрибуты, на которые опирается код

| Атрибут | Где | Назначение |
|--------|-----|------------|
| `data-theme-toggle` | Кнопка темы | Переключение тёмной темы |
| `data-site-rail` | `nav` | Корень боковой навигации |
| `data-rail-step` | `li` шага | Видимость участвует в расчёте rail |
| `data-rail-link` | `a` | Якорные ссылки rail |
| `data-rail-connector` | `span` | Вертикальная линия-прогресс между пунктами |
| `data-rail-path-step` | Шаг к `#path` | Скрыт при `path-state=idle` |
| `data-path-pick` | Карточка услуги | `idle` / `coaching` / `interview` |
| `data-path-state` | `#path` | Текущий режим секции |
| `data-path-intro`, `data-path-heading`, `data-path-idle`, `data-path-panel` | Внутри `#path` | Переключаемые куски UI |
| `data-hero-persona` | `.hero` | Активная персона |
| `data-hero-persona-set` | Табы | Значение персоны |
| `data-persona-copy` | Разные узлы | Копирайт для pro/intern |
| `data-hero-speaker` | Блок спикера | Клик → смена персоны |
| `data-reviews-tabs` | Корень отзывов | Inline-скрипт + `aria` |
| `data-reveal`, `data-reveal-delay` | Секции/карточки | Анимация появления |

### Классы первого экрана (CSS + JS)

| Класс | Где | Назначение |
|-------|-----|------------|
| `main-fold--content-revealed` | `.main-fold` | Синий хвост схлопнут, обычная высота блока |

### Ключи `localStorage`

| Ключ | Значения |
|------|----------|
| `theme` | `"dark"` или нет |
| `pathFormat` | `coaching`, `interview` или удалён в idle |
| `heroPersona` | `intern` или по умолчанию pro |

---

## 8. Доступность (кратко)

- Табы персоны и отзывов: `role="tablist"` / `tab` / `tabpanel`, `aria-selected`, клавиатура стрелками.
- Rail: `aria-hidden` пока hero на экране; текущий пункт — `aria-current="location"`.
- Форма: `reportValidity`, кастомные сообщения на полях, `#guide-status` с `role="status"`, `aria-live="polite"`.

---

## 9. Типичные задачи

| Задача | Куда смотреть |
|--------|----------------|
| Поменять цвета/типографику | `hero.css` → `:root` и `html[data-theme="dark"]` |
| Новая секция с якорем | `index.html` (`main`), стили в `sections.css`, при необходимости пункт в `nav.site-rail` |
| Изменить тексты под персону | Блоки с `data-persona-copy` в hero и about |
| Подключить отправку формы гайда | Обработчик `submit` в `site.js`, бэкенд endpoint |
| Заменить видео смены персоны | `assets/hero-persona-swap.mp4` (+ при необходимости перекодировать из `test.mov`), проверить кадры под `initHeroVideo*` |
| Настроить первый экран / синий хвост | `sections.css` (`.main-fold`, `.main-fold__blue-bleed`), `site.js` (`initMainFoldBleed`) |
| Сброс кэша у клиентов | Увеличить `?v=` у `hero.css`, `sections.css`, `site.js` в `index.html` |

---

## 10. Git

Репозиторий: ветка **`main`**, удалённый **`origin`** (например `https://github.com/koolesoo/landing.git`). Коммиты и пуш — стандартный Git CLI.

---

*Последнее обновление документа: 18 апреля 2026. При крупных изменениях в вёрстке или JS имеет смысл обновить разделы 4–7.*
