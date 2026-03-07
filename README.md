# MAX BOTS HUB

**Мультитенантная SaaS-платформа для создания ботов в MAX мессенджере**

## 📋 О проекте

MAX BOTS HUB — это платформа-конструктор ботов для MAX мессенджера (Bots as a Service). Предприниматели могут выбрать готовый тип бота, настроить его под себя и получить работающего бота за 5 минут.

**Статус:** ✅ MVP готов к тестированию!

**Дата начала:** 4 февраля 2026
**MVP завершён:** 4 февраля 2026 (за 1 день!)

---

## 🎯 Концепция

### Проблема
MAX мессенджер — молодая платформа с 50M+ пользователей, но **нет конструкторов ботов** для неё.

### Решение
Единая платформа, где можно:
1. Выбрать тип бота из 10 шаблонов (Госуслуги, Бизнес-ассистент, AI-консультант и др.)
2. Настроить под себя (тексты, стиль, интеграции)
3. Получить работающего бота за 5 минут
4. Платить подписку 299-2990 ₽/мес

### Монетизация
- **100 клиентов** = 100K ₽/мес
- **500 клиентов** = 500K ₽/мес
- **2000 клиентов** = 2M ₽/мес

---

## 🏗️ Архитектура

### Мультитенантность
Один сервер обслуживает множество клиентов с полной изоляцией данных:
```
MAX BOTS HUB (Platform)
├── Клиент 1 (tenant_id: xxx)
│   ├── Такси-бот
│   └── Их пользователи
├── Клиент 2 (tenant_id: yyy)
│   ├── Госуслуги-бот
│   └── Их пользователи
└── Клиент 3 (tenant_id: zzz)
    ├── Бизнес-ассистент
    └── Их пользователи
```

### Технологии
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL + pgvector
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui
- **AI:** Claude Sonnet 3.5, Deepseek, YandexGPT (fallback)
- **Боты:** aiogram 3.x, MAX Bot API

---

## 📁 Структура проекта

```
max-bots-hub/
├── docs/                    # Документация
│   ├── ARCHITECTURE.md      # Детальная архитектура
│   ├── DEVELOPMENT.md       # Гайд по разработке
│   ├── DEPLOYMENT.md        # Инструкции по деплою
│   └── API.md               # API документация
│
├── platform/                # Ядро платформы
│   ├── api/                # FastAPI endpoints
│   ├── services/           # Бизнес-логика
│   ├── models/             # SQLAlchemy модели
│   └── bot_engine/         # Единый движок для ботов
│
├── bot_templates/           # Шаблоны ботов
│   ├── conversation_bot/   # Диалоговый бот (AI + RAG)
│   ├── content_generator_bot/  # Генератор контента
│   └── ...                 # +8 типов (в планах)
│
├── shared/                  # Общий код (из APEXFLOW)
│   ├── config/             # Конфигурация
│   ├── database/           # База данных
│   ├── ai_clients/         # AI провайдеры
│   └── rag/                # RAG система
│
├── frontend/                # React приложения
│   ├── client-dashboard/   # Личный кабинет клиента
│   └── admin-dashboard/    # Админка платформы
│
├── migrations/              # Миграции БД
│   └── versions/           # SQL миграции
│
├── scripts/                 # Утилиты
├── tests/                   # Тесты
└── .env.example            # Пример переменных окружения
```

---

## 🚀 Быстрый старт

### Требования
- Python 3.11+
- PostgreSQL 15+
- Node.js 18+
- Git

### Установка

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd max-bots-hub

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить .env
cp .env.example .env
# Заполнить переменные окружения

# 5. Запустить миграции
psql -U postgres -d max_bots_hub -f migrations/versions/001_add_multitenancy.sql

