"""
Модели для мультитенантности MAX BOTS HUB
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, TIMESTAMP, JSON, Enum as SQLEnum, Numeric, Boolean, Date, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import enum

from shared.database.base import Base


class TenantStatus(str, enum.Enum):
    """Статусы тенанта"""
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    BANNED = "BANNED"


class BotStatus(str, enum.Enum):
    """Статусы бота"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DELETED = "DELETED"


class SubscriptionStatus(str, enum.Enum):
    """Статусы подписки"""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class Tenant(Base):
    """Клиент платформы MAX BOTS HUB (тенант)"""
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Bcrypt hash пароля"
    )
    status: Mapped[TenantStatus] = mapped_column(
        SQLEnum(TenantStatus),
        default=TenantStatus.TRIAL,
        nullable=False,
        index=True
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    bot_configs: Mapped[list["BotConfig"]] = relationship(
        "BotConfig",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    usage_stats: Mapped[list["UsageStats"]] = relationship(
        "UsageStats",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant(slug='{self.slug}', name='{self.name}', status={self.status})>"


class BotConfig(Base):
    """Конфигурация бота клиента"""
    __tablename__ = "bot_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    bot_type: Mapped[str] = mapped_column(String(50), nullable=False)
    bot_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bot_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True
    )
    bot_username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[BotStatus] = mapped_column(
        SQLEnum(BotStatus),
        default=BotStatus.DRAFT,
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="bot_configs"
    )
    usage_stats: Mapped[list["UsageStats"]] = relationship(
        "UsageStats",
        back_populates="bot",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<BotConfig(bot_name='{self.bot_name}', type={self.bot_type}, status={self.status})>"


class Subscription(Base):
    """Подписка клиента на платформу"""
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
        index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.utcnow,
        nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
        index=True
    )
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="subscriptions"
    )

    def __repr__(self) -> str:
        return f"<Subscription(plan='{self.plan}', status={self.status})>"


class UsageStats(Base):
    """Статистика использования ботов (ежедневная)"""
    __tablename__ = "usage_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    bot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    messages_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_api_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="usage_stats"
    )
    bot: Mapped[Optional["BotConfig"]] = relationship(
        "BotConfig",
        back_populates="usage_stats"
    )

    def __repr__(self) -> str:
        return f"<UsageStats(date={self.date}, messages={self.messages_count})>"
