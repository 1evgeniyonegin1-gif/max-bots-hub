"""
Knowledge Base API

Endpoints для управления базой знаний (RAG).
Позволяет добавлять, искать и удалять документы.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from platform.api.auth import get_current_tenant
from platform.models.tenant import Tenant
from shared.rag import RAGEngine, get_rag_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class AddDocumentRequest(BaseModel):
    """Запрос на добавление документа"""
    content: str
    source: str = "api"
    category: str = "general"
    metadata: dict = {}


class AddDocumentsBatchRequest(BaseModel):
    """Запрос на добавление нескольких документов"""
    documents: List[AddDocumentRequest]


class SearchRequest(BaseModel):
    """Запрос на поиск"""
    query: str
    top_k: int = 5
    category: Optional[str] = None
    min_similarity: float = 0.3


class DocumentResponse(BaseModel):
    """Ответ с документом"""
    id: str
    content: str
    source: str
    category: str
    metadata: dict
    similarity: Optional[float] = None


class StatsResponse(BaseModel):
    """Ответ со статистикой"""
    total_documents: int
    categories: List[str]
    documents_by_category: dict


# ============================================
# ENDPOINTS
# ============================================

@router.post("/documents", response_model=dict)
async def add_document(
    request: AddDocumentRequest,
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Добавить документ в базу знаний.

    Документ будет автоматически преобразован в embedding
    и добавлен в векторное хранилище.
    """
    try:
        engine = get_rag_engine()

        # Добавляем tenant_id в metadata для изоляции
        metadata = request.metadata.copy()
        metadata["tenant_id"] = str(tenant.id)

        doc_id = engine.add_knowledge(
            content=request.content,
            source=request.source,
            category=f"{tenant.slug}_{request.category}",  # Изоляция по tenant
            metadata=metadata
        )

        logger.info(f"Document added: id={doc_id}, tenant={tenant.slug}")

        return {"document_id": doc_id, "status": "created"}

    except Exception as e:
        logger.error(f"Failed to add document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/batch", response_model=dict)
async def add_documents_batch(
    request: AddDocumentsBatchRequest,
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Добавить несколько документов в базу знаний.
    """
    try:
        engine = get_rag_engine()

        items = []
        for doc in request.documents:
            metadata = doc.metadata.copy()
            metadata["tenant_id"] = str(tenant.id)

            items.append({
                "content": doc.content,
                "source": doc.source,
                "category": f"{tenant.slug}_{doc.category}",
                "metadata": metadata
            })

        doc_ids = engine.add_knowledge_batch(items)

        logger.info(f"Batch added: {len(doc_ids)} documents, tenant={tenant.slug}")

        return {
            "document_ids": doc_ids,
            "count": len(doc_ids),
            "status": "created"
        }

    except Exception as e:
        logger.error(f"Failed to add documents batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=List[DocumentResponse])
async def search_documents(
    request: SearchRequest,
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Поиск документов по similarity.
    """
    try:
        engine = get_rag_engine()

        # Изолируем поиск по tenant
        category = None
        if request.category:
            category = f"{tenant.slug}_{request.category}"

        results = await engine.retrieve(
            query=request.query,
            top_k=request.top_k,
            category=category,
            min_similarity=request.min_similarity
        )

        return [
            DocumentResponse(
                id=r["document"].id,
                content=r["document"].content,
                source=r["document"].source,
                category=r["document"].category.replace(f"{tenant.slug}_", ""),
                metadata=r["document"].metadata,
                similarity=r["similarity"]
            )
            for r in results
        ]

    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Получить статистику базы знаний.
    """
    try:
        engine = get_rag_engine()
        stats = engine.get_stats()

        # Фильтруем по tenant
        tenant_prefix = f"{tenant.slug}_"
        tenant_categories = [
            cat.replace(tenant_prefix, "")
            for cat in stats["categories"]
            if cat.startswith(tenant_prefix)
        ]

        tenant_by_category = {
            cat.replace(tenant_prefix, ""): count
            for cat, count in stats["documents_by_category"].items()
            if cat.startswith(tenant_prefix)
        }

        total = sum(tenant_by_category.values())

        return StatsResponse(
            total_documents=total,
            categories=tenant_categories,
            documents_by_category=tenant_by_category
        )

    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Удалить документ.
    """
    try:
        engine = get_rag_engine()

        # Проверяем что документ принадлежит tenant'у
        doc = engine.vector_store.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        if doc.metadata.get("tenant_id") != str(tenant.id):
            raise HTTPException(status_code=403, detail="Access denied")

        success = engine.vector_store.delete_document(document_id)

        if success:
            return {"status": "deleted"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_knowledge_base(
    category: Optional[str] = Query(None, description="Категория для очистки"),
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Очистить базу знаний (или только указанную категорию).
    """
    try:
        engine = get_rag_engine()

        if category:
            tenant_category = f"{tenant.slug}_{category}"
        else:
            # Удаляем все категории tenant'а
            # Сначала получаем список категорий
            stats = engine.get_stats()
            tenant_prefix = f"{tenant.slug}_"
            tenant_categories = [
                cat for cat in stats["categories"]
                if cat.startswith(tenant_prefix)
            ]

            total_deleted = 0
            for cat in tenant_categories:
                deleted = engine.clear(category=cat)
                total_deleted += deleted

            return {"deleted_count": total_deleted, "status": "cleared"}

        deleted = engine.clear(category=tenant_category)
        return {"deleted_count": deleted, "status": "cleared"}

    except Exception as e:
        logger.error(f"Failed to clear knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