# 6. Запустить сервер
python -m platform.main
```

---

## 📊 Прогресс разработки

### НЕДЕЛЯ 1: Database + Auth ✅ ЗАВЕРШЕНА
- [x] SQL миграция для мультитенантности
- [x] Модели SQLAlchemy (Tenant, BotConfig, Subscription, UsageStats)
- [x] Tenant middleware для изоляции данных (RLS)
- [x] API аутентификации (JWT + Telegram Mini App)
- [x] FastAPI приложение с middleware
- [x] Документация DEVELOPMENT.md

### НЕДЕЛЯ 2: Bot Factory ✅ ЗАВЕРШЕНА
- [x] Фабрика ботов (BotFactory service)
- [x] Первый шаблон (ConversationBotTemplate)
- [x] Интеграция с MAX Bot API (с mock режимом)
- [x] API endpoints (/bots/* - 7 эндпоинтов)
- [x] MultiTenantDispatcher для обработки сообщений
- [x] Webhook handler
- [x] ConversationBotHandler (AI диалоги)
- [x] AI clients (Claude, Deepseek, YandexGPT)

### MVP ГОТОВ! 🎉
**16 API endpoints, полный цикл работы ботов**

### ОБНОВЛЕНИЕ 4 февраля (вечер) ✅
- [x] **Content Generator Bot** — генерация контента для соцсетей
  - 8 типов постов (product, motivation, tips, news, promo, etc.)
  - 5 персон для стиля контента
  - 6 бизнес-пресетов (ecommerce, services, personal_brand, etc.)
  - Модерация (approve/reject/edit)
- [x] **Frontend MVP** — React Dashboard
  - Login/Register страницы
  - Dashboard со статистикой
  - Список ботов
  - Wizard создания бота
  - Страница настройки бота
- [x] **RAG система** — база знаний
  - EmbeddingService (sentence-transformers)
  - VectorStore (in-memory + pgvector ready)
  - RAGEngine (retrieval + augmentation)
  - API endpoints для управления знаниями
- [x] **Улучшенный Conversation Bot**
  - RAG интеграция
  - Поддержка inline кнопок
  - Дополнительные персоны (expert, mentor)
  - Команда /status
- [x] **Тестирование и аудит безопасности**
  - pytest тесты для всех handlers
  - Security audit report
  - Список уязвимостей и рекомендаций

### Итого: 2 шаблона ботов, Frontend, RAG, Тесты

### СЛЕДУЮЩИЕ ШАГИ:
- [ ] Аутентификация с паролем (КРИТИЧНО)
- [ ] Rate limiting
- [ ] Хранение данных в БД (вместо памяти)
- [ ] Деплой на VPS

---

## 📚 Документация

- [Архитектура](docs/ARCHITECTURE.md) — Детальное описание архитектуры
- [Разработка](docs/DEVELOPMENT.md) — Гайд для разработчиков
- [API](docs/API.md) — Документация API
- [Деплой](docs/DEPLOYMENT.md) — Инструкции по деплою
- [Аудит безопасности](docs/SECURITY_AUDIT.md) — Отчёт по безопасности

---

## 🔗 Связь с APEXFLOW

MAX BOTS HUB создан на основе проекта [APEXFLOW](../nl-international-ai-bots):
- ✅ Переиспользуем 70% кода (shared/, database/, ai_clients/)
- ✅ Опыт мультитенантности
- ✅ Готовые AI интеграции (Claude, Deepseek, YandexGPT)
- ✅ RAG система с pgvector

---

## 📈 Бизнес-модель

### Тарифы
- **Старт:** 299 ₽/мес (1 бот, до 100 пользователей)
- **Бизнес:** 990 ₽/мес (3 бота, до 1000 пользователей)
- **Про:** 2990 ₽/мес (безлимит ботов)
- **Корпорат:** от 10K ₽/мес (+ интеграции, поддержка)

### Прогноз (6 месяцев)
| Месяц | Клиенты | Доход | Баланс |
|-------|---------|-------|--------|
| 1 (MVP) | 0 | 0 | -10K ₽ |
| 2 (Тест) | 10-20 | 0 | -15K ₽ |
| 3 (Монетизация) | 20-50 | 20-50K ₽ | -30K до +5K ₽ |
| 6 (Масштабирование) | 150-200 | 150-200K ₽ | +40-90K ₽ |

---

## 📝 Лицензия

Proprietary — Все права защищены

---

## 👨‍💻 Команда

- **Продакт/Бизнес:** Вы
- **Разработка:** Claude Code (AI)

---

## 📮 Контакты

- Email: [ваш email]
- Telegram: [ваш telegram]

---

**🚀 Создано с помощью Claude Code**
