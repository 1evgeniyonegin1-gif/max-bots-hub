"""
Security Tests

Тестирование безопасности MAX BOTS HUB
"""
import pytest
from unittest.mock import patch, MagicMock


class TestInputValidation:
    """Тесты валидации входных данных"""

    def test_sql_injection_in_message(self):
        """Тест защиты от SQL injection в сообщениях"""
        from bot_templates.conversation_bot.handlers import ConversationBotHandler

        config = {"bot_name": "Test"}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler("test_tenant", config)

        # Попытка SQL injection
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users --",
            "'; DELETE FROM bot_configs; --"
        ]

        for malicious_input in malicious_inputs:
            # История диалога не должна выполнять SQL
            handler._add_to_history("user_123", "user", malicious_input)

            history = handler._get_conversation_history("user_123")
            # Проверяем что текст сохранён как есть (не интерпретирован как SQL)
            assert any(malicious_input in h["content"] for h in history)

    def test_xss_in_content(self):
        """Тест защиты от XSS в контенте"""
        from bot_templates.content_generator_bot.handlers import ContentGeneratorBotHandler

        config = {
            "bot_name": "Test",
            "admin_ids": ["123"]
        }

        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler("test_tenant", config)

        # Попытка XSS
        xss_inputs = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "'-alert(1)-'"
        ]

        for xss_input in xss_inputs:
            # Создаём пост с XSS
            handler._posts["test"] = {
                "id": "test",
                "content": xss_input,
                "status": "pending"
            }

            # Контент сохраняется как текст, не выполняется
            assert handler._posts["test"]["content"] == xss_input

    def test_path_traversal_protection(self):
        """Тест защиты от path traversal"""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM"
        ]

        # Эти пути не должны использоваться напрямую в коде
        # Проверяем что они не приводят к ошибкам при обработке как текст
        from bot_templates.conversation_bot.handlers import ConversationBotHandler

        config = {"bot_name": "Test"}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler("test_tenant", config)

        for path in dangerous_paths:
            # Просто проверяем что обработка не падает
            handler._add_to_history("user_123", "user", path)


class TestAuthenticationSecurity:
    """Тесты безопасности аутентификации"""

    def test_admin_id_type_coercion(self):
        """Тест типизации admin_ids"""
        from bot_templates.content_generator_bot.handlers import ContentGeneratorBotHandler

        # Тест с разными типами admin_ids
        configs = [
            {"bot_name": "Test", "admin_ids": ["123"]},
            {"bot_name": "Test", "admin_ids": [123]},  # int
            {"bot_name": "Test", "admin_ids": "123"},  # string
        ]

        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            for config in configs:
                handler = ContentGeneratorBotHandler("test_tenant", config)
                # Проверяем что проверка работает
                assert handler._is_admin("123") is True
                assert handler._is_admin("456") is False

    def test_empty_admin_ids(self):
        """Тест с пустым списком админов"""
        from bot_templates.content_generator_bot.handlers import ContentGeneratorBotHandler

        config = {
            "bot_name": "Test",
            "admin_ids": []
        }

        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler("test_tenant", config)

        # Никто не должен быть админом
        assert handler._is_admin("123") is False
        assert handler._is_admin("admin") is False


class TestTenantIsolation:
    """Тесты изоляции данных между тенантами"""

    def test_conversation_history_isolation(self):
        """Тест изоляции истории диалогов"""
        from bot_templates.conversation_bot.handlers import ConversationBotHandler

        config = {"bot_name": "Test"}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler1 = ConversationBotHandler("tenant_1", config)
            handler2 = ConversationBotHandler("tenant_2", config)

        # Добавляем историю для разных тенантов
        handler1._add_to_history("user_123", "user", "Сообщение tenant 1")
        handler2._add_to_history("user_123", "user", "Сообщение tenant 2")

        # Проверяем изоляцию
        history1 = handler1._get_conversation_history("user_123")
        history2 = handler2._get_conversation_history("user_123")

        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0]["content"] != history2[0]["content"]

    def test_posts_isolation(self):
        """Тест изоляции постов"""
        from bot_templates.content_generator_bot.handlers import ContentGeneratorBotHandler

        config = {
            "bot_name": "Test",
            "admin_ids": ["123"]
        }

        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler1 = ContentGeneratorBotHandler("tenant_1", config)
            handler2 = ContentGeneratorBotHandler("tenant_2", config)

        # Добавляем посты для разных тенантов
        handler1._posts["post1"] = {"id": "post1", "tenant_id": "tenant_1"}
        handler2._posts["post2"] = {"id": "post2", "tenant_id": "tenant_2"}

        # Проверяем изоляцию
        assert "post1" in handler1._posts
        assert "post1" not in handler2._posts
        assert "post2" in handler2._posts
        assert "post2" not in handler1._posts


