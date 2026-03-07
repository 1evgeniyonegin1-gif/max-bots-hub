"""
Conversation Bot Handler
Обработчик диалогового бота (адаптация curator_bot из APEXFLOW)

Улучшения:
- RAG интеграция для базы знаний
- Поддержка inline кнопок
- Сохранение истории в БД
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from shared.ai_clients.anthropic_client import AnthropicClient
from shared.ai_clients.deepseek_client import DeepseekClient
from shared.ai_clients.yandexgpt_client import YandexGPTClient
from shared.database import get_session
from platform.models.conversation import ConversationMessage

logger = logging.getLogger(__name__)

# Lazy import для RAG (может быть не установлен)
_rag_engine = None


def get_rag_engine():
    """Ленивая загрузка RAG engine"""
    global _rag_engine
    if _rag_engine is None:
        try:
            from shared.rag import get_rag_engine as _get_rag
            _rag_engine = _get_rag()
        except ImportError:
            logger.warning("RAG system not available (sentence-transformers not installed)")
            _rag_engine = False
    return _rag_engine if _rag_engine else None


class ConversationBotHandler:
    """
    Handler для диалогового бота

    Функции:
    - Приём сообщений от пользователей
    - Генерация ответов через AI (Claude/Deepseek/YandexGPT)
    - RAG - поиск в базе знаний
    - Сохранение истории диалогов
    - Поддержка inline кнопок
    - Персонализация по конфигу

    Usage:
        handler = ConversationBotHandler(
            tenant_id="123-456",
            config={
                "greeting": "Привет!",
                "persona": "friendly",
                "ai_provider": "claude",
                "enable_rag": True
            }
        )

        response = await handler.handle_message(message_data)
    """

    def __init__(self, tenant_id: str, bot_id: str, config: Dict[str, Any]):
        """
        Args:
            tenant_id: ID тенанта (для изоляции данных)
            bot_id: ID бота
            config: Конфигурация бота из BotConfig
        """
        self.tenant_id = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        self.bot_id = uuid.UUID(bot_id) if isinstance(bot_id, str) else bot_id
        self.config = config

        # Параметры из конфига
        self.greeting = config.get("greeting", "Привет! Чем могу помочь?")
        self.persona = config.get("persona", "friendly")
        self.ai_provider = config.get("ai_provider", "claude")
        self.max_conversation_length = config.get("max_conversation_length", 100)
        self.enable_rag = config.get("enable_rag", True)
        self.rag_category = config.get("rag_category", "general")
        self.custom_system_prompt = config.get("custom_system_prompt", "")

        # Инициализация AI клиента
        self.ai_client = self._init_ai_client()

        # RAG engine (ленивая загрузка)
        self._rag_engine = None

        # Состояния пользователей для FSM (пока в памяти)
        self._user_states: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"ConversationBotHandler initialized: tenant={tenant_id}, bot={bot_id}, "
            f"provider={self.ai_provider}, persona={self.persona}, "
            f"rag={self.enable_rag}"
        )

    def _init_ai_client(self):
        """Инициализация AI клиента по provider'у"""
        if self.ai_provider == "claude":
            return AnthropicClient()
        elif self.ai_provider == "deepseek":
            return DeepseekClient()
        elif self.ai_provider == "yandexgpt":
            return YandexGPTClient()
        else:
            logger.warning(f"Unknown AI provider: {self.ai_provider}, using Claude")
            return AnthropicClient()

    def _get_rag_engine(self):
        """Получить RAG engine (ленивая загрузка)"""
        if self._rag_engine is None:
            self._rag_engine = get_rag_engine()
        return self._rag_engine

    def _get_system_prompt(self) -> str:
        """Генерация system prompt на основе persona"""
        persona_prompts = {
            "friendly": (
                "Ты дружелюбный AI-ассистент. Общайся тепло и неформально. "
                "Используй смайлики 😊. Будь полезным и поддерживающим."
            ),
            "professional": (
                "Ты профессиональный AI-ассистент. Общайся формально и по делу. "
                "Давай точные и структурированные ответы. Избегай эмоций."
            ),
            "funny": (
                "Ты весёлый AI-ассистент с чувством юмора. Шути, используй мемы. "
                "Делай общение лёгким и развлекательным, но оставайся полезным."
            ),
            "expert": (
                "Ты эксперт в своей области. Давай глубокие, структурированные ответы. "
                "Используй факты и примеры. Будь уверенным, но открытым для вопросов."
            ),
            "mentor": (
                "Ты мудрый наставник. Задавай наводящие вопросы. "
                "Помогай пользователю прийти к ответу самостоятельно."
            )
        }

        base_prompt = persona_prompts.get(
            self.persona,
            persona_prompts["friendly"]
        )

        if self.custom_system_prompt:
            base_prompt = f"{base_prompt}\n\n{self.custom_system_prompt}"

        return f"{base_prompt}\n\nОтвечай кратко и по существу. Максимум 3-4 предложения."

    async def _get_conversation_history(
        self,
        user_id: str,
        session: AsyncSession
    ) -> List[Dict]:
        """
        Получить историю диалога с пользователем из БД

        Args:
            user_id: ID пользователя
            session: AsyncSession для работы с БД

        Returns:
            Список сообщений [{role, content, timestamp}]
        """
        # Берём последние N сообщений
        result = await session.execute(
            select(ConversationMessage)
            .where(
                ConversationMessage.tenant_id == self.tenant_id,
                ConversationMessage.bot_id == self.bot_id,
                ConversationMessage.user_id == user_id
            )
            .order_by(desc(ConversationMessage.created_at))
            .limit(self.max_conversation_length)
        )

        messages = result.scalars().all()

        # Переворачиваем чтобы старые были первыми
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in reversed(messages)
        ]

    async def _add_to_history(
        self,
        user_id: str,
        role: str,
        content: str,
        session: AsyncSession
    ):
        """
        Добавить сообщение в историю в БД

        Args:
            user_id: ID пользователя
            role: Роль (user или assistant)
            content: Текст сообщения
            session: AsyncSession для работы с БД
        """
        message = ConversationMessage(
            tenant_id=self.tenant_id,
            bot_id=self.bot_id,
            user_id=user_id,
            role=role,
            content=content
        )

        session.add(message)
        await session.commit()

    async def _get_rag_context(self, query: str) -> str:
        """Получить контекст из RAG"""
        if not self.enable_rag:
            return ""

        rag = self._get_rag_engine()
        if not rag:
            return ""

        try:
            # Категория с tenant prefix для изоляции
            category = f"{self.tenant_id}_{self.rag_category}"

            context = await rag.get_context(
                query=query,
                top_k=3,
                category=category,
                min_similarity=0.3,
                max_context_length=1500
            )

            return context

        except Exception as e:
            logger.error(f"RAG error: {str(e)}")
            return ""

    async def handle_message(
        self,
        message: Dict[str, Any],
        session: AsyncSession
    ) -> Optional[str]:
        """
        Обработать входящее сообщение

        Args:
            message: Данные сообщения от MAX
            session: AsyncSession для работы с БД

        Returns:
            Текст ответа
        """
        try:
            user_id = str(message["from"]["id"])
            user_text = message.get("text", "")

            # В DEBUG режиме логируем текст
            if logger.level <= logging.DEBUG:
                logger.debug(f"Message text: {user_text[:50]}")
            else:
                logger.info(
                    f"Processing message: tenant={self.tenant_id}, "
                    f"user={user_id}, length={len(user_text)}"
                )

            # Проверяем состояние FSM
            user_state = self._user_states.get(user_id, {})
            if user_state.get("state"):
                return await self._handle_fsm_state(user_id, user_text, user_state, session)

            # Обработка команд
            if user_text.startswith("/"):
                return await self._handle_command(user_text, user_id, session)

            # Добавляем сообщение пользователя в историю
            await self._add_to_history(user_id, "user", user_text, session)

            # Получаем историю для контекста
            history = await self._get_conversation_history(user_id, session)

            # Получаем RAG контекст
            rag_context = await self._get_rag_context(user_text)

            # Формируем system prompt
            system_prompt = self._get_system_prompt()
            if rag_context:
                system_prompt = f"{system_prompt}\n\n{rag_context}"

            # Генерируем ответ через AI
            messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in history
            ]

            response_text = await self.ai_client.chat(
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=500
            )

            # Добавляем ответ в историю
            await self._add_to_history(user_id, "assistant", response_text, session)

            logger.info(
                f"Generated response: tenant={self.tenant_id}, "
                f"user={user_id}, length={len(response_text)}, "
                f"has_rag={bool(rag_context)}"
            )

            return response_text

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            return "Извините, произошла ошибка. Попробуйте ещё раз."

    async def _handle_command(
        self,
        command: str,
        user_id: str,
        session: AsyncSession
    ) -> str:
        """Обработка команд бота"""
        command = command.lower().strip()
        parts = command.split(maxsplit=1)
        cmd = parts[0]

        if cmd == "/start":
            # Очищаем состояние FSM
            self._user_states[user_id] = {}
            return self.greeting

        elif cmd == "/help":
            return (
                "Я AI-ассистент, готов помочь вам!\n\n"
                "Команды:\n"
                "/start - Начать заново\n"
                "/help - Показать эту справку\n"
                "/status - Статус бота"
            )

        elif cmd == "/status":
            history = await self._get_conversation_history(user_id, session)
            history_len = len(history)
            rag_status = "включён" if self.enable_rag and self._get_rag_engine() else "отключён"

            return (
                f"Статус бота:\n"
                f"• AI: {self.ai_provider}\n"
                f"• Персона: {self.persona}\n"
                f"• RAG: {rag_status}\n"
                f"• Сообщений в истории: {history_len}"
            )

        else:
            return f"Неизвестная команда: {cmd}. Используйте /help для справки."

    async def _handle_fsm_state(
        self,
        user_id: str,
        text: str,
        state: Dict[str, Any],
        session: AsyncSession
    ) -> str:
        """Обработка состояния FSM"""
        current_state = state.get("state")

        # Сброс состояния по умолчанию
        self._user_states[user_id] = {}

        # Можно добавить кастомные состояния здесь
        return "Состояние сброшено. Чем могу помочь?"

    async def handle_callback(self, callback: Dict[str, Any]) -> Optional[str]:
        """
        Обработать callback query (нажатие кнопки)

        Args:
            callback: Данные callback от MAX

        Returns:
            Текст ответа
        """
        callback_data = callback.get("data", "")
        user_id = str(callback.get("from", {}).get("id", ""))

        logger.info(f"Callback received: data={callback_data}, user={user_id}")

        # Обработка разных типов callback
        parts = callback_data.split(":")

        if parts[0] == "clear":
            self._conversation_history[user_id] = []
            return "История очищена!"

        elif parts[0] == "help":
            return await self._handle_command("/help", user_id)

        return f"Callback обработан: {callback_data}"

    def get_inline_keyboard(self) -> List[List[Dict[str, str]]]:
        """
        Получить inline клавиатуру для бота

        Returns:
            Список рядов кнопок
        """
        return [
            [
                {"text": "Помощь", "callback_data": "help"},
                {"text": "Очистить", "callback_data": "clear"}
            ]
        ]

    def add_knowledge(
        self,
        content: str,
        source: str = "manual",
        category: Optional[str] = None
    ) -> Optional[str]:
        """
        Добавить знание в RAG базу

        Args:
            content: Текст знания
            source: Источник
            category: Категория (по умолчанию берётся из конфига)

        Returns:
            ID документа или None
        """
        if not self.enable_rag:
            logger.warning("RAG is disabled for this bot")
            return None

        rag = self._get_rag_engine()
        if not rag:
            logger.warning("RAG engine not available")
            return None

        try:
            cat = category or self.rag_category
            tenant_category = f"{self.tenant_id}_{cat}"

            doc_id = rag.add_knowledge(
                content=content,
                source=source,
                category=tenant_category,
                metadata={"tenant_id": self.tenant_id}
            )

            logger.info(f"Knowledge added: id={doc_id}, category={tenant_category}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to add knowledge: {str(e)}")
            return None


# ============================================
# ИНТЕГРАЦИЯ С BotFactory
# ============================================

def create_conversation_bot_handler(
    tenant_id: str,
    bot_id: str,
    config: Dict[str, Any]
) -> ConversationBotHandler:
    """
    Фабричная функция для создания handler'а

    Args:
        tenant_id: ID тенанта
        bot_id: ID бота
        config: Конфигурация бота

    Returns:
        ConversationBotHandler instance
    """
    return ConversationBotHandler(tenant_id, bot_id, config)
