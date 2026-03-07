# 🚀 Быстрый старт MAX BOTS HUB

## ✅ Что реализовано

- Мультитенантность с RLS
- **Аутентификация с паролем (bcrypt)**
- **Rate limiting (защита от DoS)**
- **Хранение диалогов и постов в БД**
- **HTTPS редирект в production**
- JWT авторизация
- API: auth, bots, webhook, knowledge

---

## 🚀 Установка за 5 минут

### Шаг 1: Виртуальное окружение

```bash
cd "C:\Users\mafio\OneDrive\Документы\projects\max-bots-hub"

# Windows
python -m venv venv
venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

### Шаг 2: Создай БД PostgreSQL

**Вариант A: Через pgAdmin**
1. ПКМ на Databases → Create → Database
2. Name: `max_bots_hub`, Owner: `postgres`

**Вариант B: Docker**
```bash
docker run -d --name max-bots-postgres \
  -e POSTGRES_DB=max_bots_hub \
  -e POSTGRES_PASSWORD=твой_пароль \
  -p 5432:5432 \
  postgres:15
```

### Шаг 3: Примени миграции

```bash
# Через Python скрипт (рекомендуется)
python scripts/apply_migrations.py
```

Или вручную через psql:
```bash
psql -U postgres -d max_bots_hub -f migrations/versions/001_add_multitenancy.sql
psql -U postgres -d max_bots_hub -f migrations/versions/002_security_improvements.sql
```

### Шаг 4: Настрой .env

```bash
copy .env.example .env
```

**Обязательные поля:**
```env
DATABASE_URL=postgresql+asyncpg://postgres:твой_пароль@localhost:5432/max_bots_hub
SECRET_KEY=сгенерируй_ниже
DEBUG=true

# AI (минимум один)
ANTHROPIC_API_KEY=sk-ant-api03-xxx
```

**Сгенерируй SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Шаг 5: Запусти сервер

```bash
# Вариант 1
python -m platform.main

# Вариант 2 (с автоперезагрузкой)
uvicorn platform.main:app --reload --port 8000
```

Откроется: **http://localhost:8000**

---

## 🧪 Тестирование API

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Ответ:
```json
{
  "status": "healthy",
  "app": "MAX BOTS HUB",
  "version": "0.1.0"
}
```

### 2. Регистрация (теперь с паролем!)

```bash
curl -X POST http://localhost:8000/api/v1/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"name\": \"Test User\", \"email\": \"test@example.com\", \"password\": \"Test1234\"}"
```

**Требования к паролю:**
- Минимум 8 символов
- Заглавная буква
- Строчная буква
- Цифра

Ответ:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "tenant_slug": "test_user"
}
```

### 3. Логин (теперь с паролем!)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\": \"test@example.com\", \"password\": \"Test1234\"}"
```

### 4. Получить профиль

```bash
curl http://localhost:8000/api/v1/auth/me ^
  -H "Authorization: Bearer ВАШ_ТОКЕН"
```

---

## 📚 Документация API

Откройте в браузере:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 🗄️ Проверка БД

```sql
-- Подключиться к БД
psql -U postgres -d max_bots_hub

-- Проверить таблицы
\dt

-- Посмотреть тенантов
SELECT id, slug, name, email, status FROM tenants;

-- Проверить RLS
\d+ bot_configs
```

---

## ✅ Что дальше? (Неделя 2)

- [ ] **Bot Factory** — сервис для создания ботов из шаблонов
- [ ] **Первый шаблон бота** — Conversation Bot (адаптация из APEXFLOW)
- [ ] **MAX Bot API** — интеграция с @MasterBot
- [ ] **API endpoints** — /bots/create, /bots/list, /bots/{id}

---

## 🐛 Troubleshooting

### Ошибка подключения к БД

```
sqlalchemy.exc.OperationalError: could not connect to server
```

Решение:
1. Проверить что PostgreSQL запущен
2. Проверить DATABASE_URL в .env
3. Проверить пароль БД

### Ошибка миграции

```
ERROR: relation "tenants" already exists
```

Решение — удалить таблицы и применить заново:
```sql
DROP TABLE IF EXISTS usage_stats, bot_configs, subscriptions, tenants CASCADE;
```

Затем:
```bash
psql -U postgres -d max_bots_hub -f migrations/versions/001_add_multitenancy.sql
```

### JWT токен не валидный

Убедитесь что SECRET_KEY в .env совпадает при каждом запуске сервера.

---

## 📞 Контакты

Вопросы и предложения: создайте issue в репозитории

---

**🚀 Создано с помощью Claude Code**
**Дата:** 4 февраля 2026
