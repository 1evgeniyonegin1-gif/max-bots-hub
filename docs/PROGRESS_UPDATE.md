# Прогресс разработки MAX BOTS HUB

**Дата:** 4 февраля 2026
**Сессия:** Продолжение Недели 2

---

## ✅ Что сделано сегодня

### 1. Bot Factory Service

Создан сервис для генерации ботов из шаблонов:

**[platform/services/bot_factory.py](../platform/services/bot_factory.py)**

Ключевые компоненты:
- `BotTemplate` — базовый класс для шаблонов
- `BotFactory` — фабрика с реестром шаблонов
- `ConversationBotTemplate` — первый шаблон (диалоговый бот)

**Возможности:**
- ✅ Регистрация шаблонов через `register_template()`
- ✅ Валидация конфигурации клиента
- ✅ Дефолтные значения для каждого шаблона
- ✅ Callback `on_create()` для инициализации
- ✅ Создание бота с автоматической регистрацией в MAX
- ✅ Обновление конфигурации бота
- ✅ Деплой бота (DRAFT → ACTIVE)
- ✅ Soft delete ботов

**Методы:**
```python
factory = BotFactory(session)

# Создать бота
bot_config = await factory.create_bot(
    tenant_id="123-456",
    bot_type="conversation",
    config={"bot_name": "My Bot", "greeting": "Hi!"}
)

# Обновить конфиг
bot_config = await factory.update_bot_config(
    bot_id="789",
    config={"greeting": "Hello!"}
)

# Задеплоить
bot_config = await factory.deploy_bot(bot_id="789")

# Удалить
await factory.delete_bot(bot_id="789")
```

---

### 2. MAX API Client

Создан клиент для интеграции с MAX Bot API:

**[platform/services/max_api_client.py](../platform/services/max_api_client.py)**

**Два режима:**

1. **MAXAPIClient** — реальный клиент для MAX API
   - Требует `MAX_MASTER_BOT_TOKEN` в .env
   - HTTP клиент на httpx
   - Методы: `create_bot()`, `set_webhook()`, `delete_bot()`

2. **MockMAXAPIClient** — mock для разработки
   - Не требует токен
   - Генерирует fake bot_token и username
   - Используется автоматически если токена нет

**Методы:**
```python
client = MAXAPIClient()  # или MockMAXAPIClient()

# Создать бота
bot_data = await client.create_bot(
    bot_name="My Bot",
    description="...",
    tenant_id="123"
)
# -> {"token": "...", "username": "@my_bot", "id": "..."}

# Установить webhook
await client.set_webhook(
    bot_token="...",
    webhook_url="https://your-domain.com/webhook/..."
)

# Получить инфо
info = await client.get_bot_info(bot_token="...")

# Удалить
await client.delete_bot(bot_token="...")
```

**Автоматический выбор:**
Bot Factory автоматически использует:
- `MAXAPIClient` — если в .env есть валидный `MAX_MASTER_BOT_TOKEN`
- `MockMAXAPIClient` — если токена нет (для dev/тестирования)

---

### 3. Bots API Endpoints

Создан полный REST API для управления ботами:

**[platform/api/bots.py](../platform/api/bots.py)**

| Метод | Путь | Описание | Статус |
|-------|------|----------|--------|
| GET | `/api/v1/bots/templates` | Список шаблонов | ✅ |
| POST | `/api/v1/bots/create` | Создать бота | ✅ |
| GET | `/api/v1/bots` | Список ботов клиента | ✅ |
| GET | `/api/v1/bots/{id}` | Получить бота | ✅ |
| PATCH | `/api/v1/bots/{id}/config` | Обновить конфиг | ✅ |
| POST | `/api/v1/bots/{id}/deploy` | Задеплоить | ✅ |
| DELETE | `/api/v1/bots/{id}` | Удалить | ✅ |

**Все endpoints:**
- ✅ Требуют JWT токен (аутентификация)
- ✅ Автоматическая изоляция по tenant_id (RLS)
- ✅ Валидация входных данных (Pydantic)
- ✅ Обработка ошибок (400, 401, 404, 500)

---

## 🧪 Как тестировать

### 1. Получить список шаблонов

```bash
curl http://localhost:8000/api/v1/bots/templates
```

Ответ:
```json
[
  {
    "type": "conversation",
    "name": "Диалоговый бот",
    "description": "AI-бот для диалогов с пользователями...",
    "config_schema": {
      "fields": [
        {
          "name": "bot_name",
          "label": "Название бота",
          "type": "text",
          "required": true
        },
        {
          "name": "greeting",
          "label": "Приветственное сообщение",
          "type": "textarea",
          "default": "Привет! Чем могу помочь?"
        },
        {
          "name": "persona",
          "label": "Стиль общения",
          "type": "select",
          "options": [
            {"value": "friendly", "label": "Дружелюбный"},
            {"value": "professional", "label": "Профессиональный"},
            {"value": "funny", "label": "Весёлый"}
          ],
          "default": "friendly"
        }
      ]
    }
  }
]
```

