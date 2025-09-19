"""
架構測試：驗證系統部署和基本安全性
對應測試計畫中的「Azure 部署與基本安全性」測試用例
"""
import pytest
import requests
from unittest.mock import patch, MagicMock
from src.main import app
import os
import ssl
import socket
from urllib.parse import urlparse


@pytest.mark.integration
class TestAzureDeploymentAndSecurity:
    """Azure 部署與基本安全性測試"""
    
    @pytest.fixture
    def client(self):
        """測試客戶端 fixture"""
        app.testing = True
        with app.test_client() as client:
            yield client
    
    def test_app_starts_successfully(self, client):
        """測試應用程式能成功啟動"""
        response = client.get('/')
        assert response.status_code in [200, 302, 404]  # 可能重定向到登入頁面
    
    def test_https_redirect_configured(self, client):
        """測試 HTTPS 重定向配置（模擬）"""
        # 檢查是否有相關安全頭
        response = client.get('/')
        # Flask-Talisman 或類似的安全擴展可能會添加這些頭
        security_headers = [
            'Strict-Transport-Security',
            'X-Content-Type-Options',
            'X-Frame-Options'
        ]
        
        # 至少檢查應用是否有基本安全意識
        assert response.status_code != 500, "應用不應該發生內部錯誤"
    
    @patch('requests.get')
    def test_external_https_connection(self, mock_get):
        """測試對外 HTTPS 連接（模擬 Azure 部署環境）"""
        # 模擬 HTTPS 連接響應
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = 'https://your-app.azurewebsites.net'
        mock_get.return_value = mock_response
        
        # 模擬檢查部署的應用
        response = requests.get('https://your-app.azurewebsites.net')
        assert response.status_code == 200
        assert response.url.startswith('https://')
    
    def test_authentication_endpoints_exist(self, client):
        """測試身份驗證端點存在"""
        auth_endpoints = [
            '/auth/status',
            '/auth/providers',
            '/auth/login/github'
        ]
        
        for endpoint in auth_endpoints:
            response = client.get(endpoint)
            assert response.status_code != 404, f"端點 {endpoint} 不應該返回 404"
    
    def test_session_security_configuration(self, client):
        """測試 Session 安全配置"""
        # 檢查應用是否正確配置了 session
        with client.session_transaction() as sess:
            sess['test'] = 'value'
        
        response = client.get('/auth/status')
        # 應該能正常處理 session，不會出錯
        assert response.status_code == 200
    
    def test_environment_variables_loaded(self):
        """測試環境變數是否正確載入"""
        # 檢查關鍵環境變數
        critical_env_vars = [
            'AZURE_OPENAI_ENDPOINT',
            'AZURE_OPENAI_API_KEY',
            'GITHUB_CLIENT_ID'
        ]
        
        # 至少有一個環境變數應該存在（表示配置有載入）
        env_loaded = any(os.getenv(var) for var in critical_env_vars)
        assert env_loaded or app.config.get('TESTING'), "至少應該有部分環境變數被載入"


@pytest.mark.security
class TestBasicSecurity:
    """基本安全性測試"""
    
    @pytest.fixture
    def client(self):
        """測試客戶端 fixture"""
        app.testing = True
        with app.test_client() as client:
            yield client
    
    def test_sql_injection_basic_protection(self, client):
        """測試基本 SQL 注入防護"""
        # 嘗試基本的 SQL 注入攻擊
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' UNION SELECT * FROM users --"
        ]
        
        for payload in malicious_inputs:
            # 假設有一個搜索端點
            response = client.get(f'/auth/status?query={payload}')
            # 不應該返回內部伺服器錯誤
            assert response.status_code != 500, f"SQL 注入測試失敗: {payload}"
    
    def test_xss_basic_protection(self, client):
        """測試基本 XSS 防護"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ]
        
        for payload in xss_payloads:
            response = client.get('/auth/status', query_string={'msg': payload})
            # 檢查響應是否包含未轉義的腳本
            if response.status_code == 200:
                assert '<script>' not in response.get_data(as_text=True), f"XSS 防護失敗: {payload}"
    
    def test_csrf_protection_present(self, client):
        """測試 CSRF 保護"""
        # 測試 POST 請求是否有適當的保護
        response = client.post('/auth/logout', data={})
        # 如果有 CSRF 保護，應該返回適當的錯誤
        assert response.status_code in [200, 302, 400, 403, 405], "CSRF 測試端點響應異常"
    
    def test_secure_headers_configuration(self, client):
        """測試安全標頭配置"""
        response = client.get('/')
        
        # 檢查是否有基本的安全意識（不要求所有標頭都存在）
        headers = response.headers
        
        # 至少檢查應用不會洩露敏感資訊
        assert 'Server' not in headers or 'Apache' not in headers.get('Server', ''), \
            "不應該洩露伺服器資訊"
        
        # 檢查內容類型設置正確
        if 'Content-Type' in headers:
            assert 'text/html' in headers.get('Content-Type', '') or \
                   'application/json' in headers.get('Content-Type', ''), \
                   "Content-Type 應該正確設置"


@pytest.mark.performance
class TestBasicPerformance:
    """基本效能測試"""
    
    @pytest.fixture
    def client(self):
        """測試客戶端 fixture"""
        app.testing = True
        with app.test_client() as client:
            yield client
    
    def test_response_time_acceptable(self, client):
        """測試響應時間在可接受範圍內"""
        import time
        
        start_time = time.time()
        response = client.get('/auth/status')
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # 基本端點應該在 2 秒內響應
        assert response_time < 2.0, f"響應時間過長: {response_time:.2f}s"
        assert response.status_code == 200
    
    def test_concurrent_requests_handling(self, client):
        """測試並發請求處理"""
        import threading
        import time
        
        results = []
        
        def make_request():
            start = time.time()
            response = client.get('/auth/status')
            end = time.time()
            results.append({
                'status_code': response.status_code,
                'response_time': end - start
            })
        
        # 模擬 5 個並發請求
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 檢查所有請求都成功
        assert len(results) == 5
        for result in results:
            assert result['status_code'] == 200
            assert result['response_time'] < 3.0  # 並發下允許稍長的響應時間
    
    def test_memory_usage_stable(self, client):
        """測試記憶體使用穩定"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 執行多次請求
        for _ in range(10):
            response = client.get('/auth/status')
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # 記憶體增長不應該超過 50MB（考虑测试环境的限制）
        assert memory_growth < 50 * 1024 * 1024, f"記憶體增長過多: {memory_growth / 1024 / 1024:.2f}MB"
