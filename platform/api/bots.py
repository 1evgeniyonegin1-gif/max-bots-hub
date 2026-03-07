"""
Bots API
Управление ботами клиентов
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid
from slowapi import Limiter
from slowapi.util import get_remote_address

from shared.database import get_session
from shared.database.tenant_middleware import set_tenant_context
from platform.api.auth import get_current_tenant
from platform.models.tenant import Tenant, BotConfig, BotStatus
from platform.services.bot_factory import BotFactory

router = APIRouter(prefix="/bots", tags=["Bots"])
limiter = Limiter(key_func=get_remote_address)


# ====================
# PYDANTIC MODELS
# ====================

class BotTemplateResponse(BaseModel):
    """Информация о шаблоне бота"""
    type: str
    name: str
    description: str
    config_schema: Dict[str, Any]


class CreateBotRequest(BaseModel):
    """Запрос на создание бота"""
    bot_type: str
    config: Dict[str, Any]


class UpdateBotConfigRequest(BaseModel):
    """Запрос на обновление конфига"""
    config: Dict[str, Any]


class BotResponse(BaseModel):
    """Ответ с информацией о боте"""
    id: str
    bot_type: str
    bot_name: str
    bot_username: str | None
    status: str
    config: Dict[str, Any]
    created_at: str

    class Config:
        from_attributes = True


# ====================
# API ENDPOINTS
# ====================

@router.get("/templates", response_model=List[BotTemplateResponse])
async def list_templates():
    """
    Получить список доступных шаблонов ботов

    Возвращает информацию о всех зарегистрированных типах ботов:
    - Название и описание
    - Схему конфигурации (какие поля можно настроить)
    - Доступные интеграции
    """
    templates = BotFactory.get_available_templates()

    return [
        BotTemplateResponse(
            type=bot_type,
            name=info["name"],
            description=info["description"],
            config_schema=info["config_schema"]
        )
        for bot_type, info in templates.items()
    ]


@router.post("/create", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_bot(
    http_request: Request,
    request: CreateBotRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """
    Создать нового бота из шаблона

    Процесс:
    1. Валидация конфигурации
    2. Регистрация в MAX мессенджере
    3. Сохранение в БД
    4. Возврат информации о боте

    **Требуется JWT токен**

    Example:
    ```json
    {
      "bot_type": "conversation",
      "config": {
        "bot_name": "Мой Бот",
        "greeting": "Привет!",
        "persona": "friendly"
      }
    }
    ```
    """
    # Устанавливаем tenant context
    await set_tenant_context(session, str(tenant.id))

    # Создаём фабрику
    factory = BotFactory(session)

    try:
        bot_config = await factory.create_bot(
            tenant_id=str(tenant.id),
            bot_type=request.bot_type,
            config=request.config
        )

        return BotResponse(
            id=str(bot_config.id),
            bot_type=bot_config.bot_type,
            bot_name=bot_config.bot_name,
            bot_username=bot_config.bot_username,
            status=bot_config.status.value,
            config=bot_config.config,
            created_at=bot_config.created_at.isoformat()
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/", response_model=List[BotResponse])
async def list_bots(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить список всех ботов клиента

    Возвращает только боты текущего тенанта (автоматическая фильтрация через RLS)

    **Требуется JWT токен**
    """
    # Устанавливаем tenant context
    await set_tenant_context(session, str(tenant.id))

    # Получаем ботов (RLS автоматически фильтрует по tenant_id)
    result = await session.execute(
        select(BotConfig).where(BotConfig.status != BotStatus.DELETED)
    )
    bots = result.scalars().all()

    return [
        BotResponse(
            id=str(bot.id),
            bot_type=bot.bot_type,
            bot_name=bot.bot_name,
            bot_username=bot.bot_username,
            status=bot.status.value,
            config=bot.config,
            created_at=bot.created_at.isoformat()
        )
        for bot in bots
    ]


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить информацию о конкретном боте

    **Требуется JWT токен**
    """
    # Устанавливаем tenant context
    await set_tenant_context(session, str(tenant.id))

    try:
        result = await session.execute(
            select(BotConfig).where(BotConfig.id == uuid.UUID(bot_id))
        )
        bot = result.scalar_one_or_none()

        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bot {bot_id} not found"
            )

        return BotResponse(
            id=str(bot.id),
            bot_type=bot.bot_type,
            bot_name=bot.bot_name,
            bot_username=bot.bot_username,
            status=bot.status.value,
            config=bot.config,
            created_at=bot.created_at.isoformat()
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bot_id format"
        )


@router.patch("/{bot_id}/config", response_model=BotResponse)
async def update_bot_config(
    bot_id: str,
    request: UpdateBotConfigRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """
    Обновить конфигурацию бота

    Можно обновить частично — передайте только те поля, которые хотите изменить.

    **Требуется JWT токен**

    Example:
    ```json
    {
      "config": {
        "greeting": "Новое приветствие!",
        "persona": "professional"
      }
    }
    ```
    """
    # Устанавливаем tenant context
    await set_tenant_context(session, str(tenant.id))

    factory = BotFactory(session)

    try:
        bot_config = await factory.update_bot_config(
            bot_id=bot_id,
            config=request.config
        )

        return BotResponse(
            id=str(bot_config.id),
            bot_type=bot_config.bot_type,
            bot_name=bot_config.bot_name,
            bot_username=bot_config.bot_username,
            status=bot_config.status.value,
            config=bot_config.config,
            created_at=bot_config.created_at.isoformat()
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{bot_id}/deploy", response_model=BotResponse)
async def deploy_bot(
    bot_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """
    Задеплоить бота (перевести из DRAFT в ACTIVE)

    После деплоя бот начнёт принимать и обрабатывать сообщения.

    **Требуется JWT токен**
    """
    # Устанавливаем tenant context
    await set_tenant_context(session, str(tenant.id))

    factory = BotFactory(session)

    try:
        bot_config = await factory.deploy_bot(bot_id=bot_id)

        return BotResponse(
            id=str(bot_config.id),
            bot_type=bot_config.bot_type,
            bot_name=bot_config.bot_name,
            bot_username=bot_config.bot_username,
            status=bot_config.status.value,
            config=bot_config.config,
            created_at=bot_config.created_at.isoformat()
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """
    Удалить бота

    Soft delete — бот помечается как DELETED, но не удаляется из БД.

    **Требуется JWT токен**
    """
    # Устанавливаем tenant context
    await set_tenant_context(session, str(tenant.id))

    factory = BotFactory(session)

    try:
        await factory.delete_bot(bot_id=bot_id)
        return None

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
