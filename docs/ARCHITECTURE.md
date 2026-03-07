# Архитектура MAX BOTS HUB

**Дата:** 4 февраля 2026
**Статус:** Draft v0.1

---

## 📊 Обзор

MAX BOTS HUB — мультитенантная SaaS-платформа для создания ботов в MAX мессенджере.

### Ключевые принципы
1. **Мультитенантность** — один сервер, много изолированных клиентов
2. **Row-Level Security (RLS)** — изоляция данных на уровне PostgreSQL
3. **Bot Templates** — готовые шаблоны ботов, легко настраиваемые
4. **API-First** — вся логика через REST API (FastAPI)

---

## 🏗️ Компоненты системы

### 1. Platform Core (Ядро платформы)

**Назначение:** Управление тенантами, ботами, подписками

**Технологии:**
- FastAPI
- SQLAlchemy 2.0 (async)
- PostgreSQL + pgvector
- Alembic (миграции)

**Модули:**
```
platform/
├── api/
│   ├── auth.py          # JWT аутентификация
│   ├── tenants.py       # CRUD для тенантов
│   ├── bots.py          # CRUD для ботов
│   ├── billing.py       # Подписки, оплата
│   └── analytics.py     # Метрики
├── services/
│   ├── bot_factory.py   # Создание ботов из шаблонов
│   ├── tenant_service.py
│   └── billing_service.py
├── models/
│   ├── tenant.py        # Tenant, BotConfig, Subscription
│   └── usage_stats.py
└── bot_engine/
    ├── dispatcher.py    # Роутинг по tenant_id
    └── tenant_context.py
```

---

### 2. Bot Templates (Шаблоны ботов)

**Назначение:** Переиспользуемые шаблоны для разных типов ботов

**10 типов ботов:**
1. **Conversation Bot** — диалоговый бот (из curator_bot)
2. **Content Generator** — генератор контента (из content_manager_bot)
3. **Gosuslugi Bot** — интеграция с Госуслугами
4. **Business Assistant** — бизнес-ассистент + СБП
5. **Marketplace Bot** — витрина товаров/услуг
6. **Education Bot** — онлайн-курсы
7. **Real Estate Bot** — недвижимость
8. **Taxi/Delivery Bot** — такси/доставка
9. **Entertainment Bot** — гороскопы, квизы
10. **Medical Bot** — запись к врачу

**Структура шаблона:**
```python
bot_templates/conversation_bot/
├── handlers.py          # Обработчики сообщений
├── chat_engine.py       # AI движок
├── prompts.py           # Промпты (customizable)
└── config_schema.yaml   # Что можно настроить
```

**config_schema.yaml:**
```yaml
type: conversation_bot
version: 1.0

customizable_fields:
  - name: greeting
    label: "Приветственное сообщение"
    type: text
    default: "Привет! Чем могу помочь?"

  - name: persona
    label: "Стиль общения"
    type: select
    options:
      - friendly: "Дружелюбный"
      - professional: "Профессиональный"
    default: friendly
```

---

### 3. Shared Code (Общий код)

**Назначение:** Переиспользуемый код из APEXFLOW

**Компоненты:**
```
shared/
├── config/
│   └── settings.py      # Pydantic settings
├── database/
│   ├── base.py          # AsyncSession
│   ├── models.py        # Base модели
│   └── tenant_middleware.py  # RLS
├── ai_clients/
│   ├── anthropic_client.py   # Claude
│   ├── deepseek_client.py    # Deepseek
│   └── yandexgpt_client.py   # YandexGPT
└── rag/
    ├── rag_engine.py
    ├── vector_store.py
    └── embeddings.py
```

---

### 4. Frontend (Клиентские приложения)

**Два дашборда:**

**A. Client Dashboard** — для клиентов платформы
```tsx
frontend/client-dashboard/
├── src/
│   ├── pages/
│   │   ├── Dashboard.tsx      # Главная
│   │   ├── BotSelector.tsx    # Выбор типа бота
│   │   ├── BotCustomizer.tsx  # Конструктор
│   │   ├── Analytics.tsx      # Статистика
│   │   └── Billing.tsx        # Оплата
│   ├── components/
│   │   ├── BotPreview.tsx     # Предпросмотр
│   │   └── ConfigForm.tsx     # Форма настройки
│   └── api/
│       └── client.ts          # axios
└── package.json
```

**B. Admin Dashboard** — для управления платформой
```tsx
frontend/admin-dashboard/
├── src/
│   ├── pages/
│   │   ├── Tenants.tsx    # Список клиентов
│   │   ├── Revenue.tsx    # Доходы
│   │   └── Stats.tsx      # Статистика
│   └── ...
```

---

## 🗄️ База данных

### Схема БД

