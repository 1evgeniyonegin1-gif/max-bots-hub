"""
Модели для хранения истории диалогов
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, TIMESTAMP, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid

from shared.database.base import Base


class ConversationMessage(Base):
    """
    История диалогов с пользователями

    Используется для:
    - Сохранения контекста диалога
    - Аналитики (какие вопросы задают)
    - Отладки (что отвечал бот)
    """
    __tablename__ = "conversation_messages"

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
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="ID пользователя в MAX"
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Роль: user или assistant"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текст сообщения"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    __table_args__ = (
        # Составной индекс для быстрого получения истории диалога
        Index(
            "idx_conversation_user_created",
            "tenant_id",
            "bot_id",
            "user_id",
            "created_at"
        ),
    )

    def __repr__(self) -> str:
        return f"<ConversationMessage(user={self.user_id}, role={self.role}, created={self.created_at})>"
