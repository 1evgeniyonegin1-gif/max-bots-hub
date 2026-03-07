"""
Pytest Configuration and Fixtures

Общие фикстуры для тестирования MAX BOTS HUB
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
import uuid

# Настройка тестовых переменных окружения
import os
os.environ["DEBUG"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key-32-characters!!"
os.environ["ANTHROPIC_API_KEY"] = "test-api-key"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Создать event loop для async тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_ai_client():
    """Mock AI клиент"""
    client = MagicMock()
    client.chat = AsyncMock(return_value="Тестовый ответ от AI")
    return client


@pytest.fixture
def sample_tenant_id() -> str:
    """Тестовый tenant ID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_bot_config():
    """Тестовый конфиг бота"""
    return {
        "bot_name": "Test Bot",
        "greeting": "Привет! Я тестовый бот.",
        "persona": "friendly",
        "ai_provider": "claude",
        "enable_rag": False
    }


@pytest.fixture
def sample_message():
    """Тестовое сообщение"""
    return {
        "message_id": 123,
        "from": {
            "id": "user_123",
            "username": "test_user",
            "first_name": "Test"
        },
        "chat": {
            "id": "chat_123",
            "type": "private"
        },
        "text": "Привет!",
        "date": 1234567890
    }


@pytest.fixture
def sample_callback():
    """Тестовый callback query"""
    return {
        "id": "callback_123",
        "from": {
            "id": "user_123",
            "username": "test_user"
        },
        "data": "test:action",
        "message": {
            "message_id": 123,
            "chat": {"id": "chat_123"}
        }
    }


@pytest.fixture
def sample_document():
    """Тестовый документ для RAG"""
    return {
        "content": "Это тестовый документ для базы знаний. Он содержит важную информацию.",
        "source": "test",
        "category": "general",
        "metadata": {"test": True}
    }
