# Marketplace AI

Анализ скрытых причин недовольства покупателей по бренду на Wildberries: сбор отзывов, кластеризация негативных жалоб, описание проблем через LLM.

## Функционал:

1. Находит товары бренда на WB (API, при необходимости — браузер).
2. Собирает отзывы, дедуплицирует варианты одной карточки (`imt_id`).
3. Фильтрует негативные отзывы (по умолчанию оценка ≤ 3, текст ≥ 8 символов).
4. Группирует похожие жалобы (эмбеддинги + HDBSCAN/KMeans).
5. Генерирует названия кластеров и первопричины (Ollama).
6. Сохраняет отчёт в `reports/` (CSV + JSON), опционально — в PostgreSQL.

## Требования

- Python 3.11+
- Ollama
- PostgreSQL — только если нужен `--save-db`
- Chrome — только если API WB не находит товары (режим `--cdp-url`)

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
playwright install chromium   # если планируете --use-browser
```

Заполните файл `.env` своими данными:

Для сохранения в БД создайте схему:

```bash
python scripts/create_tables.py
```

Если таблицы уже есть и нужно пересоздать с нуля (все данные будут удалены):

```bash
python scripts/create_tables.py --force-recreate
```

## Запуск

```bash
python scripts/run_analysis.py --brand "brand-name"
```

Примеры:

```bash
# больше товаров и отзывов
python scripts/run_analysis.py --brand scan-to --max-products 200 --max-reviews-per-product 200

# сохранить в PostgreSQL
python scripts/run_analysis.py --brand "BLACK BOX" --save-db

# если API не нашёл товары — подключить ваш Chrome
python scripts/run_analysis.py --brand vitaveris --cdp-url http://127.0.0.1:9222
```

Chrome для CDP:

```text
chrome.exe --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\wb-chrome-profile"
```

Откройте wildberries.ru в этом окне, затем запустите анализ с `--cdp-url`.

## Основные флаги

| Флаг | Описание |
|------|----------|
| `--brand` | Slug или ссылка на бренд WB (обязательный) |
| `--max-products` | Лимит товаров (по умолчанию 120) |
| `--max-reviews-per-product` | Лимит отзывов на карточку (120) |
| `--top` | Сколько проблем показать в отчёте и БД (10) |
| `--output-dir` | Папка отчётов (по умолчанию `reports`) |
| `--save-db` | Записать результат в PostgreSQL |
| `--include-neutral` | Включить отзывы с 4–5 звёздами |
| `--headless` | Playwright в headless-режиме (часто блокируется) |
| `--no-wait-captcha` | Не ждать ручного прохождения anti-bot |
| `--cdp-url` | Подключение к открытому Chrome |
| `--use-browser` | Playwright, если API не сработал |

## Структура

```text
app/          — логика: парсер WB, фильтры, кластеризация, LLM, отчёты, БД
scripts/      — точки входа (run_analysis.py, create_tables.py)
reports/      — сгенерированные CSV/JSON (не коммитить, см. .gitignore)
```

## Тесты

```bash
pytest
```

Покрыта чистая логика: фильтр отзывов, нормализация брендов, severity, пайплайн (top-N без лишних LLM-вызовов), экспорт отчётов, сохранение в БД (SQLite in-memory). Парсер WB, эмбеддинги и LLM в тестах не гоняются.

## Примечания

- Строки `Получено уникальных отзывов: 0` — у карточки нет отзывов, это не ошибка.
- `Отзывы уже загружены для imt_id=...` — варианты одного товара, отзывы общие.
- Первый запуск скачивает модель эмбеддингов с Hugging Face — может занять время.
