"""
AI 功能測試：測試威脅檢測和異常行為分析
對應測試計畫中的「AI 核心功能」測試用例
"""
import pytest
from unittest.mock import Mock, MagicMock
import json
from datetime import datetime
from src.services.ai_agent_service import SecurityAgent, ThreatAnalysisAgent
from src.services.vectorization_service import VectorizationService


@pytest.mark.unit
class TestThreatDetectionModule:
    """威脅檢測模組測試"""
    
    @pytest.fixture
    def mock_vectorization_service(self):
        """模擬向量化服務"""
        service = Mock()
        search_results = [
            {
                'content': '惡意IP地址 192.168.1.100 嘗試SSH暴力破解',
                'metadata': {'type': 'threat', 'severity': 'high'},
                'similarity': 0.85,
                'distance': 0.15
            },
            {
                'content': '檢測到異常登入行為，來源IP：203.0.113.45',
                'metadata': {'type': 'anomaly', 'severity': 'medium'},
                'similarity': 0.78,
                'distance': 0.22
            }
        ]
        service.search_similar = Mock(return_value=search_results)
        service.search_similar_documents = service.search_similar
        service.add_document = Mock(return_value=True)
        service.get_collection_stats = Mock(return_value={"count": 1})
        return service
    
    @pytest.fixture
    def threat_agent(self, mock_vectorization_service):
        """威脅分析Agent fixture"""
        client_mock = MagicMock()
        return ThreatAnalysisAgent(
            vectorization_service=mock_vectorization_service,
            openai_api_key="test_key",
            openai_client=client_mock,
            openai_deployment="test-deployment"
        )
    
    def test_threat_detection_with_malicious_traffic(self, threat_agent):
        """測試AI威脅檢測模組 - 異常流量識別"""
        # 準備模擬異常流量資料
        malicious_traffic_data = {
            "source_ip": "192.168.1.100",
            "destination_port": "22",
            "request_frequency": "1000 requests/min",
            "user_agent": "automated_scanner",
            "behavior": "brute_force_ssh"
        }
        
        # 模擬 OpenAI 回應
        threat_agent._openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(
                message=Mock(content=json.dumps({
                    "threat_detected": True,
                    "threat_type": "Brute Force Attack",
                    "severity": "HIGH",
                    "confidence": 0.92,
                    "description": "檢測到針對SSH服務的暴力破解攻擊",
                    "recommended_actions": [
                        "立即封鎖來源IP",
                        "加強SSH安全配置",
                        "啟用入侵檢測系統"
                    ]
                }))
            )]
        )
        
        # 執行威脅檢測
        query = f"分析這個網路流量是否為威脅: {json.dumps(malicious_traffic_data)}"
        result = threat_agent.analyze(query)
        
        # 驗證結果
        assert result['agent'] == '威脅分析Agent'
        assert 'analysis' in result
        assert 'timestamp' in result
        assert result['confidence'] > 0.7  # 信心度應該足夠高

        # 驗證向量化服務被正確調用
        threat_agent.vectorization_service.search_similar.assert_called_once()
        threat_agent._openai_client.chat.completions.create.assert_called_once()
    
    def test_anomaly_behavior_analysis(self, threat_agent):
        """測試異常行為分析模組"""
        # 準備正常與異常行為資料
        normal_behavior = {
            "user_id": "user123",
            "login_time": "09:00",
            "login_location": "辦公室",
            "access_pattern": "正常業務系統訪問"
        }
        
        anomaly_behavior = {
            "user_id": "user123", 
            "login_time": "03:00",
            "login_location": "未知地點",
            "access_pattern": "大量下載敏感文件"
        }
        
        # 模擬 OpenAI 對異常行為的回應
        threat_agent._openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(
                message=Mock(content=json.dumps({
                    "anomaly_detected": True,
                    "anomaly_type": "Suspicious Data Access",
                    "risk_score": 8.5,
                    "behavioral_changes": [
                        "非正常時間登入",
                        "異常地理位置",
                        "大量敏感資料存取"
                    ],
                    "recommendations": [
                        "立即要求重新驗證",
                        "限制敏感資料存取",
                        "啟動調查程序"
                    ]
                }))
            )]
        )
        
        # 測試異常行為識別
        query = f"分析用戶行為異常: 正常行為 {json.dumps(normal_behavior)}, 當前行為 {json.dumps(anomaly_behavior)}"
        result = threat_agent.analyze(query)
        
        # 驗證異常被正確識別
        assert result['agent'] == '威脅分析Agent'
        assert 'analysis' in result
        assert isinstance(result['timestamp'], str)
        
        # 驗證 OpenAI 被調用
        threat_agent._openai_client.chat.completions.create.assert_called_once()
    
    def test_normal_traffic_no_false_positive(self, threat_agent):
        """測試正常流量不產生誤報"""
        # 準備正常流量資料
        normal_traffic_data = {
            "source_ip": "192.168.1.50",
            "destination_port": "80",
            "request_frequency": "10 requests/min",
            "user_agent": "Mozilla/5.0",
            "behavior": "normal_web_browsing"
        }
        
        # 模擬向量化服務返回正常內容
        threat_agent.vectorization_service.search_similar.return_value = [
            {
                'content': '正常的網頁瀏覽行為',
                'metadata': {'type': 'normal', 'severity': 'low'},
                'similarity': 0.65,
                'distance': 0.35
            }
        ]
        threat_agent.vectorization_service.search_similar_documents = threat_agent.vectorization_service.search_similar
        
        threat_agent._openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(
                message=Mock(content=json.dumps({
                    "threat_detected": False,
                    "threat_type": "None",
                    "severity": "LOW",
                    "confidence": 0.95,
                    "description": "正常的網路活動，無威脅檢測",
                    "recommended_actions": []
                }))
            )]
        )

        query = f"分析網路流量: {json.dumps(normal_traffic_data)}"
        result = threat_agent.analyze(query)
        
        # 正常流量應該有低信心度的威脅檢測
        assert result['confidence'] <= 0.8
        assert 'analysis' in result
        threat_agent._openai_client.chat.completions.create.assert_called_once()


