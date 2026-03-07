"""
Vector Store

Хранилище документов с поддержкой векторного поиска.
Поддерживает два режима:
1. In-memory (для разработки и небольших баз)
2. PostgreSQL + pgvector (для production)
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import numpy as np

from shared.rag.embeddings import get_embedding_service, EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """
    Документ в базе знаний.

    Attributes:
        content: Текст документа
        source: Источник (файл, URL, тип)
        category: Категория для фильтрации
        metadata: Дополнительные данные
        embedding: Векторное представление (создаётся автоматически)
        id: Уникальный ID
        created_at: Дата создания
    """
    content: str
    source: str = "manual"
    category: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь"""
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "category": self.category,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class VectorStore:
    """
    Хранилище документов с векторным поиском.

    Поддерживает:
    - Добавление документов
    - Поиск по similarity
    - Фильтрация по категории
    - In-memory хранение

    Usage:
        store = VectorStore()

        # Добавление документов
        store.add_document(Document(content="Текст...", category="faq"))
        store.add_documents([doc1, doc2])

        # Поиск
        results = store.search("запрос", top_k=5, category="faq")
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """
        Args:
            embedding_service: Сервис для создания embeddings.
                              По умолчанию используется singleton.
        """
        self.embedding_service = embedding_service or get_embedding_service()
        self._documents: Dict[str, Document] = {}

        logger.info("VectorStore initialized (in-memory mode)")

    def add_document(self, document: Document) -> str:
        """
        Добавить документ в хранилище.

        Args:
            document: Документ для добавления

        Returns:
            str: ID добавленного документа
        """
        # Создаём embedding если нет
        if document.embedding is None:
            document.embedding = self.embedding_service.get_embedding(document.content)

        self._documents[document.id] = document
        logger.debug(f"Document added: id={document.id}, category={document.category}")

        return document.id

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Добавить несколько документов.

        Args:
            documents: Список документов

        Returns:
            List[str]: Список ID добавленных документов
        """
        # Batch создание embeddings
        texts = [doc.content for doc in documents if doc.embedding is None]
        if texts:
            embeddings = self.embedding_service.get_embeddings(texts)

            embedding_idx = 0
            for doc in documents:
                if doc.embedding is None:
                    doc.embedding = embeddings[embedding_idx]
                    embedding_idx += 1

        # Добавляем в хранилище
        ids = []
        for doc in documents:
            self._documents[doc.id] = doc
            ids.append(doc.id)

        logger.info(f"Added {len(documents)} documents to store")
        return ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Поиск релевантных документов.

        Args:
            query: Поисковый запрос
            top_k: Максимальное количество результатов
            category: Фильтр по категории (опционально)
            min_similarity: Минимальный порог similarity

        Returns:
            List[Dict]: Список результатов с полями:
                - document: Document object
                - similarity: float (0-1)
        """
        if not self._documents:
            logger.debug("No documents in store")
            return []

        # Создаём embedding запроса
        query_embedding = self.embedding_service.get_embedding(query)

        # Фильтруем по категории
        candidates = list(self._documents.values())
        if category:
            candidates = [doc for doc in candidates if doc.category == category]

        if not candidates:
            logger.debug(f"No documents in category: {category}")
            return []

        # Вычисляем similarity
        results = []
        for doc in candidates:
            if doc.embedding is None:
                continue

            similarity = self.embedding_service.similarity(
                query_embedding,
                doc.embedding
            )

            if similarity >= min_similarity:
                results.append({
                    "document": doc,
                    "similarity": similarity
                })

        # Сортируем по similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # Ограничиваем количество
        results = results[:top_k]

        logger.debug(
            f"Search completed: query='{query[:50]}...', "
            f"results={len(results)}, top_similarity={results[0]['similarity'] if results else 0:.3f}"
        )

        return results

    def get_document(self, document_id: str) -> Optional[Document]:
        """
        Получить документ по ID.

        Args:
            document_id: ID документа

        Returns:
            Document или None
        """
        return self._documents.get(document_id)

    def delete_document(self, document_id: str) -> bool:
        """
        Удалить документ.

        Args:
            document_id: ID документа

        Returns:
            bool: True если документ был удалён
        """
        if document_id in self._documents:
            del self._documents[document_id]
            logger.debug(f"Document deleted: id={document_id}")
            return True
        return False

    def get_all_documents(
        self,
        category: Optional[str] = None
    ) -> List[Document]:
        """
        Получить все документы.

        Args:
            category: Фильтр по категории (опционально)

        Returns:
            List[Document]: Список документов
        """
        docs = list(self._documents.values())
        if category:
            docs = [doc for doc in docs if doc.category == category]
        return docs

    def get_categories(self) -> List[str]:
        """
        Получить список всех категорий.

        Returns:
            List[str]: Уникальные категории
        """
        return list(set(doc.category for doc in self._documents.values()))

    def count(self, category: Optional[str] = None) -> int:
        """
        Количество документов.

        Args:
            category: Фильтр по категории (опционально)

        Returns:
            int: Количество документов
        """
        if category:
            return len([d for d in self._documents.values() if d.category == category])
        return len(self._documents)

    def clear(self, category: Optional[str] = None) -> int:
        """
        Очистить хранилище.

        Args:
            category: Если указано, удаляются только документы этой категории

        Returns:
            int: Количество удалённых документов
        """
        if category:
            ids_to_delete = [
                doc_id for doc_id, doc in self._documents.items()
                if doc.category == category
            ]
            for doc_id in ids_to_delete:
                del self._documents[doc_id]
            count = len(ids_to_delete)
        else:
            count = len(self._documents)
            self._documents.clear()

        logger.info(f"Cleared {count} documents" + (f" from category '{category}'" if category else ""))
        return count


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Получить singleton instance VectorStore"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
