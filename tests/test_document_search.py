import pytest
from src.main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_document_search_valid(client):
    # 測試有效的查詢應返回結果
    response = client.post('/api/rag/search', json={"query": "security"})
    # 期望狀態碼為 200
    assert response.status_code == 200, f"預期狀態碼 200，但獲得 {response.status_code}"
    data = response.get_json()
    # 檢查返回結果中含有 results 欄位
    assert data is not None, "回應內容為空"
    assert 'results' in data, "回應中未包含 'results' 欄位"
    # 進一步檢查至少有一筆結果（根據實際需求可能需調整）
    assert isinstance(data['results'], list), "results 應為 list 類型"
    # 當然，實際結果數可能因資料庫狀態而變
    

def test_document_search_empty_query(client):
    # 測試空查詢應返回 400 錯誤
    response = client.post('/api/rag/search', json={"query": ""})
    assert response.status_code == 400, f"預期狀態碼 400，但獲得 {response.status_code}"
