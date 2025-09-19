"""Azure AI Search integration tests."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on the import path for src.* modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

pytest.importorskip("flask")

from src.services.azure_search_service import (
    DocumentResult,
    get_cached_azure_search_service,
    reset_cached_azure_search_service,
)
from src.main import app
from src.routes import rag_api


@pytest.fixture(autouse=True)
def reset_search_service_cache():
    """Reset cached service before each test to avoid cross-test bleed."""
    reset_cached_azure_search_service()
    yield
    reset_cached_azure_search_service()


def test_get_cached_service_uses_cache():
    """Ensure the cached getter only instantiates the service once."""
    with patch(
        "src.services.azure_search_service.create_azure_search_service",
        autospec=True,
    ) as mock_factory:
        mock_instance = MagicMock()
        mock_factory.return_value = mock_instance

        first = get_cached_azure_search_service()
        second = get_cached_azure_search_service()
        third = get_cached_azure_search_service(force_refresh=True)

        assert first is mock_instance
        assert second is mock_instance
        assert third is mock_instance
        assert mock_factory.call_count == 2  # initial + force refresh


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client


def _prepare_rag_mocks():
    rag_api.vectorization_service = MagicMock()
    rag_api.vectorization_service.add_document.return_value = "doc_123"
    rag_api.vectorization_service.search_similar.return_value = [{
        "id": "fallback",
        "content": "example",
        "metadata": {},
    }]
    rag_api.ai_orchestrator = MagicMock()
    rag_api.azure_search_service = None


def test_add_knowledge_indexes_with_azure_search(client):
    _prepare_rag_mocks()
    mock_search = MagicMock()

    with patch.object(rag_api, "get_cached_azure_search_service", return_value=mock_search):
        response = client.post(
            "/api/rag/knowledge/add",
            json={
                "collection": "security_threats",
                "content": "SQL injection is a common vulnerability.",
                "metadata": {
                    "title": "SQL Injection",
                    "tags": ["sql", "injection"],
                },
            },
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    mock_search.index_document.assert_called_once()
    args, kwargs = mock_search.index_document.call_args
    assert kwargs["doc_id"] == "doc_123"
    assert "SQL Injection" in kwargs["title"]
    assert "SQL injection" in kwargs["content"].lower()


def test_search_endpoint_uses_azure_results(client):
    _prepare_rag_mocks()
    document_result = DocumentResult(
        id="doc1",
        title="Zero Trust Guide",
        content="Implement MFA for all accounts",
        score=0.8,
        metadata={"category": "policy"},
        highlights=["Implement **MFA**"],
    )
    mock_search = MagicMock()
    mock_search.search_documents.return_value = [document_result]

    with patch.object(rag_api, "get_cached_azure_search_service", return_value=mock_search):
        rag_api.azure_search_service = None  # force refresh within initialize_services
        response = client.post(
            "/api/rag/search",
            json={
                "query": "How to enforce MFA?",
                "top_k": 3,
            },
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["total_results"] == 1
    assert data["results"][0]["title"] == "Zero Trust Guide"
    assert data["fallback"] is None
