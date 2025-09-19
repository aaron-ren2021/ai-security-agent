import pytest
import os
import tempfile
import json
from io import BytesIO
from src.main import app

@pytest.fixture
def client():
    """創建測試客戶端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def temp_test_file():
    """創建臨時測試文件"""
    content = "這是一個測試文件內容，包含一些安全相關的關鍵字如：SQL injection、XSS、RCE"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_file_path = f.name
    
    yield temp_file_path, content
    
    # 清理
    try:
        os.unlink(temp_file_path)
    except FileNotFoundError:
        pass

class TestFileUpload:
    """文件上傳功能測試"""
    
    def test_upload_valid_text_file(self, client, temp_test_file):
        """測試上傳有效的文本文件"""
        temp_file_path, content = temp_test_file
        
        with open(temp_file_path, 'rb') as f:
            data = {
                'file': (f, 'test_security_report.txt')
            }
            response = client.post('/api/files/upload', data=data)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'file_id' in data
        assert data['filename'] == 'test_security_report.txt'
        
    def test_upload_no_file(self, client):
        """測試沒有文件的上傳請求"""
        response = client.post('/api/files/upload', data={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert '沒有找到文件' in data['error']
        
    def test_upload_empty_filename(self, client):
        """測試空文件名的上傳請求"""
        data = {
            'file': (BytesIO(b'test content'), '')
        }
        response = client.post('/api/files/upload', data=data)
        
        assert response.status_code == 400
        data = response.get_json()
        assert '沒有選擇文件' in data['error']
        
    def test_upload_unsupported_file_type(self, client):
        """測試不支援的文件類型"""
        data = {
            'file': (BytesIO(b'test content'), 'test.exe')
        }
        response = client.post('/api/files/upload', data=data)
        
        assert response.status_code == 400
        data = response.get_json()
        assert '不支援的文件類型' in data['error']

class TestFileManagement:
    """文件管理功能測試"""
    
    def test_list_documents_empty(self, client):
        """測試列出文件 - 空列表"""
        response = client.get('/api/files/documents')
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        
    def test_upload_and_list_documents(self, client, temp_test_file):
        """測試上傳文件後列出文件"""
        temp_file_path, content = temp_test_file
        
        # 上傳文件
        with open(temp_file_path, 'rb') as f:
            upload_data = {
                'file': (f, 'security_analysis.txt')
            }
            upload_response = client.post('/api/files/upload', data=upload_data)
        
        assert upload_response.status_code == 200
        upload_result = upload_response.get_json()
        file_id = upload_result['file_id']
        
        # 列出文件
        list_response = client.get('/api/files/documents')
        assert list_response.status_code == 200
        
        documents = list_response.get_json()
        assert len(documents) >= 1
        
        # 檢查上傳的文件是否在列表中
        uploaded_doc = next((doc for doc in documents if doc['id'] == file_id), None)
        assert uploaded_doc is not None
        assert uploaded_doc['filename'] == 'security_analysis.txt'
        
    def test_get_document_details(self, client, temp_test_file):
        """測試獲取文件詳細信息"""
        temp_file_path, content = temp_test_file
        
        # 上傳文件
        with open(temp_file_path, 'rb') as f:
            upload_data = {
                'file': (f, 'vulnerability_report.txt')
            }
            upload_response = client.post('/api/files/upload', data=upload_data)
        
        upload_result = upload_response.get_json()
        file_id = upload_result['file_id']
        
        # 獲取文件詳細信息
        detail_response = client.get(f'/api/files/documents/{file_id}')
        assert detail_response.status_code == 200
        
        document = detail_response.get_json()
        assert document['id'] == file_id
        assert document['filename'] == 'vulnerability_report.txt'
        assert 'content' in document
        assert 'created_at' in document
        
    def test_get_nonexistent_document(self, client):
        """測試獲取不存在的文件"""
        response = client.get('/api/files/documents/nonexistent-id')
        
        assert response.status_code == 404
        data = response.get_json()
        assert '文件不存在' in data['error']

class TestFileSearch:
    """文件搜尋功能測試"""
    
    def test_search_documents_valid_query(self, client, temp_test_file):
        """測試有效的文件搜尋查詢"""
        temp_file_path, content = temp_test_file
        
        # 上傳文件
        with open(temp_file_path, 'rb') as f:
            upload_data = {
                'file': (f, 'security_vulnerabilities.txt')
            }
            upload_response = client.post('/api/files/upload', data=upload_data)
        
        assert upload_response.status_code == 200
        
        # 搜尋文件
        search_data = {'query': 'SQL injection'}
        search_response = client.post('/api/files/search', 
                                    data=json.dumps(search_data),
                                    content_type='application/json')
        
        assert search_response.status_code == 200
        search_results = search_response.get_json()
        
        assert search_results['success'] is True
        assert 'results' in search_results
        assert len(search_results['results']) >= 1
        
        # 檢查搜尋結果包含相關內容
        result = search_results['results'][0]
        assert 'snippet' in result
        assert 'score' in result
        
    def test_search_documents_no_query(self, client):
        """測試空查詢的搜尋請求"""
        search_data = {'query': ''}
        response = client.post('/api/files/search',
                             data=json.dumps(search_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert '查詢內容不能為空' in data['error']
        
    def test_search_documents_no_matches(self, client):
        """測試沒有匹配結果的搜尋"""
        search_data = {'query': 'nonexistent_content_12345'}
        response = client.post('/api/files/search',
                             data=json.dumps(search_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        search_results = response.get_json()
        assert search_results['success'] is True
        assert len(search_results['results']) == 0

class TestFileDelete:
    """文件刪除功能測試"""
    
    def test_delete_existing_document(self, client, temp_test_file):
        """測試刪除存在的文件"""
        temp_file_path, content = temp_test_file
        
        # 上傳文件
        with open(temp_file_path, 'rb') as f:
            upload_data = {
                'file': (f, 'temp_security_doc.txt')
            }
            upload_response = client.post('/api/files/upload', data=upload_data)
        
        upload_result = upload_response.get_json()
        file_id = upload_result['file_id']
        
        # 刪除文件
        delete_response = client.delete(f'/api/files/documents/{file_id}')
        assert delete_response.status_code == 200
        
        delete_result = delete_response.get_json()
        assert delete_result['success'] is True
        assert '文件已成功刪除' in delete_result['message']
        
        # 確認文件已被刪除
        get_response = client.get(f'/api/files/documents/{file_id}')
        assert get_response.status_code == 404
        
    def test_delete_nonexistent_document(self, client):
        """測試刪除不存在的文件"""
        response = client.delete('/api/files/documents/nonexistent-id')
        
        assert response.status_code == 404
        data = response.get_json()
        assert '文件不存在' in data['error']

class TestFileDownload:
    """文件下載功能測試"""
    
    def test_download_existing_document(self, client, temp_test_file):
        """測試下載存在的文件"""
        temp_file_path, content = temp_test_file
        
        # 上傳文件
        with open(temp_file_path, 'rb') as f:
            upload_data = {
                'file': (f, 'download_test.txt')
            }
            upload_response = client.post('/api/files/upload', data=upload_data)
        
        upload_result = upload_response.get_json()
        file_id = upload_result['file_id']
        
        # 下載文件
        download_response = client.get(f'/api/files/documents/{file_id}/download')
        assert download_response.status_code == 200
        
        # 檢查下載的內容
        downloaded_content = download_response.data.decode('utf-8')
        assert content in downloaded_content
        
    def test_download_nonexistent_document(self, client):
        """測試下載不存在的文件"""
        response = client.get('/api/files/documents/nonexistent-id/download')
        
        assert response.status_code == 404
        data = response.get_json()
        assert '文件不存在' in data['error']

class TestFileIntegration:
    """文件管理整合測試"""
    
    def test_complete_file_lifecycle(self, client, temp_test_file):
        """測試完整的文件生命周期"""
        temp_file_path, content = temp_test_file
        
        # 1. 上傳文件
        with open(temp_file_path, 'rb') as f:
            upload_data = {
                'file': (f, 'lifecycle_test.txt')
            }
            upload_response = client.post('/api/files/upload', data=upload_data)
        
        assert upload_response.status_code == 200
        upload_result = upload_response.get_json()
        file_id = upload_result['file_id']
        
        # 2. 列出文件（檢查文件是否存在）
        list_response = client.get('/api/files/documents')
        documents = list_response.get_json()
        assert any(doc['id'] == file_id for doc in documents)
        
        # 3. 搜尋文件
        search_data = {'query': 'SQL injection'}
        search_response = client.post('/api/files/search',
                                    data=json.dumps(search_data),
                                    content_type='application/json')
        
        search_results = search_response.get_json()
        assert search_results['success'] is True
        
        # 4. 獲取文件詳細信息
        detail_response = client.get(f'/api/files/documents/{file_id}')
        assert detail_response.status_code == 200
        
        # 5. 下載文件
        download_response = client.get(f'/api/files/documents/{file_id}/download')
        assert download_response.status_code == 200
        
        # 6. 刪除文件
        delete_response = client.delete(f'/api/files/documents/{file_id}')
        assert delete_response.status_code == 200
        
        # 7. 確認文件已被刪除
        final_detail_response = client.get(f'/api/files/documents/{file_id}')
        assert final_detail_response.status_code == 404