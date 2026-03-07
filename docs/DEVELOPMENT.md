# Руководство по разработке MAX BOTS HUB

**Дата:** 4 февраля 2026
**Статус:** Draft v0.1

---

## 📋 Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Структура проекта](#структура-проекта)
3. [База данных](#база-данных)
4. [API разработка](#api-разработка)
5. [Тестирование](#тестирование)
6. [Деплой](#деплой)

---

## 🚀 Быстрый старт

### Требования

- Python 3.11+
- PostgreSQL 15+ с расширением pgvector
- Node.js 18+ (для frontend)
- Git

### Установка

```bash
# 1. Клонировать репозиторий
cd C:\Users\mafio\OneDrive\Документы\projects\max-bots-hub

# 2. Создать виртуальное окружение
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить .env
copy .env.example .env
# Заполнить переменные окружения в .env

# 5. Создать базу данных
psql -U postgres
CREATE DATABASE max_bots_hub;
\q

# 6. Запустить миграции
psql -U postgres -d max_bots_hub -f migrations/versions/001_add_multitenancy.sql

# 7. Запустить сервер (development)
python -m platform.main
```

Сервер запустится на http://localhost:8000

- Документация API: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

---

## 📁 Структура проекта

```
max-bots-hub/
├── platform/                # Ядро платформы
│   ├── api/                # FastAPI endpoints
│   │   ├── auth.py        # JWT аутентификация
│   │   ├── tenants.py     # CRUD тенантов (TODO)
│   │   ├── bots.py        # CRUD ботов (TODO)
│   │   └── ...
│   ├── models/             # SQLAlchemy модели
│   │   └── tenant.py      # Tenant, BotConfig, Subscription
│   ├── services/           # Бизнес-логика (TODO)
│   └── main.py            # FastAPI app
│
├── shared/                 # Общий код
│   ├── config/
│   │   └── settings.py    # Конфигурация из .env
│   ├── database/
│   │   ├── base.py        # AsyncSession setup
│   │   └── tenant_middleware.py  # RLS изоляция
│   ├── ai_clients/        # AI провайдеры (TODO)
│   └── rag/               # RAG система (TODO)
│
├── bot_templates/          # Шаблоны ботов (TODO)
├── frontend/               # React приложения (TODO)
├── migrations/             # SQL миграции
├── docs/                   # Документация
└── tests/                  # Тесты (TODO)
```

---

## 🗄️ База данных

### Модели

| Таблица | Описание |
|---------|----------|
| `tenants` | Клиенты платформы |
| `bot_configs` | Конфигурации ботов |
| `subscriptions` | Подписки |
| `usage_stats` | Статистика использования |

### Миграции

Миграции находятся в `migrations/versions/`:

```bash
# Применить миграцию
psql -U postgres -d max_bots_hub -f migrations/versions/001_add_multitenancy.sql

# Откатить миграцию (TODO: создать rollback скрипты)
```

### Row-Level Security (RLS)

Изоляция данных реализована через PostgreSQL RLS:

```sql
-- Включено для:
ALTER TABLE bot_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_stats ENABLE ROW LEVEL SECURITY;

-- Политика изоляции:
CREATE POLICY tenant_isolation ON bot_configs
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

**Автоматическая установка tenant_id в коде:**

```python
from shared.database.tenant_middleware import set_tenant_context

async def my_endpoint(session: AsyncSession):
    # Установить tenant context
    await set_tenant_context(session, tenant_id)

    # Все запросы будут фильтроваться по tenant_id
    bots = await session.execute(select(BotConfig))
```

---

## 🔧 API разработка

### Создание нового эндпоинта

1. Создать файл в `platform/api/`:

```python
# platform/api/bots.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from shared.database import get_session
from platform.models.tenant import BotConfig

router = APIRouter(prefix="/bots", tags=["Bots"])

@router.get("/")
async def list_bots(session: AsyncSession = Depends(get_session)):
    """Список ботов клиента"""
    # TODO: Установить tenant context
    # TODO: Получить список ботов
    return {"bots": []}
```

2. Подключить роутер в `platform/main.py`:

```python
from platform.api import bots

app.include_router(bots.router, prefix="/api/v1")
```

### Аутентификация

Для защищённых эндпоинтов используйте dependency `get_current_tenant`:

```python
from platform.api.auth import get_current_tenant
from platform.models.tenant import Tenant

@router.get("/profile")
async def get_profile(tenant: Tenant = Depends(get_current_tenant)):
    """Требует JWT токен"""
    return {"name": tenant.name}
```

### Тестирование API

```bash
# Регистрация
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "test@example.com"}'

# Ответ:
# {
#   "access_token": "eyJ...",
#   "tenant_id": "123e4567-...",
#   "tenant_slug": "test_user"
# }

# Получить профиль
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJ..."
```

---

## 🧪 Тестирование

### Unit тесты

```bash
# Запустить все тесты
pytest

# С coverage
pytest --cov=platform --cov-report=html

# Только unit тесты
pytest tests/unit/
```

### Пример теста:

```python
# tests/test_auth.py
import pytest
from httpx import AsyncClient
from platform.main import app

@pytest.mark.asyncio
async def test_register():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"name": "Test", "email": "test@example.com"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
```

---

## 🔐 Безопасность

### Переменные окружения

**НИКОГДА не коммитить .env файл!**

```bash
# Генерация SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

### HTTPS в продакшене

TODO: Настроить Nginx с Let's Encrypt

---

## 🚀 Деплой

### Development (локально)

```bash
python -m platform.main
```

### Production (VPS)

TODO: Создать docker-compose.yml и systemd service

---

## 📚 Полезные ресурсы

- [FastAPI документация](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 документация](https://docs.sqlalchemy.org/)
- [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [MAX Bot API](https://max.team/docs/bots)

---

## 🐛 Известные проблемы

- [ ] Telegram Mini App валидация не реализована
- [ ] Нет обработки ошибок БД
- [ ] Нет rate limiting
- [ ] Нет мониторинга

---

## 📝 TODO (Неделя 2)

- [ ] Bot Factory сервис
- [ ] Первый шаблон бота (Conversation Bot)
- [ ] Интеграция с MAX Bot API
- [ ] Endpoints для управления ботами

---

**Автор:** Claude Code
**Дата:** 4 февраля 2026
