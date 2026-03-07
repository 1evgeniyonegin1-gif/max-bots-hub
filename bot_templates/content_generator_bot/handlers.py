"""
Content Generator Bot Handler
Обработчик бота для генерации контента

Функции:
- Генерация постов разных типов
- Модерация контента (approve/reject/edit)
- Планирование публикаций
- Публикация в каналы
"""
import logging
import random
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from shared.ai_clients.anthropic_client import AnthropicClient
from shared.ai_clients.deepseek_client import DeepseekClient
from shared.ai_clients.yandexgpt_client import YandexGPTClient
from shared.database import get_session
from platform.models.content import GeneratedPost, PostStatus
from bot_templates.content_generator_bot.prompts import (
    get_content_system_prompt,
    get_post_generation_prompt,
    get_available_post_types,
    get_available_personas,
    BUSINESS_PRESETS
)

logger = logging.getLogger(__name__)


class ContentGeneratorBotHandler:
    """
    Handler для бота генерации контента

    Функции:
    - Генерация контента по типу и теме
    - Модерация (одобрение/отклонение/редактирование)
    - Планирование публикаций
    - Отслеживание статистики

    Usage:
        handler = ContentGeneratorBotHandler(
            tenant_id="123-456",
            config={
                "bot_name": "Content Bot",
                "business_preset": "services",
                "persona": "expert",
                "ai_provider": "claude"
            }
        )

        response = await handler.handle_message(message_data)
    """

    def __init__(self, tenant_id: str, bot_id: str, config: Dict[str, Any]):
        """
        Args:
            tenant_id: ID тенанта
            bot_id: ID бота
            config: Конфигурация бота
        """
        self.tenant_id = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        self.bot_id = uuid.UUID(bot_id) if isinstance(bot_id, str) else bot_id
        self.config = config

        # Параметры из конфига
        self.bot_name = config.get("bot_name", "Content Generator")
        self.persona = config.get("persona", "friend")
        self.ai_provider = config.get("ai_provider", "claude")
        self.business_preset = config.get("business_preset", "")
        self.custom_business_context = config.get("business_context", "")
        self.brand_voice = config.get("brand_voice", "")
        self.admin_ids = config.get("admin_ids", [])  # Кто может управлять

        # Инициализация AI клиента
        self.ai_client = self._init_ai_client()

        # Состояние пользователей (для FSM)
        self._user_states: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"ContentGeneratorBotHandler initialized: tenant={tenant_id}, bot={bot_id}, "
            f"provider={self.ai_provider}, persona={self.persona}"
        )

    def _init_ai_client(self):
        """Инициализация AI клиента"""
        if self.ai_provider == "claude":
            return AnthropicClient()
        elif self.ai_provider == "deepseek":
            return DeepseekClient()
        elif self.ai_provider == "yandexgpt":
            return YandexGPTClient()
        else:
            logger.warning(f"Unknown AI provider: {self.ai_provider}, using Claude")
            return AnthropicClient()

    def _get_business_context(self) -> str:
        """Получить бизнес-контекст"""
        if self.custom_business_context:
            return self.custom_business_context

        if self.business_preset and self.business_preset in BUSINESS_PRESETS:
            return BUSINESS_PRESETS[self.business_preset]["context"]

        return ""

    def _is_admin(self, user_id: str) -> bool:
        """Проверка прав администратора"""
        return str(user_id) in [str(aid) for aid in self.admin_ids]

    async def generate_post(
        self,
        post_type: str,
        session: AsyncSession,
        topic: str = "",
        additional_context: str = ""
    ) -> Dict[str, Any]:
        """
        Сгенерировать пост

        Args:
            post_type: Тип поста (product, motivation, tips, etc.)
            topic: Тема поста
            additional_context: Дополнительный контекст

        Returns:
            Dict с данными поста
        """
        logger.info(f"Generating post: type={post_type}, topic={topic[:50] if topic else 'random'}")

        # Получаем промпты
        system_prompt = get_content_system_prompt(
            persona=self.persona,
            business_context=self._get_business_context(),
            brand_voice=self.brand_voice
        )

        user_prompt = get_post_generation_prompt(
            post_type=post_type,
            topic=topic,
            additional_context=additional_context
        )

        # Генерируем через AI
        try:
            content = await self.ai_client.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                max_tokens=1000
            )

            # Очистка от артефактов
            content = self._clean_content(content)

            # Создаём пост в БД
            post = GeneratedPost(
                tenant_id=self.tenant_id,
                bot_id=self.bot_id,
                content=content,
                post_type=post_type,
                status=PostStatus.PENDING
            )

            session.add(post)
            await session.commit()
            await session.refresh(post)

            logger.info(f"Post generated: id={post.id}, length={len(content)}")

            return {
                "id": str(post.id),
                "content": post.content,
                "post_type": post.post_type,
                "topic": topic,
                "status": post.status,
                "ai_model": self.ai_provider,
                "generated_at": post.created_at.isoformat(),
                "tenant_id": str(self.tenant_id)
            }

        except Exception as e:
            logger.error(f"Error generating post: {str(e)}", exc_info=True)
            raise

    def _clean_content(self, content: str) -> str:
        """Очистка контента от артефактов AI"""
        # Убираем обрамляющие кавычки
        content = content.strip()
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        if content.startswith("'") and content.endswith("'"):
            content = content[1:-1]

        # Убираем markdown-заголовки
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.strip().startswith('#'):
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    async def handle_message(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Обработать входящее сообщение

        Args:
            message: Данные сообщения

        Returns:
            Текст ответа
        """
        try:
            user_id = str(message["from"]["id"])
            user_text = message.get("text", "").strip()

            logger.info(
                f"Processing message: tenant={self.tenant_id}, "
                f"user={user_id}, text={user_text[:50]}"
            )

            # Проверка прав
            if not self._is_admin(user_id):
                return "У вас нет прав для управления этим ботом."

            # Проверяем состояние FSM
            user_state = self._user_states.get(user_id, {})
            if user_state.get("state"):
                return await self._handle_fsm_state(user_id, user_text, user_state)

            # Обработка команд
            if user_text.startswith("/"):
                return await self._handle_command(user_text, user_id)

            # По умолчанию показываем меню
            return self._get_main_menu()

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            return "Произошла ошибка. Попробуйте ещё раз."

    async def _handle_command(self, command: str, user_id: str) -> str:
        """Обработка команд"""
        command = command.lower().strip()
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/start":
            return self._get_welcome_message()

        elif cmd == "/help":
            return self._get_help_message()

        elif cmd == "/menu":
            return self._get_main_menu()

        elif cmd == "/generate":
            if args:
                # Генерация с указанным типом
                post_type = args.strip()
                if post_type not in get_available_post_types():
                    return f"Неизвестный тип поста: {post_type}\n\nДоступные типы:\n" + \
                           "\n".join(f"• {t}" for t in get_available_post_types())

                # Устанавливаем состояние для ввода темы
                self._user_states[user_id] = {
                    "state": "waiting_topic",
                    "post_type": post_type
                }
                return f"Выбран тип: {post_type}\n\nВведите тему поста (или отправьте /skip для случайной темы):"

            # Показываем меню типов
            return self._get_post_types_menu()

        elif cmd == "/pending":
            return self._get_pending_posts()

        elif cmd == "/stats":
            return self._get_stats()

        elif cmd == "/skip":
            # Пропуск темы при генерации
            user_state = self._user_states.get(user_id, {})
            if user_state.get("state") == "waiting_topic":
                post_type = user_state.get("post_type", "tips")
                self._user_states[user_id] = {}

                # Генерируем пост
                post = await self.generate_post(post_type=post_type)
                return self._format_post_preview(post)

            return "Нечего пропускать."

        elif cmd == "/types":
            return self._get_post_types_menu()

        else:
            return f"Неизвестная команда: {cmd}\n\nИспользуйте /help для справки."

    async def _handle_fsm_state(self, user_id: str, text: str, state: Dict) -> str:
        """Обработка состояния FSM"""
        current_state = state.get("state")

        if current_state == "waiting_topic":
            # Получили тему, генерируем пост
            post_type = state.get("post_type", "tips")
            self._user_states[user_id] = {}

            post = await self.generate_post(
                post_type=post_type,
                topic=text
            )
            return self._format_post_preview(post)

        elif current_state == "waiting_edit":
            # Получили отредактированный текст
            post_id = state.get("post_id")
            self._user_states[user_id] = {}

            if post_id and post_id in self._posts:
                self._posts[post_id]["content"] = text
                self._posts[post_id]["status"] = PostStatus.PENDING
                return f"Пост обновлён!\n\n{self._format_post_preview(self._posts[post_id])}"

            return "Пост не найден."

        # Сбрасываем неизвестное состояние
        self._user_states[user_id] = {}
        return self._get_main_menu()

    async def handle_callback(self, callback: Dict[str, Any]) -> Optional[str]:
        """
        Обработать callback query (нажатие кнопки)

        Args:
            callback: Данные callback

        Returns:
            Текст ответа
        """
        callback_data = callback.get("data", "")
        user_id = str(callback.get("from", {}).get("id", ""))

        logger.info(f"Callback received: data={callback_data}, user={user_id}")

        if not self._is_admin(user_id):
            return "Нет прав."

        parts = callback_data.split(":")

        if parts[0] == "gen_type":
            # Выбор типа для генерации
            post_type = parts[1] if len(parts) > 1 else "tips"
            self._user_states[user_id] = {
                "state": "waiting_topic",
                "post_type": post_type
            }
            return f"Тип: {post_type}\n\nВведите тему или /skip:"

        elif parts[0] == "approve":
            # Одобрить пост
            post_id = parts[1] if len(parts) > 1 else ""
            if post_id in self._posts:
                self._posts[post_id]["status"] = PostStatus.APPROVED
                return f"Пост {post_id} одобрен!"
            return "Пост не найден."

        elif parts[0] == "reject":
            # Отклонить пост
            post_id = parts[1] if len(parts) > 1 else ""
            if post_id in self._posts:
                self._posts[post_id]["status"] = PostStatus.REJECTED
                return f"Пост {post_id} отклонён."
            return "Пост не найден."

        elif parts[0] == "edit":
            # Редактировать пост
            post_id = parts[1] if len(parts) > 1 else ""
            if post_id in self._posts:
                self._user_states[user_id] = {
                    "state": "waiting_edit",
                    "post_id": post_id
                }
                return f"Текущий текст:\n\n{self._posts[post_id]['content']}\n\nОтправьте новый текст:"
            return "Пост не найден."

        elif parts[0] == "regenerate":
            # Перегенерировать
            post_id = parts[1] if len(parts) > 1 else ""
            if post_id in self._posts:
                old_post = self._posts[post_id]
                new_post = await self.generate_post(
                    post_type=old_post["post_type"],
                    topic=old_post.get("topic", "")
                )
                # Удаляем старый
                del self._posts[post_id]
                return self._format_post_preview(new_post)
            return "Пост не найден."

        return f"Неизвестный callback: {callback_data}"

    def _get_welcome_message(self) -> str:
        """Приветственное сообщение"""
        return f"""Добро пожаловать в {self.bot_name}!

Я помогу генерировать контент для ваших социальных сетей.

Доступные команды:
/generate — Создать новый пост
/pending — Посты на модерации
/stats — Статистика
/help — Справка

Выберите /generate чтобы начать!"""

    def _get_help_message(self) -> str:
        """Справка"""
        return """Справка по командам:

/generate — Создать пост
/generate [тип] — Создать пост указанного типа
/types — Показать типы постов
/pending — Посты на модерации
/stats — Статистика
/menu — Главное меню

Типы постов:
• product — О продукте
• motivation — Мотивация
• success_story — История успеха
• tips — Советы
• news — Новости
• promo — Акция
• educational — Обучающий
• behind_the_scenes — Закулисье"""

    def _get_main_menu(self) -> str:
        """Главное меню"""
        pending_count = len([p for p in self._posts.values() if p["status"] == PostStatus.PENDING])

        return f"""Главное меню

Посты на модерации: {pending_count}

Команды:
/generate — Создать пост
/pending — На модерации ({pending_count})
/stats — Статистика
/help — Справка"""

    def _get_post_types_menu(self) -> str:
        """Меню типов постов"""
        types_list = "\n".join(f"• /generate {t}" for t in get_available_post_types())
        return f"""Выберите тип поста:

{types_list}

Или отправьте /generate для случайного типа."""

    def _get_pending_posts(self) -> str:
        """Список постов на модерации"""
        pending = [p for p in self._posts.values() if p["status"] == PostStatus.PENDING]

        if not pending:
            return "Нет постов на модерации.\n\nСоздайте новый: /generate"

        result = f"Постов на модерации: {len(pending)}\n\n"

        for i, post in enumerate(pending[:5], 1):  # Показываем первые 5
            preview = post["content"][:100] + "..." if len(post["content"]) > 100 else post["content"]
            result += f"{i}. [{post['post_type']}] {post['id']}\n{preview}\n\n"

        return result

    def _get_stats(self) -> str:
        """Статистика"""
        total = len(self._posts)
        by_status = {}
        for post in self._posts.values():
            status = post["status"].value if hasattr(post["status"], "value") else post["status"]
            by_status[status] = by_status.get(status, 0) + 1

        stats = f"""Статистика

Всего постов: {total}

По статусам:
"""
        for status, count in by_status.items():
            stats += f"• {status}: {count}\n"

        return stats

    def _format_post_preview(self, post: Dict[str, Any]) -> str:
        """Форматирование превью поста"""
        return f"""Новый пост создан!

Тип: {post['post_type']}
ID: {post['id']}

{post['content']}

---
Действия:
• approve:{post['id']} — Одобрить
• reject:{post['id']} — Отклонить
• edit:{post['id']} — Редактировать
• regenerate:{post['id']} — Перегенерировать"""

    def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Получить пост по ID"""
        return self._posts.get(post_id)

    def get_all_posts(self) -> List[Dict[str, Any]]:
        """Получить все посты"""
        return list(self._posts.values())

    def approve_post(self, post_id: str) -> bool:
        """Одобрить пост"""
        if post_id in self._posts:
            self._posts[post_id]["status"] = PostStatus.APPROVED
            return True
        return False

    def reject_post(self, post_id: str) -> bool:
        """Отклонить пост"""
        if post_id in self._posts:
            self._posts[post_id]["status"] = PostStatus.REJECTED
            return True
        return False


# ============================================
# ИНТЕГРАЦИЯ С BotFactory
# ============================================

def create_content_generator_handler(
    tenant_id: str,
    config: Dict[str, Any]
) -> ContentGeneratorBotHandler:
    """
    Фабричная функция для создания handler'а

    Args:
        tenant_id: ID тенанта
        config: Конфигурация бота

    Returns:
        ContentGeneratorBotHandler instance
    """
    return ContentGeneratorBotHandler(tenant_id, config)
