"""
Tests for Content Generator Bot Handler

Тестирование бота генерации контента
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from bot_templates.content_generator_bot.handlers import (
    ContentGeneratorBotHandler,
    PostStatus,
    create_content_generator_handler
)
from bot_templates.content_generator_bot.prompts import (
    get_content_system_prompt,
    get_post_generation_prompt,
    get_available_post_types,
    get_available_personas,
    BUSINESS_PRESETS
)


class TestContentGeneratorPrompts:
    """Тесты промптов"""

    def test_get_available_post_types(self):
        """Тест получения списка типов постов"""
        types = get_available_post_types()

        assert isinstance(types, list)
        assert len(types) > 0
        assert "product" in types
        assert "motivation" in types
        assert "tips" in types

    def test_get_available_personas(self):
        """Тест получения списка персон"""
        personas = get_available_personas()

        assert isinstance(personas, list)
        assert len(personas) > 0
        assert "expert" in personas
        assert "friend" in personas

    def test_get_content_system_prompt_default(self):
        """Тест системного промпта по умолчанию"""
        prompt = get_content_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "контент" in prompt.lower() or "русском" in prompt.lower()

    def test_get_content_system_prompt_with_persona(self):
        """Тест системного промпта с персоной"""
        prompt = get_content_system_prompt(persona="expert")

        assert "эксперт" in prompt.lower()

    def test_get_content_system_prompt_with_context(self):
        """Тест системного промпта с бизнес-контекстом"""
        context = "Интернет-магазин косметики"
        prompt = get_content_system_prompt(business_context=context)

        assert context in prompt

    def test_get_post_generation_prompt(self):
        """Тест промпта генерации поста"""
        prompt = get_post_generation_prompt(
            post_type="product",
            topic="Новый крем для лица"
        )

        assert isinstance(prompt, str)
        assert "ПРОДУКТ" in prompt or "product" in prompt.lower()
        assert "Новый крем для лица" in prompt

    def test_business_presets_exist(self):
        """Тест наличия бизнес-пресетов"""
        assert len(BUSINESS_PRESETS) > 0
        assert "ecommerce" in BUSINESS_PRESETS
        assert "services" in BUSINESS_PRESETS


class TestContentGeneratorBotHandler:
    """Тесты для ContentGeneratorBotHandler"""

    @pytest.fixture
    def handler_config(self):
        return {
            "bot_name": "Content Bot",
            "admin_ids": ["123456"],
            "persona": "friend",
            "ai_provider": "claude",
            "business_preset": "services"
        }

    def test_init_basic(self, sample_tenant_id, handler_config):
        """Тест базовой инициализации"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        assert handler.tenant_id == sample_tenant_id
        assert handler.bot_name == "Content Bot"
        assert "123456" in handler.admin_ids
        assert handler.persona == "friend"

    def test_is_admin_true(self, sample_tenant_id, handler_config):
        """Тест проверки админа - позитивный"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        assert handler._is_admin("123456") is True

    def test_is_admin_false(self, sample_tenant_id, handler_config):
        """Тест проверки админа - негативный"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        assert handler._is_admin("999999") is False

    def test_generate_post_id(self, sample_tenant_id, handler_config):
        """Тест генерации ID поста"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        id1 = handler._generate_post_id()
        id2 = handler._generate_post_id()

        assert id1 != id2
        assert id1.startswith("post_")

    @pytest.mark.asyncio
    async def test_generate_post(self, sample_tenant_id, handler_config, mock_ai_client):
        """Тест генерации поста"""
        mock_ai_client.chat = AsyncMock(return_value="Сгенерированный пост о продукте.")

        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient', return_value=mock_ai_client):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)
            handler.ai_client = mock_ai_client

        post = await handler.generate_post(
            post_type="product",
            topic="Новый продукт"
        )

        assert post["post_type"] == "product"
        assert post["topic"] == "Новый продукт"
        assert post["status"] == PostStatus.PENDING
        assert "content" in post
        mock_ai_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_non_admin(self, sample_tenant_id, handler_config):
        """Тест обработки сообщения от не-админа"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        message = {
            "from": {"id": "not_admin_999"},
            "text": "/generate"
        }

        response = await handler.handle_message(message)

        assert "нет прав" in response.lower()

    @pytest.mark.asyncio
    async def test_handle_start_command(self, sample_tenant_id, handler_config):
        """Тест команды /start"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        message = {
            "from": {"id": "123456"},
            "text": "/start"
        }

        response = await handler.handle_message(message)

        assert "Content Bot" in response
        assert "/generate" in response

    @pytest.mark.asyncio
    async def test_handle_help_command(self, sample_tenant_id, handler_config):
        """Тест команды /help"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        message = {
            "from": {"id": "123456"},
            "text": "/help"
        }

        response = await handler.handle_message(message)

        assert "/generate" in response
        assert "/pending" in response
        assert "/stats" in response

    @pytest.mark.asyncio
    async def test_handle_types_command(self, sample_tenant_id, handler_config):
        """Тест команды /types"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        message = {
            "from": {"id": "123456"},
            "text": "/types"
        }

        response = await handler.handle_message(message)

        assert "product" in response
        assert "motivation" in response

    @pytest.mark.asyncio
    async def test_handle_stats_command(self, sample_tenant_id, handler_config):
        """Тест команды /stats"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        message = {
            "from": {"id": "123456"},
            "text": "/stats"
        }

        response = await handler.handle_message(message)

        assert "статистика" in response.lower()

    @pytest.mark.asyncio
    async def test_handle_pending_empty(self, sample_tenant_id, handler_config):
        """Тест команды /pending когда нет постов"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        message = {
            "from": {"id": "123456"},
            "text": "/pending"
        }

        response = await handler.handle_message(message)

        assert "нет постов" in response.lower()

    def test_approve_post(self, sample_tenant_id, handler_config):
        """Тест одобрения поста"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        # Создаём тестовый пост
        handler._posts["test_post"] = {
            "id": "test_post",
            "status": PostStatus.PENDING
        }

        result = handler.approve_post("test_post")

        assert result is True
        assert handler._posts["test_post"]["status"] == PostStatus.APPROVED

    def test_reject_post(self, sample_tenant_id, handler_config):
        """Тест отклонения поста"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        handler._posts["test_post"] = {
            "id": "test_post",
            "status": PostStatus.PENDING
        }

        result = handler.reject_post("test_post")

        assert result is True
        assert handler._posts["test_post"]["status"] == PostStatus.REJECTED

    def test_get_all_posts(self, sample_tenant_id, handler_config):
        """Тест получения всех постов"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        handler._posts["post1"] = {"id": "post1"}
        handler._posts["post2"] = {"id": "post2"}

        posts = handler.get_all_posts()

        assert len(posts) == 2

    @pytest.mark.asyncio
    async def test_handle_callback_approve(self, sample_tenant_id, handler_config):
        """Тест callback одобрения"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        handler._posts["test_post"] = {
            "id": "test_post",
            "status": PostStatus.PENDING
        }

        callback = {
            "from": {"id": "123456"},
            "data": "approve:test_post"
        }

        response = await handler.handle_callback(callback)

        assert "одобрен" in response.lower()

    @pytest.mark.asyncio
    async def test_handle_callback_reject(self, sample_tenant_id, handler_config):
        """Тест callback отклонения"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        handler._posts["test_post"] = {
            "id": "test_post",
            "status": PostStatus.PENDING
        }

        callback = {
            "from": {"id": "123456"},
            "data": "reject:test_post"
        }

        response = await handler.handle_callback(callback)

        assert "отклонён" in response.lower()

    def test_clean_content(self, sample_tenant_id, handler_config):
        """Тест очистки контента"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler(sample_tenant_id, handler_config)

        # Тест удаления кавычек
        content = '"Текст в кавычках"'
        cleaned = handler._clean_content(content)
        assert cleaned == "Текст в кавычках"

        # Тест удаления markdown заголовков
        content = "# Заголовок\nТекст"
        cleaned = handler._clean_content(content)
        assert "#" not in cleaned
        assert "Текст" in cleaned

    def test_factory_function(self, sample_tenant_id, handler_config):
        """Тест фабричной функции"""
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = create_content_generator_handler(sample_tenant_id, handler_config)

        assert isinstance(handler, ContentGeneratorBotHandler)


class TestPostStatusFlow:
    """Тесты жизненного цикла поста"""

    @pytest.fixture
    def handler(self, sample_tenant_id):
        config = {
            "bot_name": "Test Bot",
            "admin_ids": ["123456"],
            "persona": "friend",
            "ai_provider": "claude"
        }
        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            return ContentGeneratorBotHandler(sample_tenant_id, config)

    def test_post_status_enum(self):
        """Тест enum статусов"""
        assert PostStatus.DRAFT == "draft"
        assert PostStatus.PENDING == "pending"
        assert PostStatus.APPROVED == "approved"
        assert PostStatus.PUBLISHED == "published"
        assert PostStatus.REJECTED == "rejected"
        assert PostStatus.SCHEDULED == "scheduled"

    @pytest.mark.asyncio
    async def test_post_lifecycle(self, handler, mock_ai_client):
        """Тест полного жизненного цикла поста"""
        mock_ai_client.chat = AsyncMock(return_value="Тестовый пост")
        handler.ai_client = mock_ai_client

        # 1. Генерация поста
        post = await handler.generate_post(post_type="tips")
        assert post["status"] == PostStatus.PENDING

        # 2. Одобрение
        handler.approve_post(post["id"])
        assert handler._posts[post["id"]]["status"] == PostStatus.APPROVED
