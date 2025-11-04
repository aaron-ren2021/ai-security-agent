from __future__ import annotations

from typing import Optional

import psycopg2
from openai import OpenAI
from pgvector.psycopg2 import register_vector
from pydantic import BaseModel, Field
from pydantic_ai import Tool


class SearchResult(BaseModel):
    id: int
    title: str
    content: str
    hybrid_score: float


class PostgresHybridSearch:
    def __init__(
        self,
        db_url: str,
        openai_api_key: str,
        *,
        embedding_model: str = "text-embedding-3-large",
        ts_language: str = "chinese",
        default_vector_weight: float = 0.6,
        default_text_weight: float = 0.4,
        default_vector_limit: int = 20,
    ) -> None:
        if default_vector_weight < 0 or default_text_weight < 0:
            raise ValueError("Weights must be non-negative.")
        if default_vector_weight == 0 and default_text_weight == 0:
            raise ValueError("At least one weight must be greater than zero.")
        if default_vector_limit < 1:
            raise ValueError("default_vector_limit must be >= 1.")

        self.db_url = db_url
        self.ts_language = ts_language
        self.vector_weight = float(default_vector_weight)
        self.text_weight = float(default_text_weight)
        self.vector_limit = int(default_vector_limit)
        self.embedding_model = embedding_model

        self.conn = psycopg2.connect(db_url)
        register_vector(self.conn)
        self.client = OpenAI(api_key=openai_api_key)

    def close(self) -> None:
        if not self.conn.closed:
            self.conn.close()

    def _ensure_connection(self) -> None:
        if self.conn.closed:
            self.conn = psycopg2.connect(self.db_url)
            register_vector(self.conn)

    def generate_embedding(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return list(response.data[0].embedding)

    def hybrid_search(
        self,
        query: str,
        *,
        top_k: int = 5,
        language: Optional[str] = None,
        vector_weight: Optional[float] = None,
        text_weight: Optional[float] = None,
        vector_candidate_limit: Optional[int] = None,
    ) -> list[SearchResult]:
        if not query.strip():
            raise ValueError("Query must not be empty.")
        if top_k < 1 or top_k > 50:
            raise ValueError("top_k must be within [1, 50].")

        vector_weight = self.vector_weight if vector_weight is None else float(vector_weight)
        text_weight = self.text_weight if text_weight is None else float(text_weight)
        if vector_weight < 0 or text_weight < 0:
            raise ValueError("Weights must be non-negative.")
        if vector_weight == 0 and text_weight == 0:
            raise ValueError("At least one weight must be greater than zero.")

        language = language or self.ts_language

        vector_limit = vector_candidate_limit if vector_candidate_limit is not None else self.vector_limit
        vector_limit = max(vector_limit, top_k)

        self._ensure_connection()
        emb = self.generate_embedding(query)
        sql = """
        WITH
        vector_results AS (
            SELECT id, 1 - (embedding <=> %s) AS vector_score
            FROM documents
            ORDER BY vector_score DESC
            LIMIT %s
        ),
        text_results AS (
            SELECT id, ts_rank(tsv, plainto_tsquery(%s::regconfig, %s)) AS text_score
            FROM documents
            WHERE tsv @@ plainto_tsquery(%s::regconfig, %s)
        )
        SELECT d.id, d.title, d.content,
               COALESCE(v.vector_score, 0) * %s + COALESCE(t.text_score, 0) * %s AS hybrid_score
        FROM documents d
        LEFT JOIN vector_results v ON d.id = v.id
        LEFT JOIN text_results t ON d.id = t.id
        WHERE COALESCE(v.vector_score, 0) > 0 OR COALESCE(t.text_score, 0) > 0
        ORDER BY hybrid_score DESC
        LIMIT %s;
        """
        with self.conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    emb,
                    vector_limit,
                    language,
                    query,
                    language,
                    query,
                    vector_weight,
                    text_weight,
                    top_k,
                ),
            )
            rows = cur.fetchall()
        return [
            SearchResult(id=row[0], title=row[1], content=row[2], hybrid_score=row[3])
            for row in rows
        ]


class PostgresHybridSearchToolInput(BaseModel):
    query: str = Field(..., description="Natural language query.")
    top_k: int = Field(5, ge=1, le=50, description="Maximum number of results to return.")
    language: Optional[str] = Field(
        None,
        description="Postgres text search configuration (e.g. 'english', 'chinese').",
    )
    vector_weight: Optional[float] = Field(
        None,
        ge=0,
        description="Weight for vector similarity in the hybrid score. Defaults to tool setting.",
    )
    text_weight: Optional[float] = Field(
        None,
        ge=0,
        description="Weight for full-text relevance in the hybrid score. Defaults to tool setting.",
    )
    vector_limit: Optional[int] = Field(
        None,
        ge=1,
        description="Number of vector candidates before re-ranking. Defaults to tool setting.",
    )


class PostgresHybridSearchToolOutput(BaseModel):
    query: str
    language: str
    vector_weight: float
    text_weight: float
    results: list[SearchResult]


def postgres_hybrid_search_tool(
    search_client: PostgresHybridSearch,
    *,
    name: str = "postgres_hybrid_search",
    description: str = "Query Postgres hybrid search index using OpenAI embeddings and pgvector.",
) -> Tool[PostgresHybridSearchToolInput, PostgresHybridSearchToolOutput]:
    @Tool.register(name=name, description=description)
    def _tool(input_data: PostgresHybridSearchToolInput) -> PostgresHybridSearchToolOutput:  # type: ignore[misc]
        vector_weight = (
            search_client.vector_weight
            if input_data.vector_weight is None
            else float(input_data.vector_weight)
        )
        text_weight = (
            search_client.text_weight
            if input_data.text_weight is None
            else float(input_data.text_weight)
        )
        language = input_data.language or search_client.ts_language

        results = search_client.hybrid_search(
            query=input_data.query,
            top_k=input_data.top_k,
            language=language,
            vector_weight=vector_weight,
            text_weight=text_weight,
            vector_candidate_limit=input_data.vector_limit,
        )
        return PostgresHybridSearchToolOutput(
            query=input_data.query,
            language=language,
            vector_weight=vector_weight,
            text_weight=text_weight,
            results=results,
        )

    return _tool
