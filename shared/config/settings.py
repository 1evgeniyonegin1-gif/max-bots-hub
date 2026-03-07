"""
Settings configuration для MAX BOTS HUB
Все настройки из .env файла
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки платформы MAX BOTS HUB"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ====================
    # DATABASE
    # ====================
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/max_bots_hub"

    # ====================
    # APP
    # ====================
    DEBUG: bool = False
    APP_NAME: str = "MAX BOTS HUB"
    APP_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ====================
    # SECURITY
    # ====================
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней

    # ====================
    # ADMIN
    # ====================
    ADMIN_TELEGRAM_IDS: List[int] = []

    # ====================
    # AI PROVIDERS
    # ====================

    # Claude (основной)
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    CLAUDE_MAX_TOKENS: int = 4096

    # Deepseek (контент)
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # YandexGPT (резервный)
    YANDEX_SERVICE_ACCOUNT_ID: Optional[str] = None
    YANDEX_KEY_ID: Optional[str] = None
    YANDEX_PRIVATE_KEY: Optional[str] = None
    YANDEX_FOLDER_ID: Optional[str] = None
    YANDEX_MODEL: str = "yandexgpt-32k"

    # ====================
    # TELEGRAM
    # ====================
    TELEGRAM_BOT_TOKEN: Optional[str] = None  # Для админ-бота

    # ====================
    # MAX MESSENGER
    # ====================
    MAX_API_URL: str = "https://api.max.team"
    MAX_MASTER_BOT_TOKEN: Optional[str] = None  # Токен @MasterBot для регистрации ботов

    # ====================
    # PAYMENTS (СБП)
    # ====================
    SBP_ENABLED: bool = False
    SBP_MERCHANT_ID: Optional[str] = None
    SBP_SECRET_KEY: Optional[str] = None

    # ====================
    # REDIS (для кеширования)
    # ====================
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    # ====================
    # FILE STORAGE
    # ====================
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB

    # ====================
    # CORS
    # ====================
    CORS_ORIGINS: List[str] = []
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ====================
    # RATE LIMITING
    # ====================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Парсим ADMIN_TELEGRAM_IDS из строки
        if isinstance(self.ADMIN_TELEGRAM_IDS, str):
            self.ADMIN_TELEGRAM_IDS = [
                int(x.strip()) for x in self.ADMIN_TELEGRAM_IDS.split(",") if x.strip()
            ]

        # Настройка CORS в зависимости от режима
        if self.DEBUG:
            # В dev режиме разрешаем localhost
            self.CORS_ORIGINS = [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173"
            ]
        else:
            # В production только доверенные домены
            if not self.CORS_ORIGINS:
                self.CORS_ORIGINS = [
                    "https://max-bots-hub.ru",
                    "https://app.max-bots-hub.ru",
                    "https://www.max-bots-hub.ru"
                ]


# Singleton instance
settings = Settings()
