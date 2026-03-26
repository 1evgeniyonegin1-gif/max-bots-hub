"""
MAX API Client
Интеграция с MAX Bot API (@MasterBot)
"""
import httpx
from typing import Dict, Any, Optional
from shared.config.settings import settings


class MAXAPIClient:
    """
    Клиент для работы с MAX Bot API

    Документация: https://max.team/docs/bots (если доступна)

    Usage:
        client = MAXAPIClient()
        bot_data = await client.create_bot(bot_name="My Bot", description="...")
    """

    def __init__(self, api_url: Optional[str] = None, master_token: Optional[str] = None):
        """
        Args:
            api_url: URL API MAX (по умолчанию из settings)
            master_token: Токен @MasterBot (по умолчанию из settings)
        """
        self.api_url = api_url or settings.MAX_API_URL
        self.master_token = master_token or settings.MAX_MASTER_BOT_TOKEN

        if not self.master_token:
            raise ValueError(
                "MAX_MASTER_BOT_TOKEN not configured. "
                "Please set it in .env file."
            )

        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.master_token}",
                "Content-Type": "application/json"
            }
        )

    async def create_bot(
        self,
        bot_name: str,
        description: str = "",
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создать нового бота в MAX мессенджере

        Args:
            bot_name: Название бота (минимум 11 символов, должно заканчиваться на _bot или bot)
            description: Описание бота
            tenant_id: ID тенанта (для внутреннего использования)

        Returns:
            Dict с данными бота:
            {
                "token": "bot_token_here",
                "username": "@bot_username",
                "id": "bot_id",
                "name": "Bot Name"
            }

        Raises:
            httpx.HTTPError: Если ошибка API
        """
        # Валидация названия
        if len(bot_name) < 5:
            raise ValueError("Bot name must be at least 5 characters")

        # Добавляем _bot если нужно
        if not (bot_name.endswith("_bot") or bot_name.endswith("bot")):
            bot_name = f"{bot_name}_bot"

        
        try:
            response = await self.client.post(
                "/bots/create",                json={
                    "name": bot_name,
                    "description": description,
                    "metadata": {
                        "tenant_id": tenant_id,
                        "platform": "MAX_BOTS_HUB"
                    }
                }
            )
            response.raise_for_status()
            data = response.json()

            return {
                "token": data.get("token"),
                "username": data.get("username"),
                "id": data.get("id"),
                "name": data.get("name", bot_name)
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise ValueError(f"Invalid bot name or parameters: {e.response.text}")
            elif e.response.status_code == 401:
                raise ValueError("Invalid MAX_MASTER_BOT_TOKEN")
            elif e.response.status_code == 409:
                raise ValueError(f"Bot with name '{bot_name}' already exists")
            else:
                raise RuntimeError(f"MAX API error: {e.response.text}")

    async def set_webhook(
        self,
        bot_token: str,
        webhook_url: str
    ) -> Dict[str, Any]:
        """
        Установить webhook для бота

        Args:
            bot_token: Токен бота
            webhook_url: URL вебхука (должен быть HTTPS)

        Returns:
            Dict с результатом
        """
        if not webhook_url.startswith("https://"):
            raise ValueError("Webhook URL must be HTTPS")

        try:
            response = await self.client.post(
                f"/bots/{bot_token}/webhook",                json={"url": webhook_url}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Failed to set webhook: {e.response.text}")

    async def delete_webhook(self, bot_token: str) -> Dict[str, Any]:
        """
        Удалить webhook бота

        Args:
            bot_token: Токен бота

        Returns:
            Dict с результатом
        """
        try:
            response = await self.client.delete(
                f"/bots/{bot_token}/webhook"            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Failed to delete webhook: {e.response.text}")

    async def get_bot_info(self, bot_token: str) -> Dict[str, Any]:
        """
        Получить информацию о боте

        Args:
            bot_token: Токен бота

        Returns:
            Dict с данными бота
        """
        try:
            response = await self.client.get(
                f"/bots/{bot_token}/info"            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Failed to get bot info: {e.response.text}")

    async def delete_bot(self, bot_token: str) -> Dict[str, Any]:
        """
        Удалить бота из MAX

        Args:
            bot_token: Токен бота

        Returns:
            Dict с результатом
        """
        try:
            response = await self.client.delete(
                f"/bots/{bot_token}"            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Failed to delete bot: {e.response.text}")

    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()


# ============================================
# MOCK CLIENT для тестирования (пока нет доступа к MAX API)
# ============================================

class MockMAXAPIClient(MAXAPIClient):
    """
    Mock-клиент для тестирования без реального MAX API

    Используется пока нет доступа к @MasterBot
    """

    def __init__(self):
        # Не вызываем super().__init__() чтобы не требовать токен
        self.api_url = "https://mock.max.team"
        self.master_token = "mock_token"

    async def create_bot(
        self,
        bot_name: str,
        description: str = "",
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock: Создание бота"""
        import uuid

        if not (bot_name.endswith("_bot") or bot_name.endswith("bot")):
            bot_name = f"{bot_name}_bot"

        # Генерируем fake данные
        bot_id = str(uuid.uuid4())
        bot_token = f"mock_token_{bot_id[:8]}"
        username = f"@{bot_name.replace('_', '').lower()}"

        return {
            "token": bot_token,
            "username": username,
            "id": bot_id,
            "name": bot_name
        }

    async def set_webhook(self, bot_token: str, webhook_url: str) -> Dict[str, Any]:
        """Mock: Установка webhook"""
        return {"ok": True, "webhook_url": webhook_url}

    async def delete_webhook(self, bot_token: str) -> Dict[str, Any]:
        """Mock: Удаление webhook"""
        return {"ok": True}

    async def get_bot_info(self, bot_token: str) -> Dict[str, Any]:
        """Mock: Информация о боте"""
        return {
            "token": bot_token,
            "username": "@mock_bot",
            "id": "mock_id"
        }

    async def delete_bot(self, bot_token: str) -> Dict[str, Any]:
        """Mock: Удаление бота"""
        return {"ok": True}

    async def close(self):
        """Mock: Закрытие клиента"""
        pass
