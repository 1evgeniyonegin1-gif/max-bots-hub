# Database Migrations

Миграции базы данных для MAX BOTS HUB.

## Порядок применения миграций

1. `001_add_multitenancy.sql` - Базовая структура мультитенантности
2. `002_security_improvements.sql` - Улучшения безопасности (пароли, история диалогов, посты)

## Как применить миграции

### Локально (PostgreSQL)

```bash
# Подключаемся к БД
psql -U postgres -d max_bots_hub

# Применяем миграции по порядку
\i migrations/versions/001_add_multitenancy.sql
\i migrations/versions/002_security_improvements.sql
```

### На production сервере

```bash
# SSH подключение
ssh user@server

# Применяем миграции
psql -U nlbot -d nl_international -f /path/to/002_security_improvements.sql
```

## Откат миграций

Каждая миграция содержит секцию ROLLBACK с командами для отката. Раскомментируйте и выполните нужные команды.

## Проверка применённых миграций

```sql
-- Проверить наличие таблиц
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';

-- Проверить наличие поля password_hash
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'tenants';
```

## Содержание миграций

### 002_security_improvements.sql

**Изменения:**

1. Добавлено поле `password_hash` в таблицу `tenants`
2. Создана таблица `conversation_messages` для истории диалогов
3. Создана таблица `generated_posts` для сгенерированного контента
4. Добавлены индексы для оптимизации запросов
5. Созданы функции очистки старых данных
6. Добавлены views для статистики

**Зачем:**

- Безопасная аутентификация с паролями
- Сохранение истории диалогов в БД (вместо памяти)
- Надёжное хранение постов с модерацией
- Защита от утечки памяти
- Возможность масштабирования

**Влияние на производительность:**

- Минимальное (добавлены оптимизированные индексы)
- Автоматическая очистка старых данных предотвращает разрастание таблиц

## Полезные запросы

```sql
-- Посмотреть количество сообщений по ботам
SELECT bot_id, COUNT(*)
FROM conversation_messages
GROUP BY bot_id;

-- Посмотреть статистику постов
SELECT status, COUNT(*)
FROM generated_posts
GROUP BY status;

-- Очистка старых данных
SELECT cleanup_old_conversations();
SELECT cleanup_rejected_posts();
```
