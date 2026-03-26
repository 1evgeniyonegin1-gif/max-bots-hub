"""
MAX BOTS HUB Platform
Главный файл FastAPI приложения
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from shared.config.settings import settings
from shared.database import init_db, close_db
from shared.database.tenant_middleware import TenantMiddleware
from platform.api import auth, bots, webhook, knowledge


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events для FastAPI

    Выполняется при старте и остановке приложения
    """
    # Startup
    print("🚀 Starting MAX BOTS HUB Platform...")
    print(f"📦 Version: {settings.APP_VERSION}")
    print(f"🗄️  Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    # Инициализация БД (только для dev - в проде используем миграции)
    if settings.DEBUG:
        print("⚠️  DEBUG mode: Creating database tables...")
        await init_db()

    yield

    # Shutdown
    print("👋 Shutting down MAX BOTS HUB Platform...")
    await close_db()


# ====================
# FASTAPI APP
# ====================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Мультитенантная SaaS-платформа для создания ботов в MAX мессенджере",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Отключаем docs в проде
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ====================
# RATE LIMITING
# ====================

# Инициализация slowapi limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ====================
# MIDDLEWARE
# ====================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Tenant isolation (автоматическая установка tenant_id)
app.add_middleware(TenantMiddleware)

# HTTPS redirect (только в production)
if not settings.DEBUG:
    app.add_middleware(HTTPSRedirectMiddleware)

# Trusted hosts (для продакшена)
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.max-bots-hub.ru", "localhost"]
    )


# ====================
# ERROR HANDLERS
# ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик ошибок"""

    if settings.DEBUG:
        # В dev режиме возвращаем детали
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        # В проде скрываем детали
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": "Something went wrong. Please contact support."
            }
        )


# ====================
# ROUTES
# ====================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health():
    """Детальный health check"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected"
    }


# Подключаем API роутеры
app.include_router(auth.router, prefix="/api/v1")
app.include_router(bots.router, prefix="/api/v1")
app.include_router(webhook.router)  # Без префикса - прямо /webhook/
app.include_router(knowledge.router, prefix="/api/v1")



# ====================
# MAIN
# ====================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "platform.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
