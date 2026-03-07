"""
Embedding Service

Сервис для создания векторных представлений (embeddings) текста.
Использует sentence-transformers для локальной генерации.
"""
import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Lazy loading для тяжёлых библиотек
_model = None
_model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class EmbeddingService:
    """
    Сервис для создания embeddings текста.

    Использует модель paraphrase-multilingual-MiniLM-L12-v2:
    - Размер embedding: 384D
    - Поддержка русского языка
    - Быстрая генерация

    Usage:
        service = EmbeddingService()
        embedding = service.get_embedding("Текст для векторизации")
        embeddings = service.get_embeddings(["Текст 1", "Текст 2"])
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Args:
            model_name: Название модели из sentence-transformers.
                       По умолчанию: paraphrase-multilingual-MiniLM-L12-v2
        """
        self.model_name = model_name or _model_name
        self._model = None

    def _load_model(self):
        """Ленивая загрузка модели"""
        global _model

        if _model is not None:
            self._model = _model
            return

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            _model = SentenceTransformer(self.model_name)
            self._model = _model
            logger.info("Embedding model loaded successfully")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            raise

    def get_embedding(self, text: str) -> List[float]:
        """
        Получить embedding для одного текста.

        Args:
            text: Текст для векторизации

        Returns:
            List[float]: Вектор размерности 384
        """
        if self._model is None:
            self._load_model()

        # Ограничиваем длину текста (модель ограничена по токенам)
        text = text[:8000]

        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Получить embeddings для списка текстов.

        Args:
            texts: Список текстов

        Returns:
            List[List[float]]: Список векторов
        """
        if self._model is None:
            self._load_model()

        # Ограничиваем длину каждого текста
        texts = [t[:8000] for t in texts]

        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Вычислить cosine similarity между двумя embeddings.

        Args:
            embedding1: Первый вектор
            embedding2: Второй вектор

        Returns:
            float: Similarity от 0 до 1
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    @property
    def embedding_dimension(self) -> int:
        """Размерность embedding вектора"""
        return 384  # Для MiniLM


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Получить singleton instance EmbeddingService"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
