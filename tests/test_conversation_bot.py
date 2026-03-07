"""
Tests for Conversation Bot Handler

Тестирование диалогового бота
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from bot_templates.conversation_bot.handlers import (
    ConversationBotHandler,
    create_conversation_bot_handler
)


class TestConversationBotHandler:
    """Тесты для ConversationBotHandler"""

    def test_init_with_default_config(self, sample_tenant_id):
        """Тест инициализации с дефолтным конфигом"""
        config = {"bot_name": "Test Bot"}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, config)

        assert handler.tenant_id == sample_tenant_id
        assert handler.greeting == "Привет! Чем могу помочь?"
        assert handler.persona == "friendly"
        assert handler.ai_provider == "claude"

    def test_init_with_custom_config(self, sample_tenant_id):
        """Тест инициализации с кастомным конфигом"""
        config = {
            "bot_name": "Custom Bot",
            "greeting": "Здравствуйте!",
            "persona": "professional",
            "ai_provider": "deepseek",
            "enable_rag": False
        }

        with patch('bot_templates.conversation_bot.handlers.DeepseekClient'):
            handler = ConversationBotHandler(sample_tenant_id, config)

        assert handler.greeting == "Здравствуйте!"
        assert handler.persona == "professional"
        assert handler.ai_provider == "deepseek"
        assert handler.enable_rag is False

    def test_get_system_prompt_friendly(self, sample_tenant_id, sample_bot_config):
        """Тест генерации system prompt для friendly персоны"""
        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, sample_bot_config)

        prompt = handler._get_system_prompt()

        assert "дружелюбный" in prompt.lower()
        assert "смайлики" in prompt.lower()

    def test_get_system_prompt_professional(self, sample_tenant_id):
        """Тест генерации system prompt для professional персоны"""
        config = {"bot_name": "Pro Bot", "persona": "professional"}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, config)

        prompt = handler._get_system_prompt()

        assert "профессиональный" in prompt.lower()
        assert "формально" in prompt.lower()

    def test_conversation_history_management(self, sample_tenant_id, sample_bot_config):
        """Тест управления историей диалога"""
        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, sample_bot_config)

        user_id = "user_123"

        # Изначально история пуста
        history = handler._get_conversation_history(user_id)
        assert len(history) == 0

        # Добавляем сообщения
        handler._add_to_history(user_id, "user", "Привет")
        handler._add_to_history(user_id, "assistant", "Здравствуйте!")

        history = handler._get_conversation_history(user_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_conversation_history_limit(self, sample_tenant_id):
        """Тест ограничения длины истории"""
        config = {"bot_name": "Test Bot", "max_conversation_length": 2}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, config)

        user_id = "user_123"

        # Добавляем больше сообщений чем лимит
        for i in range(10):
            handler._add_to_history(user_id, "user", f"Сообщение {i}")
            handler._add_to_history(user_id, "assistant", f"Ответ {i}")

        history = handler._get_conversation_history(user_id)
        # max_conversation_length * 2 = 4 сообщения
        assert len(history) <= 4

    @pytest.mark.asyncio
    async def test_handle_start_command(self, sample_tenant_id, sample_bot_config):
        """Тест команды /start"""
        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, sample_bot_config)

        message = {
            "from": {"id": "user_123"},
            "text": "/start"
        }

        response = await handler.handle_message(message)

        assert response == sample_bot_config["greeting"]

    @pytest.mark.asyncio
    async def test_handle_help_command(self, sample_tenant_id, sample_bot_config):
        """Тест команды /help"""
        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, sample_bot_config)

        message = {
            "from": {"id": "user_123"},
            "text": "/help"
        }

        response = await handler.handle_message(message)

        assert "/start" in response
        assert "/help" in response
        assert "/clear" in response

    @pytest.mark.asyncio
    async def test_handle_clear_command(self, sample_tenant_id, sample_bot_config):
        """Тест команды /clear"""
        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, sample_bot_config)

        user_id = "user_123"

        # Добавляем историю
        handler._add_to_history(user_id, "user", "Test message")

        message = {
            "from": {"id": user_id},
            "text": "/clear"
        }

        response = await handler.handle_message(message)

        assert "очищена" in response.lower()
        assert len(handler._get_conversation_history(user_id)) == 0

    @pytest.mark.asyncio
    async def test_handle_unknown_command(self, sample_tenant_id, sample_bot_config):
        """Тест неизвестной команды"""
        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, sample_bot_config)

        message = {
            "from": {"id": "user_123"},
            "text": "/unknown_cmd"
        }

        response = await handler.handle_message(message)

        assert "неизвестная" in response.lower() or "unknown" in response.lower()

    @pytest.mark.asyncio
    async def test_handle_regular_message(self, sample_tenant_id, sample_bot_config, mock_ai_client):
        """Тест обработки обычного сообщения"""
        with patch('bot_templates.conversation_bot.handlers.AnthropicClient', return_value=mock_ai_client):
            handler = ConversationBotHandler(sample_tenant_id, sample_bot_config)
            handler.ai_client = mock_ai_client

        message = {
            "from": {"id": "user_123"},
            "text": "Как дела?"
        }

        response = await handler.handle_message(message)

        assert response == "Тестовый ответ от AI"
        mock_ai_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_callback(self, sample_tenant_id, sample_bot_config, sample_callback):
        """Тест обработки callback"""
        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, sample_bot_config)

        response = await handler.handle_callback(sample_callback)

        assert response is not None

    @pytest.mark.asyncio
    async def test_handle_clear_callback(self, sample_tenant_id, sample_bot_config):
        """Тест callback очистки истории"""
        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, sample_bot_config)

        user_id = "user_123"
        handler._add_to_history(user_id, "user", "Test")

        callback = {
            "from": {"id": user_id},
            "data": "clear"
        }

        response = await handler.handle_callback(callback)

        assert "очищена" in response.lower()
        assert len(handler._get_conversation_history(user_id)) == 0

    def test_get_inline_keyboard(self, sample_tenant_id, sample_bot_config):
        """Тест получения inline клавиатуры"""
        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler(sample_tenant_id, sample_bot_config)

        keyboard = handler.get_inline_keyboard()

        assert isinstance(keyboard, list)
        assert len(keyboard) > 0
        assert "text" in keyboard[0][0]
        assert "callback_data" in keyboard[0][0]

    def test_factory_function(self, sample_tenant_id, sample_bot_config):
        """Тест фабричной функции"""
        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = create_conversation_bot_handler(sample_tenant_id, sample_bot_config)

        assert isinstance(handler, ConversationBotHandler)
        assert handler.tenant_id == sample_tenant_id


class TestAIProviderSelection:
    """Тесты выбора AI провайдера"""

    def test_claude_provider(self, sample_tenant_id):
        """Тест выбора Claude"""
        config = {"bot_name": "Test", "ai_provider": "claude"}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient') as mock:
            handler = ConversationBotHandler(sample_tenant_id, config)
            mock.assert_called_once()

    def test_deepseek_provider(self, sample_tenant_id):
        """Тест выбора Deepseek"""
        config = {"bot_name": "Test", "ai_provider": "deepseek"}

        with patch('bot_templates.conversation_bot.handlers.DeepseekClient') as mock:
            handler = ConversationBotHandler(sample_tenant_id, config)
            mock.assert_called_once()

    def test_yandexgpt_provider(self, sample_tenant_id):
        """Тест выбора YandexGPT"""
        config = {"bot_name": "Test", "ai_provider": "yandexgpt"}

        with patch('bot_templates.conversation_bot.handlers.YandexGPTClient') as mock:
            handler = ConversationBotHandler(sample_tenant_id, config)
            mock.assert_called_once()

    def test_unknown_provider_fallback(self, sample_tenant_id):
        """Тест fallback на Claude при неизвестном провайдере"""
        config = {"bot_name": "Test", "ai_provider": "unknown_provider"}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient') as mock:
            handler = ConversationBotHandler(sample_tenant_id, config)
            mock.assert_called_once()
