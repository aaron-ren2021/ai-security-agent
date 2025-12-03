from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from src.services.postgres_hybrid_service import PostgresHybridSearchService
from src.tools.postgres_hybrid_search import (
    PostgresHybridSearchToolInput,
    PostgresHybridSearchToolOutput,
)

router = APIRouter(prefix="/api/search/postgres", tags=["search"])


@router.post("/hybrid", response_model=PostgresHybridSearchToolOutput)
async def hybrid_search(request: PostgresHybridSearchToolInput):
    service = PostgresHybridSearchService.get_instance()
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Postgres hybrid search service is not configured. "
            "Set POSTGRES_HYBRID_DB_URL and POSTGRES_HYBRID_OPENAI_KEY.",
        )

    results = service.hybrid_search(request)

    return PostgresHybridSearchToolOutput(
        query=request.query,
        language=request.language or service.client.ts_language,
        vector_weight=request.vector_weight if request.vector_weight is not None else service.client.vector_weight,
        text_weight=request.text_weight if request.text_weight is not None else service.client.text_weight,
        results=results,
    )