@pytest.mark.integration
class TestAIIntegrationFlow:
    """AI 整合流程測試"""
    
    @pytest.fixture
    def ai_service_stack(self):
        """AI 服務堆疊 fixture"""
        vectorization_service = Mock()
        vectorization_service.search_similar = Mock(return_value=[])
        vectorization_service.search_similar_documents = vectorization_service.search_similar
        vectorization_service.add_document = Mock(return_value=True)
        
        client_mock = MagicMock()
        threat_agent = ThreatAnalysisAgent(
            vectorization_service=vectorization_service,
            openai_api_key="test_key",
            openai_client=client_mock,
            openai_deployment="test-deployment"
        )
        
        return {
            'vectorization_service': vectorization_service,
            'threat_agent': threat_agent
        }
    
    def test_end_to_end_threat_analysis_flow(self, ai_service_stack):
        """測試端對端威脅分析流程"""
        # 設定模擬服務
        vectorization_service = ai_service_stack['vectorization_service']
        threat_agent = ai_service_stack['threat_agent']
        
        # 模擬威脅情報檢索
        vectorization_service.search_similar.return_value = [
            {
                'content': 'SQL 注入攻擊模式：SELECT * FROM users WHERE id = 1 OR 1=1',
                'metadata': {'type': 'attack_pattern', 'severity': 'high'},
                'similarity': 0.90,
                'distance': 0.1
            }
        ]
        
        # 模擬 AI 分析結果
        threat_agent._openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(
                message=Mock(content=json.dumps({
                    "threat_detected": True,
                    "threat_type": "SQL Injection",
                    "severity": "CRITICAL",
                    "confidence": 0.95,
                    "attack_vector": "Web Application",
                    "impact_assessment": "可能導致資料庫洩露",
                    "mitigation_steps": [
                        "使用參數化查詢",
                        "實施輸入驗證",
                        "部署 Web 應用防火牆"
                    ]
                }))
            )]
        )
        
        # 執行端對端分析
        suspicious_query = "SELECT * FROM users WHERE id = '1' OR '1'='1'"
        result = threat_agent.analyze(f"分析這個查詢是否為威脅: {suspicious_query}")
        
        # 驗證完整流程
        assert result['agent'] == '威脅分析Agent'
        assert 'analysis' in result
        assert 'relevant_threats' in result
        assert result['confidence'] > 0.8
        
        # 驗證服務調用順序
        vectorization_service.search_similar.assert_called_once()
        threat_agent._openai_client.chat.completions.create.assert_called_once()
    
    def test_ai_service_error_handling(self, ai_service_stack):
        """測試 AI 服務錯誤處理"""
        threat_agent = ai_service_stack['threat_agent']
        
        # 模擬向量化服務失敗
        threat_agent.vectorization_service.search_similar.side_effect = Exception("向量化服務連接失敗")

        # 即使向量化服務失敗，應該仍能進行基本分析
        threat_agent._openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(
                message=Mock(content=json.dumps({
                    "threat_detected": False,
                    "confidence": 0.3,
                    "error": "部分服務不可用，分析結果可能不完整"
                }))
            )]
        )

        result = threat_agent.analyze("測試查詢")

        # 應該返回結果，但信心度較低
        assert 'analysis' in result
        assert result['confidence'] < 0.5


@pytest.mark.performance
class TestAIPerformance:
    """AI 性能測試"""
    
    @pytest.fixture
    def performance_threat_agent(self):
        """性能測試用的威脅分析Agent"""
        vectorization_service = Mock()
        vectorization_service.search_similar = Mock(return_value=[])
        vectorization_service.search_similar_documents = vectorization_service.search_similar
        vectorization_service.add_document = Mock(return_value=True)
        
        client_mock = MagicMock()
        return ThreatAnalysisAgent(
            vectorization_service=vectorization_service,
            openai_api_key="test_key",
            openai_client=client_mock,
            openai_deployment="test-deployment"
        )
    
    def test_ai_response_time(self, performance_threat_agent):
        """測試 AI 響應時間"""
        import time
        
        # 模擬快速回應
        performance_threat_agent._openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(
                message=Mock(content='{"threat_detected": false}')
            )]
        )
        
        start_time = time.time()
        result = performance_threat_agent.analyze("測試查詢")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # AI 分析應該在合理時間內完成（不包含實際 OpenAI API 調用時間）
        assert response_time < 1.0, f"AI 響應時間過長: {response_time:.2f}s"
        assert 'analysis' in result
        performance_threat_agent._openai_client.chat.completions.create.assert_called_once()

    def test_batch_analysis_performance(self, performance_threat_agent):
        """測試批量分析性能"""
        import time
        
        performance_threat_agent._openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(
                message=Mock(content='{"threat_detected": false}')
            )]
        )
        
        # 批量分析多個查詢
        queries = [f"測試查詢 {i}" for i in range(5)]
        
        start_time = time.time()
        results = []
        for query in queries:
            result = performance_threat_agent.analyze(query)
            results.append(result)
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / len(queries)
        
        # 平均每次分析應該在合理時間內
        assert avg_time < 0.5, f"批量分析平均時間過長: {avg_time:.2f}s"
        assert len(results) == len(queries)
        
        for result in results:
            assert 'analysis' in result
        assert performance_threat_agent._openai_client.chat.completions.create.call_count == len(queries)
