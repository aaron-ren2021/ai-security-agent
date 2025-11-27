from __future__ import annotations

"""Pydantic schema definitions used by the FastAPI routers."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., description="User query content")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context for the orchestrator")
    agent: Optional[str] = Field(default=None, description="Explicit agent override")
    multi_agent: bool = Field(default=False, description="Whether to trigger multi-agent analysis")


class KnowledgeAddRequest(BaseModel):
    collection: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    use_openai: bool = True


class KnowledgeSearchRequest(BaseModel):
    collection: str
    query: str
    n_results: int = 5
    use_openai: bool = True


class AzureModelUpdateRequest(BaseModel):
    chat_model: Optional[str] = None
    embedding_model: Optional[str] = None


class AzureChatRequest(BaseModel):
    query: str
    context: Optional[Union[str, Dict[str, Any]]] = None
    analysis_type: str = "general"


class AzureEmbeddingRequest(BaseModel):
    text: str
    model: Optional[str] = None


class DocumentSearchRequest(BaseModel):
    query: str
    collection: Optional[str] = None
    top_k: int = 5
    semantic_search: bool = True
    include_vectors: bool = True
    force_refresh: bool = False


class PydanticTextRequest(BaseModel):
    query: Optional[str] = None
    text: Optional[str] = None

    def normalized_text(self) -> str:
        return self.query or self.text or ""
