"""Live integration test hitting a real Azure AI Search service.

啟用條件 (避免在 CI / 未授權環境自動執行)：
  需設定環境變數：
    AZURE_SEARCH_LIVE=1 (或 true / yes)
    AZURE_SEARCH_SERVICE_NAME=<your search service name>
  選擇性：
    AZURE_SEARCH_API_KEY=<admin/query key>  (若未設定則使用 DefaultAzureCredential)
    AZURE_SEARCH_INDEX_NAME=<index name，預設 documents>
    AZURE_SEARCH_USE_SEMANTIC=true|false (若 semantic 設定為 true 且服務端有語意設定則會用 semantic query)
    AZURE_SEARCH_RECREATE=1  (測試前強制刪除並重建索引)

測試流程：
  1. 建立/確保索引 (可選 recreate)
  2. 上傳唯一文件 (含隨機 token)
  3. 輪詢搜尋直到文件可被查詢 (處理 Azure Search 索引延遲)
  4. 驗證結果內容 (id / title / content / metadata 解析 / score)
  5. 刪除文件 (清理)

注意：Azure Search 新增/刪除有一致性延遲，本測試僅保證『能找到』；刪除後是否立即不可見不再強制驗證。
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime
from typing import Optional

import pytest

try:
    from src.services.stable.azure_ai_search import (
        AzureSearchConfig,
        AzureAISearchExperimental,
        AZURE_SEARCH_AVAILABLE,
    )
except Exception as exc:  # pragma: no cover - import path 問題時直接 skip
    AZURE_SEARCH_AVAILABLE = False  # type: ignore
    IMPORT_ERROR = exc  # type: ignore
else:
    IMPORT_ERROR = None  # type: ignore


LIVE_FLAG = os.getenv("AZURE_SEARCH_LIVE", "").lower() in {"1", "true", "yes"}


def _require_live_prereq():  # noqa: D401 - helper
    if not AZURE_SEARCH_AVAILABLE:
        pytest.skip(f"azure-search-documents not installed: {IMPORT_ERROR}")
    if not LIVE_FLAG:
        pytest.skip("Set AZURE_SEARCH_LIVE=1 to enable live Azure AI Search test")
    if not os.getenv("AZURE_SEARCH_SERVICE_NAME"):
        pytest.skip("AZURE_SEARCH_SERVICE_NAME not set")


@pytest.fixture(scope="module")
def search_client():
    _require_live_prereq()

    service_name = os.getenv("AZURE_SEARCH_SERVICE_NAME")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")  # optional
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "documents")
    use_semantic = os.getenv("AZURE_SEARCH_USE_SEMANTIC", "true").lower() in {"1", "true", "yes"}
    recreate = os.getenv("AZURE_SEARCH_RECREATE", "").lower() in {"1", "true", "yes"}

    cfg = AzureSearchConfig(
        service_name=service_name,  # type: ignore[arg-type]
        api_key=api_key,
        index_name=index_name,
        use_semantic_search=use_semantic,
    )
    client = AzureAISearchExperimental(cfg)
    client.ensure_index(recreate=recreate)
    return client


def _poll_until_found(client: AzureAISearchExperimental, doc_id: str, token: str, *, timeout: float = 40.0, interval: float = 2.0) -> Optional[dict]:
    """輪詢搜尋直到文件可被查到或超時。

    使用關鍵字 token 作為 query_text，若回傳列表中有 id=doc_id 即成功。
    """
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            results = client.search(query_text=token, top_k=5)
        except Exception as e:  # pragma: no cover - 罕見瞬時錯誤
            last_err = e
            time.sleep(interval)
            continue
        for r in results:
            if r.get("id") == doc_id:
                return r
        time.sleep(interval)
    return None  # timeout 未找到


@pytest.mark.integration
@pytest.mark.slow
def test_live_azure_ai_search_end_to_end(search_client):
    """E2E: ensure index -> index document -> search -> validate -> delete.

    若未啟用 LIVE_FLAG 則本測試會被 skip。
    """
    client = search_client

    unique_token = f"live-e2e-{uuid.uuid4().hex[:8]}"
    doc_id = f"doc-{unique_token}"
    title = f"E2E 測試文件 {unique_token}"
    content = f"這是一份 Azure AI Search 整合測試文件，包含唯一 token {unique_token} 用於查詢驗證。"

    # 1. 上傳文件
    client.index_document(
        doc_id=doc_id,
        title=title,
        content=content,
        metadata={"purpose": "integration", "token": unique_token},
        category="integration_test",
        tags=["live", "e2e"],
        vector=[0.0] * client.config.embedding_dimensions,  # dummy vector (允許混合查詢)
        created_at=datetime.utcnow(),
    )

    # 2. 輪詢直到可搜尋到
    found = _poll_until_found(client, doc_id=doc_id, token=unique_token)
    try:
        assert found is not None, "Document not retrievable within timeout; 可能是索引延遲或設定問題"
        assert found["id"] == doc_id
        assert unique_token in found["content"]
        assert isinstance(found["score"], float)
        assert "metadata" in found and found["metadata"].get("token") == unique_token
    finally:
        # 3. 清理（不對刪除後是否完全消失做強制驗證以避免延遲）
        try:
            client.delete_document(doc_id)
        except Exception:  # pragma: no cover - 清理失敗不影響主要 assertion
            pass
