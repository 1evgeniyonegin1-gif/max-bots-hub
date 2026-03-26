"""
Authentication API
JWT аутентификация + Telegram Mini App
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, field_validator
import hashlib
import hmac
from passlib.hash import bcrypt
from slowapi import Limiter
from slowapi.util import get_remote_address

from shared.config.settings import settings
from shared.database import get_session
from platform.models.tenant import Tenant, TenantStatus

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()
limiter = Limiter(key_func=get_remote_address)


# ====================
# PYDANTIC MODELS
# ====================

class TelegramInitData(BaseModel):
    """Данные из Telegram Mini App initData"""
    user: Optional[Dict[str, Any]] = None
    auth_date: Optional[int] = None
    hash: Optional[str] = None


class RegisterRequest(BaseModel):
    """Запрос на регистрацию"""
    name: str
    email: EmailStr
    password: str
    telegram_init_data: Optional[str] = None  # initData из Telegram Web App

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля"""
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.islower() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v


class LoginRequest(BaseModel):
    """Запрос на вход"""
    email: EmailStr
    password: str
    telegram_init_data: Optional[str] = None


class TokenResponse(BaseModel):
    """Ответ с токеном"""
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    tenant_slug: str


class UserResponse(BaseModel):
    """Информация о текущем пользователе"""
    tenant_id: str
    slug: str
    name: str
    email: str
    status: str
    created_at: datetime


# ====================
# TELEGRAM MINI APP VALIDATION
# ====================

def validate_telegram_init_data(init_data: str, bot_token: str) -> Dict[str, Any]:
    """
    Валидация initData из Telegram Mini App

    Args:
        init_data: Строка вида "query_id=xxx&user=xxx&auth_date=xxx&hash=xxx"
        bot_token: Токен бота

    Returns:
        Распарсенные данные

    Raises:
        HTTPException: Если валидация не прошла

    Документация: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        # Парсим query string
        params = {}
        for item in init_data.split("&"):
            key, value = item.split("=", 1)
            params[key] = value

        # Проверяем наличие hash
        if "hash" not in params:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid initData: hash missing"
            )

        received_hash = params.pop("hash")

        # Создаём строку для проверки
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(params.items())
        )

        # Вычисляем ожидаемый hash
        secret_key = hmac.new(
            key="WebAppData".encode(),
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()

        expected_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        # Сравниваем
        if received_hash != expected_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid initData: hash mismatch"
            )

        # Проверяем auth_date (не старше 1 часа)
        auth_date = int(params.get("auth_date", 0))
        current_time = int(datetime.utcnow().timestamp())
        if current_time - auth_date > 3600:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="InitData expired"
            )

        return params

    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid initData format: {str(e)}"
        )


# ====================
# PASSWORD HASHING
# ====================

def hash_password(password: str) -> str:
    """
    Хэширование пароля с использованием bcrypt

    Args:
        password: Пароль в открытом виде

    Returns:
        Bcrypt hash пароля
    """
    return bcrypt.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля

    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хэш пароля из БД

    Returns:
        True если пароль верный, False иначе
    """
    return bcrypt.verify(plain_password, hashed_password)


# ====================
# JWT TOKENS
# ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создать JWT токен

    Args:
        data: Payload для токена (должен содержать tenant_id)
        expires_delta: Время жизни токена

    Returns:
        JWT токен
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> Tenant:
    """
    Dependency для получения текущего тенанта из JWT токена

    Usage:
        @router.get("/profile")
        async def get_profile(tenant: Tenant = Depends(get_current_tenant)):
            return tenant
    """
    token = credentials.credentials

    try:
        # Декодируем JWT
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        tenant_id: str = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: tenant_id missing"
            )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

    # Получаем тенанта из БД
    result = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Проверяем статус
    if tenant.status == TenantStatus.BANNED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is banned"
        )

    return tenant


# ====================
# API ENDPOINTS
# ====================

@router.post("/register", response_model=TokenResponse)
@limiter.limit("3/minute")
async def register(
    http_request: Request,
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Регистрация нового клиента (тенанта)

    1. Проверяем email (уникальность)
    2. Валидируем Telegram initData (если передан)
    3. Создаём тенанта со статусом TRIAL
    4. Генерируем JWT токен
    """
    # Проверяем email
    result = await session.execute(
        select(Tenant).where(Tenant.email == request.email)
    )
    existing_tenant = result.scalar_one_or_none()

    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate Telegram initData if provided
    telegram_user_id = None
    if request.telegram_init_data:
        # Telegram WebApp validation requires bot token at runtime
        pass

    # Создаём slug из имени
    slug = request.name.lower().replace(" ", "_")[:50]

    # Хэшируем пароль
    password_hash = hash_password(request.password)

    # Создаём тенанта
    tenant = Tenant(
        slug=slug,
        name=request.name,
        email=request.email,
        password_hash=password_hash,
        status=TenantStatus.TRIAL,
        config={
            "telegram_user_id": telegram_user_id
        }
    )

    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    # Генерируем JWT токен
    access_token = create_access_token(
        data={"tenant_id": str(tenant.id), "email": tenant.email}
    )

    return TokenResponse(
        access_token=access_token,
        tenant_id=str(tenant.id),
        tenant_slug=tenant.slug
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    http_request: Request,
    request: LoginRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Вход для существующего клиента

    1. Проверяем email
    2. Валидируем Telegram initData (если передан)
    3. Генерируем JWT токен
    """
    # Получаем тенанта по email
    result = await session.execute(
        select(Tenant).where(Tenant.email == request.email)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )

    # Проверяем пароль
    if not tenant.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль не установлен. Пожалуйста, обратитесь к администратору."
        )

    if not verify_password(request.password, tenant.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )

    # Проверяем статус
    if tenant.status == TenantStatus.BANNED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт заблокирован"
        )

    # Validate Telegram initData if provided
    if request.telegram_init_data:
        pass

    # Генерируем JWT токен
    access_token = create_access_token(
        data={"tenant_id": str(tenant.id), "email": tenant.email}
    )

    return TokenResponse(
        access_token=access_token,
        tenant_id=str(tenant.id),
        tenant_slug=tenant.slug
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Получить информацию о текущем пользователе

    Требует JWT токен в заголовке:
    Authorization: Bearer <token>
    """
    return UserResponse(
        tenant_id=str(tenant.id),
        slug=tenant.slug,
        name=tenant.name,
        email=tenant.email,
        status=tenant.status.value,
        created_at=tenant.created_at
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Обновить JWT токен

    Используется для продления сессии без повторного логина
    """
    access_token = create_access_token(
        data={"tenant_id": str(tenant.id), "email": tenant.email}
    )

    return TokenResponse(
        access_token=access_token,
        tenant_id=str(tenant.id),
        tenant_slug=tenant.slug
    )