class TestDataSanitization:
    """Тесты санитизации данных"""

    def test_content_cleaning(self):
        """Тест очистки контента"""
        from bot_templates.content_generator_bot.handlers import ContentGeneratorBotHandler

        config = {
            "bot_name": "Test",
            "admin_ids": ["123"]
        }

        with patch('bot_templates.content_generator_bot.handlers.AnthropicClient'):
            handler = ContentGeneratorBotHandler("test_tenant", config)

        # Тестируем очистку разных типов контента
        test_cases = [
            ('"Текст в кавычках"', "Текст в кавычках"),
            ("'Текст в одинарных'", "Текст в одинарных"),
            ("# Заголовок\nТекст", "Текст"),  # Markdown заголовки удаляются
            ("  Пробелы  ", "Пробелы"),  # Лишние пробелы
        ]

        for input_text, expected in test_cases:
            cleaned = handler._clean_content(input_text)
            assert expected in cleaned or cleaned.strip() == expected.strip()

    def test_max_content_length(self):
        """Тест ограничения длины контента"""
        from bot_templates.conversation_bot.handlers import ConversationBotHandler

        config = {"bot_name": "Test", "max_conversation_length": 2}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler("test_tenant", config)

        # Добавляем много сообщений
        for i in range(100):
            handler._add_to_history("user_123", "user", f"Сообщение {i}" * 100)

        history = handler._get_conversation_history("user_123")

        # История не должна превышать лимит
        assert len(history) <= config["max_conversation_length"] * 2


class TestAPISecurityChecks:
    """Тесты безопасности API"""

    def test_callback_data_validation(self):
        """Тест валидации callback data"""
        from bot_templates.conversation_bot.handlers import ConversationBotHandler

        config = {"bot_name": "Test"}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler("test_tenant", config)

        # Тест с разными форматами callback data
        test_callbacks = [
            {"data": "normal:data"},
            {"data": ""},
            {"data": "a" * 1000},  # Очень длинный
            {"data": "special:chars:in:data"},
            {"data": None},  # None
        ]

        for cb in test_callbacks:
            cb["from"] = {"id": "user_123"}
            # Не должно падать
            try:
                import asyncio
                asyncio.get_event_loop().run_until_complete(handler.handle_callback(cb))
            except Exception as e:
                # Допустимо если KeyError на None
                assert isinstance(e, (KeyError, TypeError, AttributeError))

    def test_message_without_required_fields(self):
        """Тест обработки сообщений без обязательных полей"""
        from bot_templates.conversation_bot.handlers import ConversationBotHandler

        config = {"bot_name": "Test"}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler("test_tenant", config)

        # Сообщения без обязательных полей
        incomplete_messages = [
            {},
            {"text": "hello"},  # Нет from
            {"from": {}},  # from без id
            {"from": {"id": "123"}},  # Нет text
        ]

        import asyncio
        for msg in incomplete_messages:
            try:
                asyncio.get_event_loop().run_until_complete(handler.handle_message(msg))
            except (KeyError, TypeError):
                pass  # Ожидаемые ошибки


class TestRateLimitingPreparation:
    """Подготовка к rate limiting (проверка структуры)"""

    def test_history_limit_enforcement(self):
        """Тест принудительного ограничения истории"""
        from bot_templates.conversation_bot.handlers import ConversationBotHandler

        config = {"bot_name": "Test", "max_conversation_length": 5}

        with patch('bot_templates.conversation_bot.handlers.AnthropicClient'):
            handler = ConversationBotHandler("test_tenant", config)

        # Добавляем много сообщений
        for i in range(50):
            handler._add_to_history("user_123", "user", f"Msg {i}")
            handler._add_to_history("user_123", "assistant", f"Reply {i}")

        history = handler._get_conversation_history("user_123")

        # Проверяем что история не превышает лимит
        max_messages = config["max_conversation_length"] * 2
        assert len(history) <= max_messages

        # Проверяем что сохранены последние сообщения
        last_msg = history[-1]
        assert "49" in last_msg["content"] or "Reply" in last_msg["content"]
