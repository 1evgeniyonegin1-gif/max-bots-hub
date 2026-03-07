# Исправления безопасности MAX BOTS HUB

**Дата:** 4 февраля 2026
**Статус:** ✅ Все критические проблемы исправлены

## Что было сделано

### 1. ✅ Аутентификация с паролем

**Проблема:** Вход только по email
**Решение:** Добавлена проверка пароля с bcrypt хэшированием

**Изменённые файлы:**
- `platform/models/tenant.py` - поле password_hash
- `platform/api/auth.py` - валидация и проверка пароля

**Требования к паролю:**
- Минимум 8 символов
- Заглавная буква
- Строчная буква
- Цифра

### 2. ✅ Rate Limiting

**Проблема:** Нет защиты от DoS
**Решение:** Интегрирован slowapi

**Лимиты:**
- `/auth/register` - 3/мин
- `/auth/login` - 5/мин
- `/bots/create` - 10/мин
- `/webhook/*` - 100/мин

### 3. ✅ Хранение в БД

**Проблема:** Данные в памяти (теряются при перезапуске)
**Решение:** PostgreSQL с оптимизированными индексами

**Новые таблицы:**
- `conversation_messages` - история диалогов
- `generated_posts` - сгенерированный контент

**Автоочистка:**
- Диалоги старше 90 дней
- Отклонённые посты старше 30 дней

### 4. ✅ HTTPS редирект

**Проблема:** Нет принудительного HTTPS
**Решение:** `HTTPSRedirectMiddleware` в production

### 5. ✅ Строгие CORS

**Проблема:** Разрешены любые домены (`["*"]`)
**Решение:** Только доверенные домены

**Production:**
- `https://max-bots-hub.ru`
- `https://app.max-bots-hub.ru`

**Dev:**
- `http://localhost:3000`
- `http://localhost:5173`

### 6. ✅ Безопасное логирование

**Проблема:** Персональные данные в логах
**Решение:** Только метаданные в production

## Как применить

### 1. Обновить код

```bash
cd max-bots-hub
git pull
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

Проверить что установлены:
- `passlib[bcrypt]`
- `slowapi`

### 3. Применить миграцию

```bash
# Локально
psql -U postgres -d max_bots_hub -f migrations/versions/002_security_improvements.sql

# На сервере
ssh user@server
psql -U nlbot -d nl_international -f /path/to/002_security_improvements.sql
```

### 4. Обновить .env

Добавить переменные если их нет:

```env
# Безопасность
DEBUG=False
SECRET_KEY=your-strong-secret-key-change-this

# CORS (опционально, по умолчанию берётся из settings.py)
# CORS_ORIGINS=https://max-bots-hub.ru,https://app.max-bots-hub.ru
```

### 5. Перезапустить приложение

```bash
# Если через systemd
sudo systemctl restart max-bots-hub

# Или напрямую
python run_server.py
```

## Проверка работоспособности

### 1. Проверить таблицы

```sql
-- Подключиться к БД
psql -U postgres -d max_bots_hub

-- Проверить новые таблицы
\dt conversation_messages
\dt generated_posts

-- Проверить поле password_hash
\d tenants
```

### 2. Проверить аутентификацию

```bash
# Попробовать зарегистрироваться (должно требовать пароль)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "test@example.com", "password": "Test1234"}'

# Попробовать войти
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test1234"}'
```

### 3. Проверить rate limiting

```bash
# Попробовать 6 раз войти за минуту (должен вернуть 429 после 5-го)
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "wrong"}'
  echo ""
done
```

### 4. Проверить HTTPS redirect

```bash
# В production должен редиректить на HTTPS
curl -I http://your-domain.com
# Должен вернуть 307 Temporary Redirect
```

## Откат (если что-то пошло не так)

```sql
-- Откатить миграцию (раскомментировать в файле 002_security_improvements.sql)
DROP TABLE IF EXISTS conversation_messages CASCADE;
DROP TABLE IF EXISTS generated_posts CASCADE;
ALTER TABLE tenants DROP COLUMN IF EXISTS password_hash;
```

## Что дальше

### Обязательно перед production:
- [x] Применить все миграции
- [x] Установить сильный SECRET_KEY
- [x] Настроить CORS для своего домена
- [ ] Настроить backup БД
- [ ] Настроить мониторинг

### Рекомендуется:
- [ ] Добавить 2FA для админов
- [ ] Настроить Sentry для ошибок
- [ ] Добавить security headers
- [ ] Написать privacy policy

## Поддержка

Если возникли проблемы:
1. Проверьте логи: `journalctl -u max-bots-hub -n 100`
2. Проверьте БД: подключение и наличие таблиц
3. Проверьте .env: все нужные переменные заданы

## Changelog

**4 февраля 2026:**
- ✅ Добавлена аутентификация с паролем
- ✅ Добавлен rate limiting
- ✅ Перенесены данные в БД
- ✅ Добавлен HTTPS redirect
- ✅ Настроены строгие CORS
- ✅ Исправлено логирование
