"""
RAG (Retrieval-Augmented Generation) System

Система для улучшения качества ответов AI через поиск релевантной информации
в базе знаний перед генерацией ответа.

Components:
- EmbeddingService: Создание векторных представлений текста
- VectorStore: Хранение и поиск документов по similarity
- RAGEngine: Объединение поиска и генерации
"""

from shared.rag.embeddings import EmbeddingService
from shared.rag.vector_store import VectorStore, Document
from shared.rag.rag_engine import RAGEngine

__all__ = [
    "EmbeddingService",
    "VectorStore",
    "Document",
    "RAGEngine"
]
