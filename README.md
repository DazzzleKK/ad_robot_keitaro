# Adrobot

MVP на FastAPI для создания кампаний в Keitaro, обновления справочников
Keitaro, редактирования офферов в потоках и восстановления офферов из
локальной истории.

## Стек

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Jinja2
- httpx
- pytest
- ruff

## Настройка

```bash
uv sync --extra dev
cp .env.example .env
```

Заполните значения Keitaro в `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://adrobot:adrobot@localhost:5432/adrobot
KEITARO_BASE_URL=https://your-keitaro.example
KEITARO_API_KEY=your-api-key
```

## База данных

```bash
docker compose up -d postgres
uv run alembic upgrade head
```

Для полной проверки внутри Docker-сети:

```bash
docker compose run --rm test
```

## Запуск

```bash
uv run uvicorn src.main:app --reload
```

Откройте `http://127.0.0.1:8000/campaigns/new`.

Перед созданием кампании откройте `http://127.0.0.1:8000/dictionaries`
и нажмите `Refresh from Keitaro`. Форма создания кампании использует Keitaro ID
из этих локально сохраненных справочников для домена, группы кампании,
источника трафика и офферов.

Или запустите весь стек через Compose:

```bash
docker compose build app
docker compose up -d app
```

## Тесты и линтер

```bash
uv run pytest
uv run ruff check src tests migrations
```