### 2. Создать бота

```bash
# Сначала зарегистрироваться и получить токен
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "test@example.com"}'

# Ответ: {"access_token": "eyJ...", "tenant_id": "..."}

# Создать бота
curl -X POST http://localhost:8000/api/v1/bots/create \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "bot_type": "conversation",
    "config": {
      "bot_name": "My First Bot",
      "greeting": "Hello!",
      "persona": "friendly"
    }
  }'
```

Ответ:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "bot_type": "conversation",
  "bot_name": "My First Bot",
  "bot_username": "@myfirstbot_bot",
  "status": "DRAFT",
  "config": {
    "bot_name": "My First Bot",
    "greeting": "Hello!",
    "persona": "friendly",
    "max_conversation_length": 10,
    "enable_rag": true
  },
  "created_at": "2026-02-04T12:00:00"
}
```

### 3. Получить список ботов

```bash
curl http://localhost:8000/api/v1/bots \
  -H "Authorization: Bearer eyJ..."
```

### 4. Обновить конфиг

```bash
curl -X PATCH http://localhost:8000/api/v1/bots/{bot_id}/config \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"config": {"greeting": "New greeting!"}}'
```

### 5. Задеплоить

```bash
curl -X POST http://localhost:8000/api/v1/bots/{bot_id}/deploy \
  -H "Authorization: Bearer eyJ..."
```

### 6. Удалить

```bash
curl -X DELETE http://localhost:8000/api/v1/bots/{bot_id} \
  -H "Authorization: Bearer eyJ..."
```

---

## 📊 Статистика

**Файлы созданы:** 3
- `platform/services/bot_factory.py` (~400 строк)
- `platform/services/max_api_client.py` (~250 строк)
- `platform/api/bots.py` (~300 строк)

**Новые endpoints:** 7
**Новые классы:** 4 (BotTemplate, BotFactory, MAXAPIClient, MockMAXAPIClient)

---

## 🎯 Текущий статус

### ✅ Готово

**Неделя 1:**
- [x] База данных (мультитенантность, RLS)
- [x] SQLAlchemy модели
- [x] Tenant middleware
- [x] JWT аутентификация
- [x] FastAPI приложение

**Неделя 2 (частично):**
- [x] Bot Factory сервис
- [x] MAX API client (с mock режимом)
- [x] API endpoints для ботов (/bots/*)
- [x] Первый шаблон (ConversationBotTemplate)

### ⏳ В процессе

- [ ] Адаптация curator_bot из APEXFLOW
- [ ] MultiTenantDispatcher для обработки сообщений
- [ ] Webhook handler для MAX ботов

### 📋 Следующие шаги

**Приоритет 1: Bot Engine (Dispatcher)**
- Создать `platform/bot_engine/dispatcher.py`
- MultiTenantDispatcher для роутинга сообщений
- Регистрация handler'ов по bot_token

**Приоритет 2: Conversation Bot Handler**
- Адаптировать `curator_bot` из APEXFLOW
- Создать `bot_templates/conversation_bot/handlers.py`
- Интеграция с Claude/Deepseek

**Приоритет 3: Webhook**
- Endpoint `/webhook/{bot_token}` для приёма сообщений
- Интеграция с MultiTenantDispatcher

---

## 🧪 Swagger UI

Откройте http://localhost:8000/docs для тестирования API в браузере!

Все новые endpoints доступны в Swagger:
- Bots (7 endpoints)
- Authentication (4 endpoints)

---

## 📝 Заметки

### Bot Factory Pattern

Реализован классический паттерн фабрики:
1. Клиент выбирает тип бота (из списка шаблонов)
2. Заполняет config (по схеме шаблона)
3. Фабрика создаёт экземпляр бота
4. Бот регистрируется в MAX и сохраняется в БД

### Config Schema

Каждый шаблон определяет схему:
```python
{
  "fields": [
    {
      "name": "field_name",
      "label": "Display Name",
      "type": "text|textarea|select|file",
      "required": true|false,
      "default": "...",
      "options": [...]  # для select
    }
  ],
  "integrations": [...]
}
```

Эта схема используется:
- Frontend'ом для генерации формы настройки
- Backend'ом для валидации

### Mock vs Real MAX API

**Development:**
- Не нужен доступ к MAX API
- Используется MockMAXAPIClient
- Генерируются fake bot_token

**Production:**
- Требуется MAX_MASTER_BOT_TOKEN в .env
- Используется MAXAPIClient
- Реальная регистрация в MAX

---

## 🎉 Итог

**Неделя 2 (частичная) завершена!**

Создана система для:
- ✅ Регистрации ботов из шаблонов
- ✅ Управления ботами через REST API
- ✅ Интеграции с MAX API (с mock режимом)
- ✅ Конфигурирования ботов клиентами

**Следующий шаг:** Bot Engine для обработки сообщений 🚀

---

**Автор:** Claude Code
**Дата:** 4 февраля 2026
