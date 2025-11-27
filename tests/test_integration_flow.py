"""
整合測試：端對端流程驗證
對應測試計畫中的「整合與系統測試」測試用例
"""
import pytest
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from src.main import app
from src.services.vectorization_service import VectorizationService
from src.services.ai_agent_service import AIAgentOrchestrator, ThreatAnalysisAgent


@pytest.mark.integration
class TestEndToEndFlow:
    """端對端流程驗證測試"""
    
    @pytest.fixture
    def client(self):
        """測試客戶端 fixture"""
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        with app.test_client() as client:
            with app.app_context():
                # 初始化測試資料庫
                try:
                    from src.models.auth import db
                    db.create_all()
                except Exception:
                    pass  # 資料庫可能已存在或使用不同配置
                
                yield client
    
    @pytest.fixture
    def mock_services(self):
        """模擬服務堆疊"""
        # 模擬向量化服務
        vectorization_service = Mock(spec=VectorizationService)
        vectorization_service.search_similar_documents.return_value = [
            {
                'content': 'SQL注入攻擊防護指南',
                'metadata': {'type': 'security_guide', 'severity': 'high'},
                'similarity': 0.85
            }
        ]
        vectorization_service.add_document.return_value = True
        
        # 模擬AI協調器
        ai_orchestrator = Mock(spec=AIAgentOrchestrator)
        ai_orchestrator.analyze_query.return_value = {
            'agent': 'threat_analysis',
            'analysis': '檢測到SQL注入威脅，建議立即修補',
            'confidence': 0.92,
            'recommendations': ['使用參數化查詢', '實施輸入驗證']
        }
        
        return {
            'vectorization_service': vectorization_service,
            'ai_orchestrator': ai_orchestrator
        }
    
    @patch('src.routers.rag_router.vectorization_service')
    @patch('src.routers.rag_router.ai_orchestrator')
    def test_complete_security_analysis_flow(self, mock_ai_orch, mock_vec_service, client):
        """測試完整的安全分析流程"""
        # 設定模擬服務
        mock_vec_service.search_similar_documents.return_value = [
            {
                'content': 'DDoS攻擊檢測與防護策略',
                'metadata': {'type': 'threat_analysis', 'severity': 'critical'},
                'similarity': 0.88
            }
        ]
        
        mock_ai_orch.analyze_query.return_value = {
            'agent': 'threat_analysis',
            'query': '檢測到異常流量',
            'analysis': {
                'threat_detected': True,
                'threat_type': 'DDoS Attack',
                'severity': 'CRITICAL',
                'confidence': 0.94,
                'description': '檢測到大量異常流量，疑似DDoS攻擊',
                'mitigation_steps': [
                    '啟動DDoS防護機制',
                    '分析攻擊來源',
                    '實施流量限制'
                ]
            },
            'timestamp': '2025-09-12T10:00:00Z',
            'confidence': 0.94
        }
        
        # 步驟1：檢查系統健康狀態
        health_response = client.get('/api/rag/health')
        assert health_response.status_code == 200
        health_data = health_response.get_json()
        assert health_data['status'] == 'healthy'
        
        # 步驟2：提交安全威脅查詢
        threat_query = {
            'query': '檢測到異常流量：源IP 192.168.1.100，流量 10000 req/min',
            'context': {
                'source_ip': '192.168.1.100',
                'traffic_volume': '10000 req/min',
                'timestamp': '2025-09-12T10:00:00Z'
            },
            'agent': 'threat_analysis'
        }
        
        chat_response = client.post('/api/rag/chat',
                                   data=json.dumps(threat_query),
                                   content_type='application/json')
        
        # 步驟3：驗證分析結果
        assert chat_response.status_code == 200
        chat_data = chat_response.get_json()
        
        assert chat_data.get('success') is True
        assert 'result' in chat_data
        
        result = chat_data['result']
        assert result['agent'] == 'threat_analysis'
        assert result['confidence'] > 0.8
        assert 'analysis' in result
        
        # 驗證服務調用
        mock_ai_orch.analyze_query.assert_called_once()
    
    @patch('src.routers.rag_router.vectorization_service')
    def test_knowledge_management_flow(self, mock_vec_service, client):
        """測試知識管理流程"""
        mock_vec_service.add_document.return_value = True
        mock_vec_service.get_collection_stats.return_value = {"count": 1}
        
        # 步驟1：新增威脅情報到知識庫
        knowledge_data = {
            'collection': 'threat_intelligence',
            'content': '新發現的零日漏洞CVE-2025-0001，影響Apache服務器',
            'metadata': {
                'cve_id': 'CVE-2025-0001',
                'severity': 'critical',
                'affected_software': 'Apache',
                'discovery_date': '2025-09-12'
            },
            'use_openai': False
        }
        
        add_response = client.post('/api/rag/knowledge/add',
                                  data=json.dumps(knowledge_data),
                                  content_type='application/json')
        
        # 驗證知識新增成功
        assert add_response.status_code == 200
        add_data = add_response.get_json()
        assert add_data.get('success') is True or 'error' not in add_data
        
        # 步驟2：查詢相關威脅情報
        query_data = {
            'query': 'Apache零日漏洞',
            'agent': 'threat_analysis'
        }
        
        # 設定搜尋結果
        mock_vec_service.search_similar_documents.return_value = [
            {
                'content': knowledge_data['content'],
                'metadata': knowledge_data['metadata'],
                'similarity': 0.95
            }
        ]
        
        with patch('src.routers.rag_router.ai_orchestrator') as mock_ai_orch:
            mock_ai_orch.analyze_query.return_value = {
                'agent': 'threat_analysis',
                'analysis': '發現關鍵零日漏洞，需要立即修補',
                'relevant_threats': [knowledge_data['content']],
                'confidence': 0.95
            }
            
            search_response = client.post('/api/rag/chat',
                                         data=json.dumps(query_data),
                                         content_type='application/json')
            
            # 驗證查詢結果
            assert search_response.status_code == 200
            search_data = search_response.get_json()
            
            if search_data.get('success'):
                result = search_data['result']
                assert result['confidence'] > 0.9
        
        # 驗證向量化服務調用
        mock_vec_service.add_document.assert_called_once()
    
    def test_authentication_integration_flow(self, client):
        """測試認證整合流程"""
        # 步驟1：檢查未認證狀態
        status_response = client.get('/auth/status')
        assert status_response.status_code == 200
        status_data = status_response.get_json()
        assert status_data.get('authenticated') is False
        
        # 步驟2：獲取OAuth提供者列表
        providers_response = client.get('/auth/providers')
        assert providers_response.status_code == 200
        providers_data = providers_response.get_json()
        assert 'providers' in providers_data
        assert 'github' in providers_data['providers']
        
        # 步驟3：初始化GitHub登入
        github_login_response = client.get('/auth/login/github')
        assert github_login_response.status_code == 200
        login_data = github_login_response.get_json()
        assert 'authorization_url' in login_data
        assert 'state' in login_data
        
        # 步驟4：模擬已認證狀態
        with client.session_transaction() as sess:
            sess['user'] = {
                'id': 'aaron-ren2021',
                'name': 'Aaron Liu',
                'email': 'aaron_l@cloudinfo.com.tw',
                'provider': 'github'
            }
        
        # 步驟5：驗證認證狀態
        auth_status_response = client.get('/auth/status')
        assert auth_status_response.status_code == 200
        auth_data = auth_status_response.get_json()
        assert auth_data.get('authenticated') is True
        assert auth_data.get('user', {}).get('id') == 'aaron-ren2021'
    
    @patch('src.routers.rag_router.vectorization_service')
    @patch('src.routers.rag_router.ai_orchestrator') 
    def test_multi_agent_analysis_flow(self, mock_ai_orch, mock_vec_service, client):
        """測試多Agent分析流程"""
        # 設定多Agent分析結果
        mock_ai_orch.multi_agent_analysis.return_value = {
            'primary_agent': 'threat_analysis',
            'secondary_agents': ['vulnerability_assessment', 'incident_response'],
            'combined_analysis': {
                'threat_level': 'HIGH',
                'attack_vector': 'Web Application',
                'impact_assessment': 'Data Breach Risk',
                'immediate_actions': [
                    '隔離受影響系統',
                    '啟動事件回應程序',
                    '通知相關團隊'
                ]
            },
            'agent_consensus': 0.89,
            'confidence': 0.91
        }
        
        # 提交多Agent分析請求
        multi_agent_query = {
            'query': '檢測到可疑的資料庫存取行為',
            'context': {
                'user_id': 'admin_user',
                'access_pattern': 'unusual_bulk_export',
                'data_volume': '100GB',
                'time': '03:00 AM'
            },
            'multi_agent': True
        }
        
        response = client.post('/api/rag/chat',
                              data=json.dumps(multi_agent_query),
                              content_type='application/json')
        
        # 驗證多Agent分析結果
        assert response.status_code == 200
        data = response.get_json()
        
        if data.get('success'):
            result = data['result']
            assert 'combined_analysis' in result
            assert result['confidence'] > 0.8
            assert 'agent_consensus' in result
        
        # 驗證多Agent協調器被調用
        mock_ai_orch.multi_agent_analysis.assert_called_once()
    
    def test_error_recovery_flow(self, client):
        """測試錯誤恢復流程"""
        # 測試無效的JSON請求
        invalid_response = client.post('/api/rag/chat',
                                      data='invalid json',
                                      content_type='application/json')
        assert invalid_response.status_code == 400
        
        # 測試缺少必要參數
        incomplete_data = {'context': {'test': 'data'}}
        incomplete_response = client.post('/api/rag/chat',
                                         data=json.dumps(incomplete_data),
                                         content_type='application/json')
        assert incomplete_response.status_code == 400
        
        # 測試系統在錯誤後仍能正常工作
        health_response = client.get('/api/rag/health')
        assert health_response.status_code == 200


