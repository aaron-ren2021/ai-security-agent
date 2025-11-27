from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

from src.tools.postgres_hybrid_search import (
    PostgresHybridSearch,
    PostgresHybridSearchToolInput,
    postgres_hybrid_search_tool,
)


load_dotenv()


class PostgresHybridSearchService:
    """Singleton wrapper around Postgres hybrid search client and tool registration."""

    _instance: Optional["PostgresHybridSearchService"] = None

    def __init__(self, db_url: str, openai_api_key: str):
        self._client = PostgresHybridSearch(
            db_url=db_url,
            openai_api_key=openai_api_key,
            ts_language=os.getenv("POSTGRES_TS_LANGUAGE", "chinese"),
            default_vector_weight=float(os.getenv("POSTGRES_VECTOR_WEIGHT", "0.6")),
            default_text_weight=float(os.getenv("POSTGRES_TEXT_WEIGHT", "0.4")),
            default_vector_limit=int(os.getenv("POSTGRES_VECTOR_LIMIT", "40")),
        )
        # Register the tool so agents can call it if desired.
        postgres_hybrid_search_tool(self._client)

    @property
    def client(self) -> PostgresHybridSearch:
        return self._client

    def hybrid_search(self, input_data: PostgresHybridSearchToolInput):
        return self._client.hybrid_search(
            query=input_data.query,
            top_k=input_data.top_k,
            language=input_data.language or self._client.ts_language,
            vector_weight=input_data.vector_weight,
            text_weight=input_data.text_weight,
            vector_candidate_limit=input_data.vector_limit,
        )

    def search_query(
        self,
        query: str,
        *,
        top_k: int | None = None,
        language: str | None = None,
        vector_weight: float | None = None,
        text_weight: float | None = None,
        vector_limit: int | None = None,
    ):
        top_k = top_k or 5
        request = PostgresHybridSearchToolInput(
            query=query,
            top_k=top_k,
            language=language,
            vector_weight=vector_weight,
            text_weight=text_weight,
            vector_limit=vector_limit,
        )
        output = self.hybrid_search(request)
        return output.results

    @classmethod
    def get_instance(cls) -> Optional["PostgresHybridSearchService"]:
        if cls._instance:
            return cls._instance

        db_url = os.getenv("POSTGRES_HYBRID_DB_URL")
        openai_key = os.getenv("POSTGRES_HYBRID_OPENAI_KEY") or os.getenv("OPENAI_API_KEY")

        if not db_url or not openai_key:
            return None

        cls._instance = PostgresHybridSearchService(db_url=db_url, openai_api_key=openai_key)
        return cls._instance


def reload_postgres_service() -> Optional[PostgresHybridSearchService]:
    """Force reinitialize the service (useful for tests)."""
    PostgresHybridSearchService._instance = None
    return PostgresHybridSearchService.get_instance()
