"""
Модели для хранения сгенерированного контента
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, TIMESTAMP, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from shared.database.base import Base


class PostStatus(str, enum.Enum):
    """Статусы поста"""
    PENDING = "PENDING"  # На модерации
    APPROVED = "APPROVED"  # Одобрен
    REJECTED = "REJECTED"  # Отклонён
    PUBLISHED = "PUBLISHED"  # Опубликован


class GeneratedPost(Base):
    """
    Сгенерированные посты

    Используется для:
    - Хранения постов на модерации
    - Истории публикаций
    - Аналитики (какие типы контента генерируются)
    """
    __tablename__ = "generated_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="ID тенанта"
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="ID бота"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текст поста"
    )
    post_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Тип поста (product, motivation, news, etc.)"
    )
    status: Mapped[PostStatus] = mapped_column(
        String(20),
        nullable=False,
        default=PostStatus.PENDING,
        index=True,
        comment="Статус поста"
    )
    admin_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="ID админа, который модерировал"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    moderated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
        comment="Время модерации"
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
        comment="Время публикации"
    )

    __table_args__ = (
        # Составной индекс для быстрой выборки постов на модерации
        Index(
            "idx_posts_tenant_status_created",
            "tenant_id",
            "bot_id",
            "status",
            "created_at"
        ),
    )

    def __repr__(self) -> str:
        return f"<GeneratedPost(type={self.post_type}, status={self.status}, created={self.created_at})>"
