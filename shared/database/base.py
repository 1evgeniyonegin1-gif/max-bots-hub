"""
Database Base Configuration
SQLAlchemy async setup с поддержкой мультитенантности
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from shared.config.settings import settings

# Создаём async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool if settings.DEBUG else None,
    pool_size=20,
    max_overflow=10,
)

# Создаём session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Базовый класс для моделей
Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для FastAPI - создаёт и возвращает async сессию

    Usage:
        @app.get("/")
        async def endpoint(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Инициализация базы данных - создание всех таблиц

    ВАЖНО: Это только для разработки!
    В продакшене используйте Alembic миграции.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Закрытие connection pool"""
    await engine.dispose()