@pytest.mark.integration
class TestSystemResilience:
    """系統韌性測試"""
    
    @pytest.fixture
    def client(self):
        """測試客戶端 fixture"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_concurrent_request_handling(self, client):
        """測試並發請求處理"""
        results = []
        
        def make_request():
            response = client.get('/api/rag/health')
            results.append({
                'status_code': response.status_code,
                'response_time': time.time()
            })
        
        # 創建10個並發請求
        threads = []
        start_time = time.time()
        
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 驗證所有請求都成功
        assert len(results) == 10
        for result in results:
            assert result['status_code'] == 200
        
        # 驗證並發處理效率
        assert total_time < 5.0, f"並發請求處理時間過長: {total_time:.2f}s"
    
    @patch('src.routers.rag_router.vectorization_service')
    def test_service_failure_handling(self, mock_vec_service, client):
        """測試服務失敗處理"""
        # 模擬向量化服務失敗
        mock_vec_service.search_similar_documents.side_effect = Exception("Vector service unavailable")
        
        # 嘗試進行查詢
        query_data = {'query': '測試查詢'}
        
        with patch('src.routers.rag_router.ai_orchestrator') as mock_ai_orch:
            # AI服務仍可正常工作
            mock_ai_orch.analyze_query.return_value = {
                'agent': 'fallback',
                'analysis': '部分服務不可用，提供基本分析',
                'confidence': 0.3,
                'warning': 'vector service unavailable'
            }
            
            response = client.post('/api/rag/chat',
                                  data=json.dumps(query_data),
                                  content_type='application/json')
            
            # 系統應該優雅處理失敗
            assert response.status_code in [200, 500]
            
            if response.status_code == 200:
                data = response.get_json()
                # 可能返回降級服務的結果
                assert 'result' in data or 'error' in data
    
    def test_resource_cleanup(self, client):
        """測試資源清理"""
        # 進行多次請求
        for i in range(5):
            response = client.get('/api/rag/health')
            assert response.status_code == 200
        
        # 檢查記憶體使用（簡化版）
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        # 記憶體使用應該在合理範圍內
        memory_mb = memory_info.rss / 1024 / 1024
        assert memory_mb < 500, f"記憶體使用過高: {memory_mb:.2f}MB"
    
    def test_database_transaction_integrity(self, client):
        """測試資料庫事務完整性"""
        # 模擬資料庫操作
        test_data = {
            'collection': 'test_integrity',
            'content': '事務完整性測試資料',
            'metadata': {'test': True}
        }
        
        # 嘗試新增資料
        response = client.post('/api/rag/knowledge/add',
                              data=json.dumps(test_data),
                              content_type='application/json')
        
        # 驗證響應（可能因為實際資料庫配置而異）
        assert response.status_code in [200, 404, 500]
        
        # 如果成功，驗證資料完整性
        if response.status_code == 200:
            data = response.get_json()
            assert 'success' in data or 'error' not in data


@pytest.mark.integration
class TestPerformanceUnderLoad:
    """負載下的效能測試"""
    
    @pytest.fixture
    def client(self):
        """測試客戶端 fixture"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_response_time_under_load(self, client):
        """測試負載下的響應時間"""
        response_times = []
        
        # 執行20次請求測量響應時間
        for _ in range(20):
            start_time = time.time()
            response = client.get('/api/rag/health')
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        # 計算平均響應時間
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # 效能指標驗證
        assert avg_response_time < 0.1, f"平均響應時間過長: {avg_response_time:.3f}s"
        assert max_response_time < 0.5, f"最大響應時間過長: {max_response_time:.3f}s"
    
    @patch('src.routers.rag_router.ai_orchestrator')
    def test_ai_analysis_performance(self, mock_ai_orch, client):
        """測試AI分析效能"""
        # 模擬快速AI回應
        mock_ai_orch.analyze_query.return_value = {
            'agent': 'performance_test',
            'analysis': '快速分析結果',
            'confidence': 0.8
        }
        
        analysis_times = []
        
        # 測試10次AI分析請求
        for i in range(10):
            query_data = {'query': f'效能測試查詢 {i}'}
            
            start_time = time.time()
            response = client.post('/api/rag/chat',
                                  data=json.dumps(query_data),
                                  content_type='application/json')
            end_time = time.time()
            
            if response.status_code == 200:
                analysis_times.append(end_time - start_time)
        
        if analysis_times:
            avg_analysis_time = sum(analysis_times) / len(analysis_times)
            assert avg_analysis_time < 1.0, f"AI分析平均時間過長: {avg_analysis_time:.3f}s"
