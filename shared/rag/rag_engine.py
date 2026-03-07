"""
RAG Engine

Движок для Retrieval-Augmented Generation.
Объединяет поиск в базе знаний с генерацией ответов через AI.
"""
import logging
from typing import List, Dict, Any, Optional

from shared.rag.vector_store import VectorStore, Document, get_vector_store

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    RAG (Retrieval-Augmented Generation) Engine.

    Процесс:
    1. Получает запрос пользователя
    2. Ищет релевантные документы в базе знаний
    3. Формирует контекст из найденных документов
    4. Возвращает augmented prompt для AI

    Usage:
        engine = RAGEngine()

        # Добавить документы
        engine.add_knowledge("Текст знаний...", category="faq")

        # Получить контекст для запроса
        context = await engine.get_context("Вопрос пользователя")

        # Или augmented prompt
        prompt = await engine.augment_prompt(
            "Вопрос пользователя",
            system_prompt="Ты помощник..."
        )
    """

    def __init__(self, vector_store: Optional[VectorStore] = None):
        """
        Args:
            vector_store: Хранилище документов.
                         По умолчанию используется singleton.
        """
        self.vector_store = vector_store or get_vector_store()

        # Паттерны нерелевантного контента
        self.irrelevant_patterns = [
            "рецепт",
            "ингредиенты на порцию",
            "способ приготовления",
            "youtube.com/live",
            "vk.com/video",
            "закрытый канал",
            "рабочий канал",
        ]

        logger.info("RAGEngine initialized")

    def add_knowledge(
        self,
        content: str,
        source: str = "manual",
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Добавить знания в базу.

        Args:
            content: Текст знаний
            source: Источник (файл, URL, etc.)
            category: Категория для фильтрации
            metadata: Дополнительные данные

        Returns:
            str: ID добавленного документа
        """
        doc = Document(
            content=content,
            source=source,
            category=category,
            metadata=metadata or {}
        )
        return self.vector_store.add_document(doc)

    def add_knowledge_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Добавить несколько знаний.

        Args:
            items: Список словарей с полями:
                   - content (required)
                   - source (optional)
                   - category (optional)
                   - metadata (optional)

        Returns:
            List[str]: Список ID добавленных документов
        """
        documents = [
            Document(
                content=item["content"],
                source=item.get("source", "manual"),
                category=item.get("category", "general"),
                metadata=item.get("metadata", {})
            )
            for item in items
        ]
        return self.vector_store.add_documents(documents)

    def _is_relevant(self, content: str) -> bool:
        """Проверить релевантность контента"""
        content_lower = content.lower()
        for pattern in self.irrelevant_patterns:
            if pattern.lower() in content_lower:
                return False
        return True

    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Найти релевантные документы.

        Args:
            query: Поисковый запрос
            top_k: Максимум результатов
            category: Фильтр по категории
            min_similarity: Минимальный порог similarity

        Returns:
            List[Dict]: Результаты с document и similarity
        """
        results = self.vector_store.search(
            query=query,
            top_k=top_k * 2,  # Берём больше для фильтрации
            category=category,
            min_similarity=min_similarity
        )

        # Фильтруем нерелевантный контент
        filtered = [
            r for r in results
            if self._is_relevant(r["document"].content)
        ]

        return filtered[:top_k]

    async def get_context(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
        min_similarity: float = 0.3,
        max_context_length: int = 2000
    ) -> str:
        """
        Получить контекст из базы знаний.

        Args:
            query: Поисковый запрос
            top_k: Максимум результатов
            category: Фильтр по категории
            min_similarity: Минимальный порог similarity
            max_context_length: Максимальная длина контекста

        Returns:
            str: Форматированный контекст
        """
        results = await self.retrieve(
            query=query,
            top_k=top_k,
            category=category,
            min_similarity=min_similarity
        )

        if not results:
            return ""

        # Форматируем контекст
        context_parts = []
        current_length = 0

        for i, result in enumerate(results, 1):
            doc = result["document"]
            similarity = result["similarity"]

            # Ограничиваем длину каждого документа
            content = doc.content
            if len(content) > 600:
                content = content[:600] + "..."

            part = f"### Источник {i} (релевантность: {similarity:.0%}):\n{content}\n"

            if current_length + len(part) > max_context_length:
                break

            context_parts.append(part)
            current_length += len(part)

        if not context_parts:
            return ""

        return "\n".join([
            "## КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:",
            "",
            *context_parts,
            "",
            "## ИНСТРУКЦИЯ:",
            "- Используй информацию из контекста для ответа",
            "- НЕ копируй дословно, адаптируй под вопрос",
            "- Если контекст не релевантен, отвечай на основе общих знаний",
            ""
        ])

    async def augment_prompt(
        self,
        user_message: str,
        system_prompt: str = "",
        top_k: int = 3,
        category: Optional[str] = None,
        min_similarity: float = 0.3
    ) -> Dict[str, str]:
        """
        Создать augmented промпты для AI.

        Args:
            user_message: Сообщение пользователя
            system_prompt: Базовый системный промпт
            top_k: Максимум результатов
            category: Фильтр по категории
            min_similarity: Минимальный порог similarity

        Returns:
            Dict с полями:
                - system_prompt: Дополненный системный промпт
                - user_message: Исходное сообщение пользователя
                - has_context: bool - найден ли контекст
        """
        context = await self.get_context(
            query=user_message,
            top_k=top_k,
            category=category,
            min_similarity=min_similarity
        )

        has_context = bool(context)

        if context:
            augmented_system = f"{system_prompt}\n\n{context}"
        else:
            augmented_system = system_prompt

        return {
            "system_prompt": augmented_system,
            "user_message": user_message,
            "has_context": has_context
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику базы знаний.

        Returns:
            Dict со статистикой
        """
        categories = self.vector_store.get_categories()
        total = self.vector_store.count()

        by_category = {
            cat: self.vector_store.count(category=cat)
            for cat in categories
        }

        return {
            "total_documents": total,
            "categories": categories,
            "documents_by_category": by_category
        }

    def clear(self, category: Optional[str] = None) -> int:
        """
        Очистить базу знаний.

        Args:
            category: Если указано, удаляются только документы этой категории

        Returns:
            int: Количество удалённых документов
        """
        return self.vector_store.clear(category=category)


# Singleton instance
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Получить singleton instance RAGEngine"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
