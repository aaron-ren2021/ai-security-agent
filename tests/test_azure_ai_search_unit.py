"""Unit tests for `AzureAISearchExperimental` without hitting real Azure.

目的：
  - 覆蓋核心邏輯（index 建立、文件索引、搜尋參數組裝、錯誤處理、輔助方法）
  - 不依賴 azure-search-documents 真實套件與網路

策略：
  - 若環境未安裝 azure SDK，本測試以 monkeypatch 注入假物件，並強制 `AZURE_SEARCH_AVAILABLE=True`
  - 以 DummySearchClient / DummyIndexClient 模擬 SDK 行為
  - 驗證：
      * ensure_index() 在索引不存在時會呼叫 create_or_update_index
      * 向量長度不符時的 ValueError（index_document 與 search）
      * 索引成功 / 失敗路徑
      * search 參數（vector_queries / semantic / filter / select）與結果轉換
      * _parse_metadata 與 _collect_highlights 的解析邏輯

測試類型標記：純單元 (不標 integration)；
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest


@pytest.fixture()
def patched_module(monkeypatch):
    """Patch azure_ai_search module to use dummy clients.

    回傳已修改之模組引用，供後續建立 AzureAISearchExperimental 實例。
    """
    from src.services.stable import azure_ai_search as mod

    # 例外類別（模擬 Azure SDK 的錯誤型別）
    class DummyHttpResponseError(Exception):
        pass

    class DummyResourceNotFoundError(Exception):
        pass

    # Dummy Index Client
    class DummyIndexClient:
        def __init__(self, *, endpoint: str, credential: Any):  # noqa: D401 - mimic signature
            self.endpoint = endpoint
            self.credential = credential
            self._existing = True  # 預設存在；可由測試修改
            self.deleted = False
            self.created_index = None

        # 行為：若 _existing=False 則 get_index 擲出 ResourceNotFoundError
        def get_index(self, name: str):  # noqa: D401
            if not self._existing:
                raise DummyResourceNotFoundError("not found")
            return {"name": name}

        def create_or_update_index(self, index):  # noqa: D401
            self.created_index = index
            self._existing = True
            return index

        def delete_index(self, name: str):  # noqa: D401
            self._existing = False
            self.deleted = True

    # Dummy Search Client
    class DummySearchClient:
        def __init__(self, *, endpoint: str, index_name: str, credential: Any):  # noqa: D401
            self.endpoint = endpoint
            self.index_name = index_name
            self.credential = credential
            self.uploaded_docs: List[Dict[str, Any]] = []
            self.last_search_kwargs: Dict[str, Any] = {}
            self.deleted_ids: List[str] = []
            # 可由測試設定：上傳是否失敗
            self.force_upload_failure = False
            self.search_results: List[Dict[str, Any]] = []

        def upload_documents(self, documents: List[Dict[str, Any]]):  # noqa: D401
            doc = documents[0]
            self.uploaded_docs.append(doc)
            if self.force_upload_failure:
                return [SimpleNamespace(succeeded=False, error_message="forced failure")]
            return [SimpleNamespace(succeeded=True, error_message=None)]

        def delete_documents(self, documents: List[Dict[str, Any]]):  # noqa: D401
            self.deleted_ids.extend([d["id"] for d in documents])

        def search(self, *, search_text: str, top: int, include_total_count: bool, **kwargs):  # noqa: D401
            # 記錄傳入參數以供驗證
            self.last_search_kwargs = dict(kwargs)
            # 模擬 iterator (list 即可)
            if not self.search_results:
                # 預設回傳一筆
                self.search_results = [
                    {
                        "id": "doc1",
                        "title": "Sample Title",
                        "content": "Body",
                        "metadata_json": '{"k":"v"}',
                        "@search.score": 1.23,
                        "@search.highlights": {"content": ["Body highlight"]},
                    }
                ]
            return self.search_results

    # 認證假物件
    class DummyAzureKeyCredential:
        def __init__(self, key: str):
            self.key = key

    class DummyDefaultAzureCredential:
        def __init__(self):
            pass

    # 修改模組屬性
    monkeypatch.setattr(mod, "HttpResponseError", DummyHttpResponseError, raising=False)
    monkeypatch.setattr(mod, "ResourceNotFoundError", DummyResourceNotFoundError, raising=False)
    monkeypatch.setattr(mod, "SearchClient", DummySearchClient, raising=False)
    monkeypatch.setattr(mod, "SearchIndexClient", DummyIndexClient, raising=False)
    monkeypatch.setattr(mod, "AzureKeyCredential", DummyAzureKeyCredential, raising=False)
    monkeypatch.setattr(mod, "DefaultAzureCredential", DummyDefaultAzureCredential, raising=False)
    monkeypatch.setattr(mod, "AZURE_SEARCH_AVAILABLE", True, raising=False)

    return mod


@pytest.fixture()
def client_instance(patched_module):
    mod = patched_module
    cfg = mod.AzureSearchConfig(service_name="dummy", api_key="KEY", index_name="idx")
    client = mod.AzureAISearchExperimental(cfg)
    return mod, client


def test_ensure_index_creates_when_absent(client_instance):
    mod, client = client_instance
    # 模擬索引不存在
    client.index_client._existing = False  # type: ignore[attr-defined]
    client.ensure_index(recreate=False)
    assert client.index_client.created_index is not None  # type: ignore[attr-defined]


def test_ensure_index_recreate_forces_delete_and_create(client_instance):
    mod, client = client_instance
    # 初始存在 -> recreate=True 應刪除後再建
    assert client.index_client._existing is True  # type: ignore[attr-defined]
    client.ensure_index(recreate=True)
    # recreate=True 時，delete_index 會先標記 deleted=True，然後 _existing 會被 create_or_update_index 設回 True
    assert client.index_client.deleted is True  # type: ignore[attr-defined]
    assert client.index_client.created_index is not None  # type: ignore[attr-defined]


def test_index_document_success_and_vector_set(client_instance):
    mod, client = client_instance
    vector = [0.0] * client.config.embedding_dimensions
    client.index_document(
        doc_id="docX",
        title="T",
        content="C",
        metadata={"a": 1},
        category="cat",
        tags=["t1", "t2"],
        vector=vector,
        created_at=datetime.utcnow(),
    )
    uploaded = client.search_client.uploaded_docs[-1]  # type: ignore[attr-defined]
    assert uploaded[client.config.vector_field_name] == vector
    assert uploaded["category"] == "cat"


def test_index_document_dimension_mismatch(client_instance):
    mod, client = client_instance
    with pytest.raises(ValueError):
        client.index_document(
            doc_id="docY",
            title="T",
            content="C",
            vector=[0.0, 1.0],  # 錯誤長度
        )


def test_index_document_forced_failure(client_instance):
    mod, client = client_instance
    # 強制上傳失敗
    client.search_client.force_upload_failure = True  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError):
        client.index_document(doc_id="fail", title="T", content="C")


def test_search_parameter_construction(client_instance):
    mod, client = client_instance
    # 準備自訂回傳
    client.search_client.search_results = [  # type: ignore[attr-defined]
        {
            "id": "doc1",
            "title": "Title1",
            "content": "Alpha",
            "metadata_json": '{"role":"test"}',
            "@search.score": 0.9,
            "@search.highlights": {"content": ["Alpha highlight"]},
        }
    ]
    vector = [0.1] * client.config.embedding_dimensions
    results = client.search(
        query_text="alpha",
        query_vector=vector,
        top_k=3,
        filter="category eq 'cat'",
        semantic=True,
        select=["id", "title"],
    )
    assert len(results) == 1
    first = results[0]
    assert first["id"] == "doc1"
    assert first["score"] == pytest.approx(0.9)
    # 驗證 search kwargs
    kwargs = client.search_client.last_search_kwargs  # type: ignore[attr-defined]
    assert "vector_queries" in kwargs
    assert kwargs.get("query_type") == "semantic"
    assert kwargs.get("filter") == "category eq 'cat'"
    assert kwargs.get("select") == "id,title"


def test_search_vector_mismatch(client_instance):
    mod, client = client_instance
    with pytest.raises(ValueError):
        client.search(query_text="x", query_vector=[0.0, 0.1])


def test_search_error_path(client_instance):
    mod, client = client_instance
    # 讓 search() 擲出模擬 HttpResponseError
    class Boom(mod.HttpResponseError):  # type: ignore[attr-defined]
        pass
    def boom_search(**_):  # noqa: D401
        raise Boom("network down")
    client.search_client.search = boom_search  # type: ignore[attr-defined]
    with pytest.raises(mod.HttpResponseError):  # type: ignore[attr-defined]
        client.search(query_text="anything")


def test_parse_metadata_and_highlights_static_methods(patched_module):
    mod = patched_module
    # metadata
    assert mod.AzureAISearchExperimental._parse_metadata(None) == {}
    assert mod.AzureAISearchExperimental._parse_metadata("{\n  \"a\": 1\n}") == {"a": 1}
    # invalid json
    bad = mod.AzureAISearchExperimental._parse_metadata("not-json")
    assert "raw" in bad
    # highlights
    hs = mod.AzureAISearchExperimental._collect_highlights({"field": ["h1", "h2"]})
    assert hs == ["h1", "h2"]
    assert mod.AzureAISearchExperimental._collect_highlights(None) is None


def test_delete_document(client_instance):
    mod, client = client_instance
    client.delete_document("docZ")
    assert "docZ" in client.search_client.deleted_ids  # type: ignore[attr-defined]
