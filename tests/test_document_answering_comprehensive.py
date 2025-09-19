"""
文件回答功能完整測試套件
測試 AI 資安機器人的文件問答能力
"""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from src.main import app
from src.services.vectorization_service import VectorizationService
from src.services.ai_agent_service import AIAgentOrchestrator


class TestDocumentAnswering:
    """文件回答功能測試類別"""
    
    @pytest.fixture
    def client(self):
        """測試客戶端"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def sample_security_document(self):
        """樣本安全文件"""
        return {
            "content": """
            資訊安全弱點掃描報告
            
            高風險漏洞：
            1. SQL Injection漏洞 - CVE-2023-1234
            2. Cross-site Scripting (XSS) - CVE-2023-5678  
            3. Remote Code Execution (RCE) - CVE-2023-9999
            
            建議修復措施：
            1. 實施參數化查詢防止SQL注入
            2. 對所有用戶輸入進行適當的編碼和過濾
            3. 加強文件上傳驗證機制
            """,
            "metadata": {
                "type": "security_report",
                "date": "2025-09-18",
                "source": "vulnerability_scan"
            }
        }
    
    @pytest.mark.unit
    def test_health_endpoint(self, client):
        """測試健康檢查端點"""
        response = client.get('/api/rag/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert 'service' in data
        assert 'version' in data
    
    @pytest.mark.unit
    def test_chat_endpoint_basic(self, client):
        """測試基本聊天端點"""
        with patch('src.routes.rag_api.ai_orchestrator') as mock_orchestrator:
            mock_orchestrator.analyze_query.return_value = {
                "answer": "這是一個SQL注入漏洞，建議使用參數化查詢進行修復。",
                "confidence": 0.95,
                "sources": ["security_report_001"]
            }
            
            response = client.post('/api/rag/chat', 
                json={'query': '什麼是SQL注入漏洞？'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'result' in data
            assert 'answer' in data['result']
    
    @pytest.mark.unit
    def test_chat_endpoint_empty_query(self, client):
        """測試空查詢處理"""
        response = client.post('/api/rag/chat', json={'query': ''})
        assert response.status_code == 400
        
        data = response.get_json()
        assert 'error' in data
    
    @pytest.mark.unit
    def test_chat_endpoint_no_json(self, client):
        """測試無JSON數據處理"""
        response = client.post('/api/rag/chat')
        assert response.status_code == 400
        
        data = response.get_json()
        assert 'error' in data
    
    @pytest.mark.integration
    def test_knowledge_add_and_search_flow(self, client, sample_security_document):
        """測試知識新增和搜尋流程"""
        with patch('src.routes.rag_api.vectorization_service') as mock_vec_service:
            # 模擬文件新增成功
            mock_vec_service.add_document.return_value = "doc_123"
            
            # 新增知識
            add_response = client.post('/api/rag/knowledge/add', json={
                'collection': 'security_threats',
                'content': sample_security_document['content'],
                'metadata': sample_security_document['metadata']
            })
            
            assert add_response.status_code == 200
            add_data = add_response.get_json()
            assert add_data['success'] is True
            assert 'document_id' in add_data
            
            # 模擬搜尋結果
            mock_vec_service.search_similar.return_value = [
                {
                    "content": "SQL Injection漏洞相關內容",
                    "score": 0.95,
                    "metadata": {"type": "security_report"}
                }
            ]
            
            # 搜尋知識
            search_response = client.post('/api/rag/knowledge/search', json={
                'collection': 'security_threats',
                'query': 'SQL Injection',
                'n_results': 5
            })
            
            assert search_response.status_code == 200
            search_data = search_response.get_json()
            assert search_data['success'] is True
            assert 'results' in search_data
            assert len(search_data['results']) > 0
    
    @pytest.mark.integration
    def test_complex_security_query(self, client):
        """測試複雜安全查詢"""
        with patch('src.routes.rag_api.ai_orchestrator') as mock_orchestrator:
            mock_orchestrator.analyze_query.return_value = {
                "answer": """
                根據您的描述，這可能是一個分散式拒絕服務攻擊（DDoS）。建議採取以下措施：
                1. 立即啟動DDoS防護機制
                2. 分析流量來源並實施IP封鎖
                3. 聯繫ISP提供商協助過濾惡意流量
                4. 監控系統資源使用情況
                """,
                "confidence": 0.88,
                "sources": ["incident_response_guide", "ddos_protection_manual"],
                "threat_level": "high",
                "recommended_actions": [
                    "activate_ddos_protection",
                    "block_suspicious_ips", 
                    "contact_isp"
                ]
            }
            
            complex_query = {
                "query": "檢測到異常流量：源IP 192.168.1.100，流量 10000 req/min，如何處理？",
                "context": {
                    "current_time": "2025-09-19 10:30:00",
                    "system_status": "under_attack"
                }
            }
            
            response = client.post('/api/rag/chat', json=complex_query)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            result = data['result']
            assert 'answer' in result
            assert 'confidence' in result
            assert 'threat_level' in result
            assert result['threat_level'] == 'high'
    
    @pytest.mark.security
    def test_input_sanitization(self, client):
        """測試輸入消毒和安全性"""
        malicious_inputs = [
            "<script>alert('XSS')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "{{7*7}}",  # Template injection
            "%3Cscript%3E"  # URL encoded script
        ]
        
        with patch('src.routes.rag_api.ai_orchestrator') as mock_orchestrator:
            mock_orchestrator.analyze_query.return_value = {
                "answer": "查詢已安全處理",
                "confidence": 0.9
            }
            
            for malicious_input in malicious_inputs:
                response = client.post('/api/rag/chat', 
                    json={'query': malicious_input})
                
                # 應該要成功處理但不執行惡意代碼
                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True
                
                # 確保回應中不包含原始惡意代碼
                response_text = json.dumps(data).lower()
                assert '<script>' not in response_text
                assert 'drop table' not in response_text
    
    @pytest.mark.performance
    def test_response_time(self, client):
        """測試響應時間性能"""
        import time
        
        with patch('src.routes.rag_api.ai_orchestrator') as mock_orchestrator:
            mock_orchestrator.analyze_query.return_value = {
                "answer": "快速回應測試",
                "confidence": 0.9
            }
            
            start_time = time.time()
            response = client.post('/api/rag/chat', 
                json={'query': '什麼是防火牆？'})
            end_time = time.time()
            
            response_time = end_time - start_time
            
            assert response.status_code == 200
            # 期望響應時間小於 2 秒（在模擬環境下）
            assert response_time < 2.0
    
    @pytest.mark.unit
    def test_multi_agent_analysis(self, client):
        """測試多代理分析功能"""
        with patch('src.routes.rag_api.ai_orchestrator') as mock_orchestrator:
            mock_orchestrator.multi_agent_analysis.return_value = {
                "primary_analysis": {
                    "agent": "security_expert",
                    "answer": "這是一個嚴重的安全威脅"
                },
                "secondary_analysis": {
                    "agent": "incident_response",
                    "recommendations": ["立即隔離", "分析日誌"]
                },
                "consensus": {
                    "threat_level": "critical",
                    "confidence": 0.95
                }
            }
            
            response = client.post('/api/rag/chat', json={
                'query': '系統遭受攻擊，需要緊急處理',
                'multi_agent': True
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            result = data['result']
            assert 'primary_analysis' in result
            assert 'consensus' in result
    
    @pytest.mark.unit
    def test_knowledge_stats(self, client):
        """測試知識庫統計功能"""
        with patch('src.routes.rag_api.vectorization_service') as mock_vec_service:
            mock_vec_service.get_collection_stats.return_value = {
                "document_count": 150,
                "last_updated": "2025-09-19",
                "avg_document_length": 1250,
                "collection_size_mb": 12.5
            }
            
            response = client.get('/api/rag/knowledge/stats?collection=security_threats')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'stats' in data
            assert data['stats']['document_count'] == 150
    
    @pytest.mark.unit
    def test_error_handling(self, client):
        """測試錯誤處理"""
        with patch('src.routes.rag_api.ai_orchestrator') as mock_orchestrator:
            # 模擬服務錯誤
            mock_orchestrator.analyze_query.side_effect = Exception("AI服務暫時不可用")
            
            response = client.post('/api/rag/chat', 
                json={'query': '測試錯誤處理'})
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['success'] is False
            assert 'error' in data
    
    @pytest.mark.integration
    def test_large_document_handling(self, client):
        """測試大文件處理"""
        # 創建一個大文件內容（模擬）
        large_content = "重複內容 " * 10000  # 約10萬字符
        
        with patch('src.routes.rag_api.vectorization_service') as mock_vec_service:
            mock_vec_service.add_document.return_value = "large_doc_001"
            
            response = client.post('/api/rag/knowledge/add', json={
                'collection': 'large_documents',
                'content': large_content,
                'metadata': {'size': 'large', 'type': 'policy'}
            })
            
            # 應該能夠處理大文件
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
    
    @pytest.mark.unit  
    def test_different_languages(self, client):
        """測試多語言查詢"""
        test_queries = [
            "What is SQL injection?",  # 英文
            "什麼是SQL注入？",          # 中文
            "SQLインジェクションとは何ですか？"  # 日文
        ]
        
        with patch('src.routes.rag_api.ai_orchestrator') as mock_orchestrator:
            for query in test_queries:
                mock_orchestrator.analyze_query.return_value = {
                    "answer": f"回答：{query}",
                    "confidence": 0.9,
                    "language_detected": "auto"
                }
                
                response = client.post('/api/rag/chat', json={'query': query})
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True


class TestVectorizationService:
    """向量化服務測試"""
    
    @pytest.mark.unit
    def test_service_initialization(self):
        """測試服務初始化"""
        with patch('src.services.vectorization_service.chromadb'):
            service = VectorizationService(
                chroma_persist_directory="./test_chroma",
                openai_api_key="test_key",
                openai_api_base="test_base"
            )
            assert service is not None
            assert service.chroma_persist_directory == "./test_chroma"
    
    @pytest.mark.unit
    def test_document_processing(self):
        """測試文件處理功能"""
        with patch('src.services.vectorization_service.chromadb'):
            service = VectorizationService(
                chroma_persist_directory="./test_chroma",
                openai_api_key="test_key",
                openai_api_base="test_base"
            )
            
            # 模擬文件處理
            test_content = "這是一個測試文件內容"
            processed = service._process_document_content(test_content)
            
            assert processed is not None
            assert len(processed) > 0


class TestAIAgentOrchestrator:
    """AI代理協調器測試"""
    
    @pytest.mark.unit
    def test_agent_orchestrator_initialization(self):
        """測試AI代理協調器初始化"""
        with patch('src.services.ai_agent_service.OpenAI'):
            mock_vectorization = MagicMock()
            
            orchestrator = AIAgentOrchestrator(
                vectorization_service=mock_vectorization,
                openai_api_key="test_key",
                openai_api_base="test_base"
            )
            
            assert orchestrator is not None
            assert orchestrator.vectorization_service == mock_vectorization
    
    @pytest.mark.unit
    def test_query_analysis(self):
        """測試查詢分析功能"""
        with patch('src.services.ai_agent_service.OpenAI') as mock_openai:
            mock_vectorization = MagicMock()
            mock_vectorization.search_similar_documents.return_value = [
                {"content": "相關安全文件", "score": 0.9}
            ]
            
            # 模擬OpenAI回應
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="這是AI的回答"))
            ]
            mock_openai.return_value.chat.completions.create.return_value = mock_response
            
            orchestrator = AIAgentOrchestrator(
                vectorization_service=mock_vectorization,
                openai_api_key="test_key",
                openai_api_base="test_base"
            )
            
            result = orchestrator.analyze_query("什麼是防火牆？")
            
            assert result is not None
            assert 'answer' in result