# Changelog MAX BOTS HUB

Все значимые изменения в проекте будут документироваться в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).

---

## [0.1.0] - 2026-02-04

### ✨ Добавлено

**Инфраструктура:**
- Создана структура проекта MAX BOTS HUB
- Настроена Python виртуальная среда
- Добавлен .gitignore для Python, Node, IDE

**База данных:**
- SQL миграция для мультитенантности (001_add_multitenancy.sql)
- Таблицы: `tenants`, `bot_configs`, `subscriptions`, `usage_stats`
- Row-Level Security (RLS) для изоляции данных по tenant_id
- SQLAlchemy модели с Enum типами (TenantStatus, BotStatus, SubscriptionStatus)

**Backend:**
- FastAPI приложение с async/await
- JWT аутентификация (/auth/register, /auth/login, /auth/me)
- Tenant middleware для автоматической установки tenant_id
- Settings через pydantic-settings с .env файлом
- CORS middleware
- Global exception handler

**Документация:**
- README.md — обзор проекта и бизнес-модель
- ARCHITECTURE.md — детальная техническая архитектура
- DEVELOPMENT.md — руководство для разработчиков
- QUICKSTART.md — быстрый старт за 5 минут
- .env.example — пример переменных окружения

**Скрипты:**
- run_server.py — запуск FastAPI сервера

**Зависимости:**
- requirements.txt с основными пакетами:
  - FastAPI 0.109.0
  - SQLAlchemy 2.0.25
  - asyncpg 0.29.0
  - python-jose (JWT)
  - aiogram 3.3.0
  - anthropic, openai (AI провайдеры)

### 🔧 Изменено

- Нет изменений (первый релиз)

### 🐛 Исправлено

- Нет исправлений (первый релиз)

### 🗑️ Удалено

- Нет удалений (первый релиз)

### 📋 TODO (Неделя 2)

- [ ] Bot Factory сервис
- [ ] Первый шаблон бота (Conversation Bot из APEXFLOW)
- [ ] Интеграция с MAX Bot API (@MasterBot)
- [ ] API endpoints: /bots/create, /bots/list, /bots/{id}
- [ ] Frontend: React + Vite базовая структура

---

## [Unreleased]

### Планируется

**Неделя 2: Bot Factory**
- Bot Factory сервис для создания ботов из шаблонов
- Адаптация curator_bot → ConversationBotHandler
- config_schema.yaml для настройки ботов
- MAX Bot API интеграция

**Неделя 3: Frontend**
- Client Dashboard (React + Vite)
- BotSelector — выбор типа бота
- BotCustomizer — конструктор настройки
- BotPreview — предпросмотр

**Неделя 4: Деплой**
- Docker + docker-compose
- Nginx reverse proxy
- Let's Encrypt SSL
- Systemd сервисы
- CI/CD GitHub Actions

---

**Формат версий:** [MAJOR.MINOR.PATCH]
- MAJOR: Несовместимые изменения API
- MINOR: Новый функционал (обратно совместимо)
- PATCH: Исправления багов

**Статус проекта:** 🚧 В активной разработке (MVP)
