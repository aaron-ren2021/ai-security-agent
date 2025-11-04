"""Integration-style test for experimental Azure AI Search wrapper.

Run with: pytest -k azure_ai_search -s

This test will:
1. Ensure (create or recreate) the index defined by env vars
2. Upload a sample document
3. (Optionally could query – not yet implemented in experimental wrapper)
4. Delete the sample document

Environment variables required (loaded via .env / conftest):
  AZURE_SEARCH_SERVICE_NAME
  AZURE_SEARCH_API_KEY (optional if using DefaultAzureCredential)
  AZURE_SEARCH_INDEX_NAME (defaults to 'documents' if missing)

The test auto-skips if azure-search-documents SDK is missing.
"""

from __future__ import annotations

import os
import logging
from datetime import datetime
import pytest

try:
    from src.services.stable.azure_ai_search import (
        AzureSearchConfig,
        AzureAISearchExperimental,
        AZURE_SEARCH_AVAILABLE,
    )
except Exception as exc:  # pragma: no cover - import error path
    AZURE_SEARCH_AVAILABLE = False  # type: ignore
    IMPORT_ERROR = exc  # type: ignore
else:
    IMPORT_ERROR = None  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.integration
def test_azure_ai_search_index_lifecycle():
    if not AZURE_SEARCH_AVAILABLE:
        pytest.skip(f"azure-search-documents not installed or import failed: {IMPORT_ERROR}")

    service_name = os.getenv("AZURE_SEARCH_SERVICE_NAME")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "documents")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")

    if not service_name:
        pytest.skip("AZURE_SEARCH_SERVICE_NAME not set; skipping live Azure AI Search test")

    config = AzureSearchConfig(
        service_name=service_name,
        api_key=api_key,
        index_name=index_name,
        vector_field_name="content_vector",
        embedding_dimensions=1536,
        use_semantic_search=True,
    )

    azure_search = AzureAISearchExperimental(config)

    # Step 1: ensure (re)create index
    azure_search.ensure_index(recreate=True)

    # Step 2: upload a document
    doc_id = "test-doc-azure-ai-search"
    azure_search.index_document(
        doc_id=doc_id,
        title="測試文件",
        content="這是一個測試文件的內容。Azure AI Search 上線測試。",
        metadata={"author": "pytest", "purpose": "integration"},
        category="測試",
        tags=["pytest", "integration"],
        vector=[0.0] * 1536,  # Dummy embedding
        created_at=datetime.utcnow(),
    )

    # Step 3: (future) perform a query once search API method exists.

    # Step 4: delete the document (cleanup)
    azure_search.delete_document(doc_id)

    # If no exception: success.
    assert True