"""
Скрипт запуска MAX BOTS HUB Platform сервера
"""
import uvicorn
from shared.config.settings import settings

if __name__ == "__main__":
    print("=" * 50)
    print(f"🚀 Starting {settings.APP_NAME}")
    print(f"📦 Version: {settings.APP_VERSION}")
    print(f"🌐 URL: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"🔧 Debug: {settings.DEBUG}")
    print("=" * 50)

    uvicorn.run(
        "platform.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