```sql
-- Клиенты платформы
tenants
├── id (UUID, PK)
├── slug (VARCHAR, UNIQUE)
├── name (VARCHAR)
├── email (VARCHAR, UNIQUE)
├── status (ENUM: TRIAL, ACTIVE, PAUSED, BANNED)
└── config (JSONB)

-- Конфиги ботов
bot_configs
├── id (UUID, PK)
├── tenant_id (UUID, FK → tenants.id)
├── bot_type (VARCHAR)
├── bot_token (VARCHAR, UNIQUE)
├── config (JSONB)
└── status (ENUM: DRAFT, ACTIVE, PAUSED)

-- Подписки
subscriptions
├── id (UUID, PK)
├── tenant_id (UUID, FK → tenants.id)
├── plan (VARCHAR: start, business, pro)
├── status (ENUM: ACTIVE, PAUSED, CANCELLED)
├── started_at (TIMESTAMP)
└── expires_at (TIMESTAMP)

-- Статистика использования
usage_stats
├── id (UUID, PK)
├── tenant_id (UUID, FK → tenants.id)
├── bot_id (UUID, FK → bot_configs.id)
├── date (DATE)
├── messages_count (INT)
├── ai_api_calls (INT)
└── active_users (INT)

-- Все таблицы из APEXFLOW + tenant_id:
users + tenant_id
conversation_messages + tenant_id
posts + tenant_id
media_assets + tenant_id
...
```

### Row-Level Security (RLS)

Автоматическая фильтрация по `tenant_id`:

```sql
-- Включаем RLS
ALTER TABLE bot_configs ENABLE ROW LEVEL SECURITY;

-- Политика изоляции
CREATE POLICY tenant_isolation ON bot_configs
  USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

**Middleware для установки контекста:**
```python
async def set_tenant_context(session: Session, tenant_id: str):
    await session.execute(f"SET app.tenant_id = '{tenant_id}'")
```

---

## 🔄 Поток данных

### 1. Создание бота клиентом

```
Клиент → Frontend (BotCustomizer)
    ↓
POST /bots/create {bot_type, config}
    ↓
BotFactory.create_bot()
    ↓
1. Зарегистрировать в MAX (@MasterBot API)
2. Сохранить в БД (bot_configs)
3. Инициализировать обработчик
4. Зарегистрировать в MultiTenantDispatcher
    ↓
← bot_token, bot_username
```

### 2. Обработка сообщения в боте

```
Пользователь → MAX Webhook → /webhook/{bot_token}
    ↓
MultiTenantDispatcher.handle_update()
    ↓
1. Получить tenant_id по bot_token
2. Установить контекст: set_tenant_context(tenant_id)
3. Найти handler по bot_token
    ↓
handler.process_message()
    ↓
1. Получить контекст диалога (с tenant_id фильтром)
2. RAG поиск (с tenant_id фильтром)
3. Генерация ответа через AI
4. Отправить ответ
5. Сохранить в БД (с tenant_id)
```

---

## 🔐 Безопасность

### 1. Изоляция данных
- **RLS на уровне PostgreSQL**
- **Tenant ID в каждой таблице**
- **Автоматическая фильтрация через middleware**

### 2. Аутентификация
- **JWT токены** (7 дней)
- **Telegram Mini App initData** валидация
- **HTTPS only**

### 3. Авторизация
- **Role-Based Access Control (RBAC)**
  - Admin — управление платформой
  - Tenant — управление своими ботами
  - User — пользователь бота

---

## ⚡ Производительность

### Масштабируемость
- **Горизонтальное масштабирование** — запуск нескольких инстансов FastAPI
- **Load Balancer** — Nginx для распределения нагрузки
- **Connection Pooling** — SQLAlchemy pool_size=20

### Кеширование
- **Redis** — для сессий и частых запросов
- **React Query** — на фронтенде

### Оптимизация БД
- **Индексы** на tenant_id, bot_token, status
- **Партиционирование** usage_stats по дате
- **pgvector** для быстрого RAG поиска

---

## 🚀 API Endpoints

### Authentication
```
POST   /auth/register       # Регистрация клиента
POST   /auth/login          # Вход (JWT)
GET    /auth/me             # Текущий пользователь
```

### Tenants (Admin only)
```
GET    /tenants             # Список тенантов
POST   /tenants             # Создать тенанта
GET    /tenants/{id}        # Получить тенанта
PATCH  /tenants/{id}        # Обновить тенанта
```

### Bots
```
GET    /bots/templates      # Список шаблонов (10 типов)
POST   /bots/create         # Создать бота из шаблона
GET    /bots                # Список ботов клиента
GET    /bots/{id}           # Получить бота
PATCH  /bots/{id}/config    # Обновить конфиг
POST   /bots/{id}/deploy    # Задеплоить изменения
DELETE /bots/{id}           # Удалить бота
```

### Analytics
```
GET    /analytics/overview      # Общая статистика
GET    /analytics/bots/{id}     # Статистика по боту
```

### Billing
```
POST   /billing/subscribe   # Подписаться на тариф
POST   /billing/payment     # Оплата (СБП)
GET    /billing/invoices    # История платежей
```

---

## 📦 Деплой

### Окружения
1. **Development** — локальная разработка
2. **Staging** — тестовый сервер
3. **Production** — боевой сервер (VPS)

### Docker Compose
```yaml
services:
  platform:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
```

---

## 📊 Мониторинг

### Метрики
- **Tenants count** — количество клиентов
- **Bots count** — количество ботов
- **Messages per day** — сообщений в день
- **AI API calls** — вызовов AI
- **Revenue** — доход

### Алерты
- CPU > 80%
- Memory > 85%
- DB connections > 90%
- API latency > 2s
- Ошибки > 5% requests

---

## 🔄 Обновления архитектуры

| Дата | Версия | Изменения |
|------|--------|-----------|
| 04.02.2026 | v0.1 | Первая версия архитектуры |

---

**Автор:** Claude Code
**Дата:** 4 февраля 2026
