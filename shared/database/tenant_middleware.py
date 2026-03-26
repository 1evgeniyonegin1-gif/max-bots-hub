"""
Tenant Middleware для мультитенантности
Автоматическая изоляция данных через Row-Level Security (RLS)
"""
from contextvars import ContextVar
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Context variable для хранения текущего tenant_id
current_tenant_id: ContextVar[Optional[str]] = ContextVar('current_tenant_id', default=None)


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    Установить tenant_id для текущей сессии

    Это активирует Row-Level Security (RLS) фильтрацию в PostgreSQL.
    Все запросы к таблицам с RLS будут автоматически фильтроваться по tenant_id.

    Args:
        session: SQLAlchemy async session
        tenant_id: UUID тенанта

    Example:
        async with async_session_maker() as session:
            await set_tenant_context(session, "123e4567-e89b-12d3-a456-426614174000")
            # Теперь все запросы будут видеть только данные этого тенанта
            bots = await session.execute(select(BotConfig))
    """
    # Сохраняем в context variable (для debugging)
    current_tenant_id.set(tenant_id)

    # Устанавливаем в PostgreSQL session
    await session.execute(
        text(f"SET app.tenant_id = '{tenant_id}'")
    )


async def clear_tenant_context(session: AsyncSession) -> None:
    """
    Очистить tenant context (для административных операций)

    ВНИМАНИЕ: Используйте только для операций, которым нужен доступ ко всем данным!

    Args:
        session: SQLAlchemy async session
    """
    current_tenant_id.set(None)
    await session.execute(text("RESET app.tenant_id"))


def get_current_tenant_id() -> Optional[str]:
    """
    Получить текущий tenant_id из контекста

    Returns:
        tenant_id или None если не установлен
    """
    return current_tenant_id.get()


class TenantContextManager:
    """
    Context manager для автоматического управления tenant context

    Usage:
        async with TenantContextManager(session, tenant_id):
            # Все операции будут изолированы по tenant_id
            bots = await session.execute(select(BotConfig))
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self.previous_tenant_id: Optional[str] = None

    async def __aenter__(self):
        # Сохраняем предыдущий tenant_id (если был)
        self.previous_tenant_id = get_current_tenant_id()

        # Устанавливаем новый
        await set_tenant_context(self.session, self.tenant_id)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Восстанавливаем предыдущий tenant_id или очищаем
        if self.previous_tenant_id:
            await set_tenant_context(self.session, self.previous_tenant_id)
        else:
            await clear_tenant_context(self.session)


# ============================================
# FastAPI Middleware для автоматической установки tenant_id
# ============================================

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class TenantMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware для автоматической установки tenant_id из JWT токена

    Извлекает tenant_id из:
    1. JWT токена (payload["tenant_id"])
    2. Header "X-Tenant-ID" (для тестирования)

    Usage в FastAPI:
        app = FastAPI()
        app.add_middleware(TenantMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        # Пропускаем публичные эндпоинты
        if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Пропускаем авторизацию
        if request.url.path.startswith("/auth"):
            return await call_next(request)

        # Извлекаем tenant_id
        tenant_id = None

        # 1. From JWT token (extracted by auth middleware)

        # 2. Из header (для тестирования)
        tenant_id = request.headers.get("X-Tenant-ID")

        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant ID not found in request"
            )

        # Сохраняем в request state для использования в эндпоинтах
        request.state.tenant_id = tenant_id

        response = await call_next(request)
        return response


# ============================================
# Dependency для FastAPI эндпоинтов
# ============================================

from fastapi import Depends


async def get_current_tenant_from_request(request: Request) -> str:
    """
    FastAPI dependency - извлекает tenant_id из request

    Usage:
        @app.get("/bots")
        async def get_bots(
            tenant_id: str = Depends(get_current_tenant_from_request),
            session: AsyncSession = Depends(get_session)
        ):
            await set_tenant_context(session, tenant_id)
            bots = await session.execute(select(BotConfig))
            return bots.scalars().all()
    """
    if not hasattr(request.state, "tenant_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant ID not found in request state"
        )

    return request.state.tenant_id


async def get_session_with_tenant(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> AsyncSession:
    """
    FastAPI dependency - возвращает session с уже установленным tenant context

    Usage:
        @app.get("/bots")
        async def get_bots(session: AsyncSession = Depends(get_session_with_tenant)):
            # tenant_id уже установлен, можно делать запросы
            bots = await session.execute(select(BotConfig))
            return bots.scalars().all()
    """
    tenant_id = await get_current_tenant_from_request(request)
    await set_tenant_context(session, tenant_id)
    return session
