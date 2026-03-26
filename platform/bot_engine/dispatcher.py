"""
MultiTenant Dispatcher
Роутинг сообщений от MAX ботов к правильным handler'ам с изоляцией по tenant_id
"""
import logging
from typing import Dict, Any, Optional, Protocol
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.base import async_session_maker
from shared.database.tenant_middleware import set_tenant_context
from platform.models.tenant import BotConfig

logger = logging.getLogger(__name__)


class BotHandler(Protocol):
    """
    Протокол для handler'ов ботов

    Все handler'ы должны реализовывать этот интерфейс
    """

    async def handle_message(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Обработать входящее сообщение

        Args:
            message: Сообщение от MAX в формате:
            {
                "message_id": "...",
                "from": {"id": "...", "username": "..."},
                "chat": {"id": "...", "type": "private"},
                "text": "...",
                "date": 1234567890
            }

        Returns:
            Текст ответа или None
        """
        ...

    async def handle_callback(self, callback: Dict[str, Any]) -> Optional[str]:
        """
        Обработать callback query (нажатие кнопки)

        Args:
            callback: Callback query от MAX

        Returns:
            Текст ответа или None
        """
        ...


class MultiTenantDispatcher:
    """
    Единый диспетчер для всех ботов платформы

    Функции:
    1. Регистрация handler'ов по bot_token
    2. Роутинг входящих сообщений к правильному handler'у
    3. Автоматическая установка tenant context (RLS)
    4. Обработка ошибок и логирование

    Usage:
        # При создании бота
        await dispatcher.register_bot(bot_token, handler_instance)

        # При получении сообщения
        await dispatcher.handle_update(bot_token, update_data)
    """

    def __init__(self):
        # bot_token -> handler instance
        self._handlers: Dict[str, BotHandler] = {}

        # bot_token -> tenant_id (кеш для быстрого доступа)
        self._bot_tenant_map: Dict[str, str] = {}

        logger.info("MultiTenantDispatcher initialized")

    async def register_bot(
        self,
        bot_token: str,
        handler: BotHandler,
        tenant_id: str
    ) -> None:
        """
        Зарегистрировать handler для бота

        Args:
            bot_token: Токен бота в MAX
            handler: Экземпляр handler'а (реализует BotHandler протокол)
            tenant_id: ID тенанта

        Example:
            handler = ConversationBotHandler(tenant_id, config)
            await dispatcher.register_bot(bot_token, handler, tenant_id)
        """
        self._handlers[bot_token] = handler
        self._bot_tenant_map[bot_token] = tenant_id

        logger.info(
            f"Registered bot handler: bot_token={bot_token[:10]}..., "
            f"tenant_id={tenant_id}, handler={handler.__class__.__name__}"
        )

    async def unregister_bot(self, bot_token: str) -> None:
        """
        Отключить handler бота

        Args:
            bot_token: Токен бота
        """
        if bot_token in self._handlers:
            del self._handlers[bot_token]
            del self._bot_tenant_map[bot_token]
            logger.info(f"Unregistered bot: bot_token={bot_token[:10]}...")

    def is_registered(self, bot_token: str) -> bool:
        """
        Проверить зарегистрирован ли бот

        Args:
            bot_token: Токен бота

        Returns:
            True если зарегистрирован
        """
        return bot_token in self._handlers

    async def handle_update(
        self,
        bot_token: str,
        update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Обработать входящее обновление от MAX

        Процесс:
        1. Получить tenant_id по bot_token
        2. Установить tenant context (RLS)
        3. Найти handler
        4. Обработать сообщение
        5. Вернуть результат

        Args:
            bot_token: Токен бота
            update: Данные от MAX в формате:
            {
                "update_id": 123456,
                "message": {...} | "callback_query": {...}
            }

        Returns:
            Dict с результатом обработки

        Raises:
            ValueError: Если бот не зарегистрирован
            RuntimeError: Если ошибка обработки
        """
        try:
            # 1. Проверяем регистрацию
            if not self.is_registered(bot_token):
                # Попытка загрузить из БД
                success = await self._load_bot_from_db(bot_token)
                if not success:
                    raise ValueError(f"Bot with token {bot_token[:10]}... not registered")

            # 2. Получаем tenant_id
            tenant_id = self._bot_tenant_map.get(bot_token)
            if not tenant_id:
                raise ValueError(f"Tenant ID not found for bot {bot_token[:10]}...")

            # 3. Устанавливаем tenant context
            async with async_session_maker() as session:
                await set_tenant_context(session, tenant_id)

                # 4. Получаем handler
                handler = self._handlers[bot_token]

                # 5. Определяем тип обновления
                if "message" in update:
                    # Обычное сообщение
                    message = update["message"]
                    logger.debug(
                        f"Processing message: bot={bot_token[:10]}..., "
                        f"user={message.get('from', {}).get('id')}, "
                        f"text={message.get('text', '')[:50]}"
                    )

                    response_text = await handler.handle_message(message)

                    return {
                        "ok": True,
                        "result": {
                            "method": "sendMessage",
                            "chat_id": message["chat"]["id"],
                            "text": response_text
                        }
                    }

                elif "callback_query" in update:
                    # Callback от кнопки
                    callback = update["callback_query"]
                    logger.debug(
                        f"Processing callback: bot={bot_token[:10]}..., "
                        f"data={callback.get('data')}"
                    )

                    response_text = await handler.handle_callback(callback)

                    return {
                        "ok": True,
                        "result": {
                            "method": "answerCallbackQuery",
                            "callback_query_id": callback["id"],
                            "text": response_text
                        }
                    }

                else:
                    logger.warning(f"Unknown update type: {update.keys()}")
                    return {"ok": False, "error": "Unknown update type"}

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return {"ok": False, "error": str(e)}

        except Exception as e:
            logger.error(f"Error processing update: {str(e)}", exc_info=True)
            return {"ok": False, "error": "Internal server error"}

    async def _load_bot_from_db(self, bot_token: str) -> bool:
        """
        Попытка загрузить бота из БД и зарегистрировать handler

        Args:
            bot_token: Токен бота

        Returns:
            True если успешно загружен
        """
        try:
            async with async_session_maker() as session:
                # Ищем бота в БД
                result = await session.execute(
                    select(BotConfig).where(BotConfig.bot_token == bot_token)
                )
                bot_config = result.scalar_one_or_none()

                if not bot_config:
                    logger.warning(f"Bot not found in DB: {bot_token[:10]}...")
                    return False

                # Handler creation is deferred to runtime registration
                logger.info(f"Found bot config in DB: {bot_token[:10]}...")
                return False

        except Exception as e:
            logger.error(f"Error loading bot from DB: {str(e)}")
            return False

    async def reload_bot(self, bot_token: str) -> bool:
        """
        Перезагрузить handler бота (при изменении конфига)

        Args:
            bot_token: Токен бота

        Returns:
            True если успешно
        """
        # Отключаем старый handler
        await self.unregister_bot(bot_token)

        # Загружаем заново
        return await self._load_bot_from_db(bot_token)

    def get_registered_bots(self) -> Dict[str, str]:
        """
        Получить список зарегистрированных ботов

        Returns:
            Dict {bot_token: tenant_id}
        """
        return self._bot_tenant_map.copy()

    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику dispatcher'а

        Returns:
            Dict со статистикой
        """
        return {
            "registered_bots_count": len(self._handlers),
            "bots": [
                {
                    "bot_token": token[:10] + "...",
                    "tenant_id": tenant_id,
                    "handler_class": handler.__class__.__name__
                }
                for token, (tenant_id, handler) in zip(
                    self._handlers.keys(),
                    zip(self._bot_tenant_map.values(), self._handlers.values())
                )
            ]
        }


# Глобальный singleton instance
dispatcher = MultiTenantDispatcher()


# ============================================
# УТИЛИТЫ ДЛЯ РАБОТЫ С DISPATCHER'ОМ
# ============================================

async def register_bot_on_create(bot_config: BotConfig) -> None:
    """
    Зарегистрировать бота в dispatcher при создании

    Вызывается из BotFactory.create_bot()

    Args:
        bot_config: Созданный BotConfig
    """
    # Handler creation deferred — templates register handlers at runtime
    logger.info(f"Bot config registered: {bot_config.bot_token[:10]}...")
