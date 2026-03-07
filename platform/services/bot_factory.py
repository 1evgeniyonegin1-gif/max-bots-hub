"""
Bot Factory Service
Фабрика для создания ботов из шаблонов
"""
import uuid
from typing import Dict, Any, Optional, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from platform.models.tenant import BotConfig, BotStatus, Tenant
from platform.services.max_api_client import MAXAPIClient, MockMAXAPIClient
from shared.config.settings import settings


class BotTemplate:
    """
    Базовый класс для шаблонов ботов

    Каждый тип бота наследуется от этого класса и реализует:
    - config_schema: схема настройки (что можно кастомизировать)
    - validate_config: валидация конфига клиента
    - get_default_config: дефолтные значения
    """

    bot_type: str = "base"
    display_name: str = "Base Bot"
    description: str = "Base bot template"

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Возвращает схему конфигурации бота

        Returns:
            Dict с полями для кастомизации
        """
        return {
            "fields": [],
            "integrations": []
        }

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> bool:
        """
        Валидация конфигурации клиента

        Args:
            config: Конфиг от клиента

        Returns:
            True если валидный

        Raises:
            ValueError: Если конфиг невалидный
        """
        return True

    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """
        Дефолтная конфигурация бота

        Returns:
            Dict с дефолтными значениями
        """
        return {}

    @classmethod
    def create_handler(cls, tenant_id: str, config: Dict[str, Any]):
        """
        Создать handler для этого типа бота

        ДОЛЖЕН быть переопределён в наследниках!

        Args:
            tenant_id: ID тенанта
            config: Конфигурация бота

        Returns:
            Handler instance (реализует BotHandler протокол)

        Raises:
            NotImplementedError: Если не переопределён
        """
        raise NotImplementedError(
            f"{cls.__name__} must implement create_handler() method"
        )

    @classmethod
    async def on_create(cls, bot_config: BotConfig, session: AsyncSession) -> None:
        """
        Callback после создания бота

        Используется для:
        - Инициализации данных
        - Создания webhook'ов
        - Отправки приветственных сообщений

        Args:
            bot_config: Созданный BotConfig
            session: Async session
        """
        pass


class BotFactory:
    """
    Фабрика для создания ботов из шаблонов

    Usage:
        factory = BotFactory(session)
        bot_config = await factory.create_bot(
            tenant_id="123-456",
            bot_type="conversation",
            config={
                "bot_name": "Мой Бот",
                "greeting": "Привет!",
                "persona": "friendly"
            }
        )
    """

    # Реестр доступных шаблонов
    _templates: Dict[str, Type[BotTemplate]] = {}

    def __init__(self, session: AsyncSession):
        self.session = session
        # Используем Mock client пока нет доступа к MAX API
        if settings.MAX_MASTER_BOT_TOKEN and settings.MAX_MASTER_BOT_TOKEN != "your_master_bot_token_from_@MasterBot":
            self.max_client = MAXAPIClient()
        else:
            self.max_client = MockMAXAPIClient()

    @classmethod
    def register_template(cls, template_class: Type[BotTemplate]) -> None:
        """
        Зарегистрировать новый шаблон бота

        Args:
            template_class: Класс шаблона (наследник BotTemplate)
        """
        cls._templates[template_class.bot_type] = template_class

    @classmethod
    def get_available_templates(cls) -> Dict[str, Dict[str, Any]]:
        """
        Получить список доступных шаблонов

        Returns:
            Dict с информацией о шаблонах
        """
        return {
            bot_type: {
                "type": template.bot_type,
                "name": template.display_name,
                "description": template.description,
                "config_schema": template.get_config_schema()
            }
            for bot_type, template in cls._templates.items()
        }

    @classmethod
    def get_template(cls, bot_type: str) -> Optional[Type[BotTemplate]]:
        """
        Получить класс шаблона по типу

        Args:
            bot_type: Тип бота ("conversation", "content_generator" и т.д.)

        Returns:
            Класс шаблона или None
        """
        return cls._templates.get(bot_type)

    async def create_bot(
        self,
        tenant_id: str,
        bot_type: str,
        config: Dict[str, Any]
    ) -> BotConfig:
        """
        Создать бота из шаблона

        Процесс:
        1. Валидация tenant_id и bot_type
        2. Валидация конфига
        3. Регистрация в MAX через @MasterBot API
        4. Сохранение в БД
        5. Инициализация обработчиков
        6. Регистрация в MultiTenantDispatcher

        Args:
            tenant_id: UUID тенанта
            bot_type: Тип бота
            config: Конфигурация бота

        Returns:
            Созданный BotConfig

        Raises:
            ValueError: Если tenant_id или bot_type невалидный
            RuntimeError: Если ошибка регистрации в MAX
        """
        # 1. Проверяем тенанта
        result = await self.session.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # 2. Проверяем тип бота
        template_class = self.get_template(bot_type)
        if not template_class:
            raise ValueError(
                f"Unknown bot type: {bot_type}. "
                f"Available: {', '.join(self._templates.keys())}"
            )

        # 3. Валидация конфига
        template_class.validate_config(config)

        # 4. Объединяем с дефолтными значениями
        full_config = {
            **template_class.get_default_config(),
            **config
        }

        bot_name = full_config.get("bot_name", f"{tenant.slug}_bot")

        # 5. Регистрация в MAX (@MasterBot API)
        try:
            max_bot_data = await self.max_client.create_bot(
                bot_name=bot_name,
                description=full_config.get("description", ""),
                tenant_id=tenant_id
            )

            bot_token = max_bot_data["token"]
            bot_username = max_bot_data["username"]

        except Exception as e:
            raise RuntimeError(f"Failed to register bot in MAX: {str(e)}")

        # 6. Сохранение в БД
        bot_config = BotConfig(
            tenant_id=uuid.UUID(tenant_id),
            bot_type=bot_type,
            bot_name=bot_name,
            bot_token=bot_token,
            bot_username=bot_username,
            config=full_config,
            status=BotStatus.DRAFT  # Начинаем с DRAFT
        )

        self.session.add(bot_config)
        await self.session.commit()
        await self.session.refresh(bot_config)

        # 7. Callback после создания (инициализация)
        await template_class.on_create(bot_config, self.session)

        # 8. TODO: Зарегистрировать в MultiTenantDispatcher
        # from platform.bot_engine.dispatcher import register_bot
        # await register_bot(bot_token, handler)

        return bot_config

    async def deploy_bot(self, bot_id: str) -> BotConfig:
        """
        Задеплоить бота (перевести из DRAFT в ACTIVE)

        Args:
            bot_id: UUID бота

        Returns:
            Обновлённый BotConfig
        """
        result = await self.session.execute(
            select(BotConfig).where(BotConfig.id == uuid.UUID(bot_id))
        )
        bot_config = result.scalar_one_or_none()

        if not bot_config:
            raise ValueError(f"Bot {bot_id} not found")

        # TODO: Настроить webhook в MAX
        # await self.max_client.set_webhook(
        #     bot_token=bot_config.bot_token,
        #     url=f"https://your-domain.com/webhook/{bot_config.bot_token}"
        # )

        # Активируем
        bot_config.status = BotStatus.ACTIVE
        await self.session.commit()
        await self.session.refresh(bot_config)

        return bot_config

    async def update_bot_config(
        self,
        bot_id: str,
        config: Dict[str, Any]
    ) -> BotConfig:
        """
        Обновить конфигурацию бота

        Args:
            bot_id: UUID бота
            config: Новая конфигурация (частичная)

        Returns:
            Обновлённый BotConfig
        """
        result = await self.session.execute(
            select(BotConfig).where(BotConfig.id == uuid.UUID(bot_id))
        )
        bot_config = result.scalar_one_or_none()

        if not bot_config:
            raise ValueError(f"Bot {bot_id} not found")

        # Получаем шаблон для валидации
        template_class = self.get_template(bot_config.bot_type)
        if not template_class:
            raise ValueError(f"Unknown bot type: {bot_config.bot_type}")

        # Объединяем старый и новый конфиг
        new_config = {**bot_config.config, **config}

        # Валидация
        template_class.validate_config(new_config)

        # Обновляем
        bot_config.config = new_config
        await self.session.commit()
        await self.session.refresh(bot_config)

        # TODO: Перезапустить обработчики бота

        return bot_config

    async def delete_bot(self, bot_id: str) -> None:
        """
        Удалить бота

        Args:
            bot_id: UUID бота
        """
        result = await self.session.execute(
            select(BotConfig).where(BotConfig.id == uuid.UUID(bot_id))
        )
        bot_config = result.scalar_one_or_none()

        if not bot_config:
            raise ValueError(f"Bot {bot_id} not found")

        # Помечаем как удалённый (soft delete)
        bot_config.status = BotStatus.DELETED
        await self.session.commit()

        # TODO: Удалить webhook из MAX
        # TODO: Отключить обработчики


# ============================================
# ПРИМЕР ШАБЛОНА
# ============================================

class ConversationBotTemplate(BotTemplate):
    """
    Шаблон диалогового бота (адаптация curator_bot из APEXFLOW)
    """

    bot_type = "conversation"
    display_name = "Диалоговый бот"
    description = "AI-бот для диалогов с пользователями, с RAG и персонализацией"

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "fields": [
                {
                    "name": "bot_name",
                    "label": "Название бота",
                    "type": "text",
                    "required": True,
                    "placeholder": "Мой Бот"
                },
                {
                    "name": "greeting",
                    "label": "Приветственное сообщение",
                    "type": "textarea",
                    "default": "Привет! Чем могу помочь?",
                    "required": False
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
                },
                {
                    "name": "ai_provider",
                    "label": "AI провайдер",
                    "type": "select",
                    "options": [
                        {"value": "claude", "label": "Claude (рекомендуется)"},
                        {"value": "deepseek", "label": "Deepseek (дешевле)"},
                        {"value": "yandexgpt", "label": "YandexGPT"}
                    ],
                    "default": "claude"
                }
            ],
            "integrations": [
                {
                    "id": "gosuslugi",
                    "name": "Интеграция с Госуслугами",
                    "description": "Доступ к данным через Госключ"
                },
                {
                    "id": "sbp",
                    "name": "СБП платежи",
                    "description": "Приём платежей через Систему быстрых платежей"
                }
            ]
        }

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> bool:
        if not config.get("bot_name"):
            raise ValueError("bot_name is required")

        persona = config.get("persona", "friendly")
        if persona not in ["friendly", "professional", "funny"]:
            raise ValueError(f"Invalid persona: {persona}")

        return True

    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        return {
            "greeting": "Привет! Чем могу помочь?",
            "persona": "friendly",
            "ai_provider": "claude",
            "max_conversation_length": 10,
            "enable_rag": True
        }

    @classmethod
    def create_handler(cls, tenant_id: str, config: Dict[str, Any]):
        """
        Создать handler для этого типа бота

        Args:
            tenant_id: ID тенанта
            config: Конфигурация бота

        Returns:
            Handler instance
        """
        from bot_templates.conversation_bot.handlers import ConversationBotHandler
        return ConversationBotHandler(tenant_id, config)

    @classmethod
    async def on_create(cls, bot_config: BotConfig, session: AsyncSession) -> None:
        """Инициализация после создания"""
        # Регистрируем handler в dispatcher
        from platform.bot_engine import dispatcher

        handler = cls.create_handler(
            tenant_id=str(bot_config.tenant_id),
            config=bot_config.config
        )

        await dispatcher.register_bot(
            bot_token=bot_config.bot_token,
            handler=handler,
            tenant_id=str(bot_config.tenant_id)
        )


# ============================================
# ШАБЛОН: Content Generator Bot
# ============================================

class ContentGeneratorBotTemplate(BotTemplate):
    """
    Шаблон бота для генерации контента
    Адаптация content_manager_bot из APEXFLOW
    """

    bot_type = "content_generator"
    display_name = "Контент-генератор"
    description = "AI-бот для генерации и публикации контента в соцсети"

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "fields": [
                {
                    "name": "bot_name",
                    "label": "Название бота",
                    "type": "text",
                    "required": True,
                    "placeholder": "Content Bot"
                },
                {
                    "name": "admin_ids",
                    "label": "ID администраторов",
                    "type": "text",
                    "required": True,
                    "placeholder": "123456789,987654321",
                    "description": "Telegram ID через запятую"
                },
                {
                    "name": "business_preset",
                    "label": "Бизнес-ниша",
                    "type": "select",
                    "options": [
                        {"value": "", "label": "Не выбрано"},
                        {"value": "ecommerce", "label": "E-commerce / Магазин"},
                        {"value": "services", "label": "Услуги / Консалтинг"},
                        {"value": "personal_brand", "label": "Личный бренд"},
                        {"value": "saas", "label": "SaaS / IT-продукт"},
                        {"value": "health_wellness", "label": "Здоровье / Wellness"},
                        {"value": "education", "label": "Образование / Курсы"}
                    ],
                    "default": ""
                },
                {
                    "name": "business_context",
                    "label": "Описание бизнеса",
                    "type": "textarea",
                    "required": False,
                    "placeholder": "Опишите ваш бизнес, продукты, целевую аудиторию...",
                    "description": "Если выбран пресет, можно оставить пустым"
                },
                {
                    "name": "persona",
                    "label": "Стиль контента",
                    "type": "select",
                    "options": [
                        {"value": "friend", "label": "Дружелюбный"},
                        {"value": "expert", "label": "Экспертный"},
                        {"value": "storyteller", "label": "Рассказчик"},
                        {"value": "mentor", "label": "Наставник"},
                        {"value": "energizer", "label": "Энергичный"}
                    ],
                    "default": "friend"
                },
                {
                    "name": "brand_voice",
                    "label": "Голос бренда",
                    "type": "textarea",
                    "required": False,
                    "placeholder": "Особенности стиля: тон, слова-маркеры, запрещённые темы..."
                },
                {
                    "name": "ai_provider",
                    "label": "AI провайдер",
                    "type": "select",
                    "options": [
                        {"value": "claude", "label": "Claude (рекомендуется)"},
                        {"value": "deepseek", "label": "Deepseek (дешевле)"},
                        {"value": "yandexgpt", "label": "YandexGPT"}
                    ],
                    "default": "claude"
                }
            ],
            "integrations": [
                {
                    "id": "telegram_channel",
                    "name": "Telegram канал",
                    "description": "Публикация постов в Telegram канал"
                },
                {
                    "id": "vk_group",
                    "name": "VK группа",
                    "description": "Публикация в VK (скоро)"
                }
            ]
        }

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> bool:
        if not config.get("bot_name"):
            raise ValueError("bot_name is required")

        if not config.get("admin_ids"):
            raise ValueError("admin_ids is required (Telegram user IDs)")

        persona = config.get("persona", "friend")
        valid_personas = ["friend", "expert", "storyteller", "mentor", "energizer"]
        if persona not in valid_personas:
            raise ValueError(f"Invalid persona: {persona}. Valid: {valid_personas}")

        return True

    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        return {
            "persona": "friend",
            "ai_provider": "claude",
            "business_preset": "",
            "business_context": "",
            "brand_voice": ""
        }

    @classmethod
    def create_handler(cls, tenant_id: str, config: Dict[str, Any]):
        """Создать handler"""
        from bot_templates.content_generator_bot.handlers import ContentGeneratorBotHandler

        # Преобразуем admin_ids из строки в список
        admin_ids = config.get("admin_ids", "")
        if isinstance(admin_ids, str):
            config["admin_ids"] = [aid.strip() for aid in admin_ids.split(",") if aid.strip()]

        return ContentGeneratorBotHandler(tenant_id, config)

    @classmethod
    async def on_create(cls, bot_config: BotConfig, session: AsyncSession) -> None:
        """Инициализация после создания"""
        from platform.bot_engine import dispatcher

        handler = cls.create_handler(
            tenant_id=str(bot_config.tenant_id),
            config=bot_config.config
        )

        await dispatcher.register_bot(
            bot_token=bot_config.bot_token,
            handler=handler,
            tenant_id=str(bot_config.tenant_id)
        )


# Регистрируем шаблоны
BotFactory.register_template(ConversationBotTemplate)
BotFactory.register_template(ContentGeneratorBotTemplate)
