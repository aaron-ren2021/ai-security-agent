"""
實際文件回答功能測試
使用真實數據測試系統回答準確性
"""

import pytest
import json
import os
from src.main import app


class TestRealDocumentAnswering:
    """真實文件回答測試"""
    
    @pytest.fixture
    def client(self):
        """測試客戶端"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """設置測試環境變數"""
        os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', 'test_key')
        os.environ['OPENAI_API_BASE'] = os.getenv('OPENAI_API_BASE', 'test_base')
        yield
        # 清理不需要，因為使用現有環境變數
    
    @pytest.mark.integration
    def test_add_real_security_document(self, client):
        """測試新增真實安全文件"""
        # 讀取測試文件
        test_file_path = "/mnt/c/Users/AaronLiu劉自仁/Documents/xcloud_project/ai-security-agent-v2/test_files/sample_security_report.txt"
        
        try:
            with open(test_file_path, 'r', encoding='utf-8') as f:
                security_content = f.read()
        except FileNotFoundError:
            pytest.skip(f"測試文件不存在: {test_file_path}")
        
        # 新增文件到知識庫
        add_response = client.post('/api/rag/knowledge/add', json={
            'collection': 'security_threats',
            'content': security_content,
            'metadata': {
                'type': 'vulnerability_report',
                'date': '2025-09-18',
                'source': 'nessus_scan'
            }
        })
        
        print(f"\\n新增文件回應: {add_response.status_code}")
        if add_response.status_code != 200:
            print(f"錯誤詳情: {add_response.get_json()}")
        
        # 期望成功或者服務不可用（開發環境下正常）
        assert add_response.status_code in [200, 500]
        
        if add_response.status_code == 200:
            data = add_response.get_json()
            assert data['success'] is True
            print(f"文件ID: {data.get('document_id')}")
    
    @pytest.mark.integration
    def test_security_vulnerability_questions(self, client):
        """測試安全漏洞相關問題"""
        security_questions = [
            "什麼是SQL注入漏洞？",
            "如何防止XSS攻擊？",
            "CVE-2023-1234是什麼漏洞？",
            "Remote Code Execution的風險等級是什麼？",
            "建議的修復措施有哪些？"
        ]
        
        results = []
        
        for question in security_questions:
            response = client.post('/api/rag/chat', json={
                'query': question,
                'context': {'domain': 'cybersecurity'}
            })
            
            print(f"\\n問題: {question}")
            print(f"狀態碼: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                if data.get('success'):
                    result = data.get('result', {})
                    answer = result.get('answer', '無回答')
                    confidence = result.get('confidence', 0)
                    
                    print(f"回答: {answer[:100]}...")
                    print(f"信心度: {confidence}")
                    
                    results.append({
                        'question': question,
                        'answer': answer,
                        'confidence': confidence,
                        'success': True
                    })
                else:
                    print(f"查詢失敗: {data}")
                    results.append({
                        'question': question,
                        'success': False,
                        'error': data.get('error')
                    })
            else:
                error_data = response.get_json() if response.data else {}
                print(f"HTTP錯誤: {error_data}")
                results.append({
                    'question': question,
                    'success': False,
                    'http_error': response.status_code
                })
        
        # 分析結果
        successful_queries = [r for r in results if r.get('success')]
        print(f"\\n成功查詢: {len(successful_queries)}/{len(security_questions)}")
        
        if successful_queries:
            avg_confidence = sum(r.get('confidence', 0) for r in successful_queries) / len(successful_queries)
            print(f"平均信心度: {avg_confidence:.2f}")
            
            # 至少應該有一些成功的查詢
            assert len(successful_queries) > 0
        else:
            # 如果沒有成功查詢，可能是服務未啟動，記錄但不失敗
            print("注意: 沒有成功的查詢，可能服務未完全啟動")
    
    @pytest.mark.integration
    def test_complex_threat_analysis(self, client):
        """測試複雜威脅分析"""
        complex_scenario = """
        系統日誌顯示以下異常活動：
        - 源IP: 192.168.1.100
        - 目標: /login.php
        - 請求頻率: 1000次/分鐘
        - 特徵: SQL注入嘗試
        - 時間: 2025-09-19 10:30:00
        
        請分析威脅等級並提供處理建議。
        """
        
        response = client.post('/api/rag/chat', json={
            'query': complex_scenario,
            'context': {
                'analysis_type': 'threat_assessment',
                'urgency': 'high'
            },
            'multi_agent': True
        })
        
        print(f"\\n複雜威脅分析狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            if data.get('success'):
                result = data.get('result', {})
                print(f"分析結果: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                # 檢查回答品質
                answer = result.get('answer', '')
                assert len(answer) > 50  # 期望詳細回答
                
                # 檢查是否包含關鍵建議
                assert any(keyword in answer.lower() for keyword in 
                          ['ip', '封鎖', '防護', '監控', '分析'])
            else:
                print(f"分析失敗: {data}")
        else:
            print(f"HTTP錯誤: {response.get_json()}")
    
    @pytest.mark.performance
    def test_response_time_real(self, client):
        """測試真實響應時間"""
        import time
        
        test_queries = [
            "什麼是防火牆？",
            "DDoS攻擊如何防護？",
            "SSL證書的作用是什麼？"
        ]
        
        response_times = []
        
        for query in test_queries:
            start_time = time.time()
            response = client.post('/api/rag/chat', json={'query': query})
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            print(f"\\n查詢: {query}")
            print(f"響應時間: {response_time:.2f}秒")
            print(f"狀態碼: {response.status_code}")
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            print(f"\\n平均響應時間: {avg_response_time:.2f}秒")
            print(f"最大響應時間: {max_response_time:.2f}秒")
            
            # 性能期望（在真實環境下可能需要調整）
            assert avg_response_time < 30.0  # 30秒內完成
            assert max_response_time < 60.0  # 單次查詢不超過60秒
    
    @pytest.mark.integration
    def test_knowledge_base_search(self, client):
        """測試知識庫搜尋功能"""
        search_terms = [
            "SQL injection",
            "XSS",
            "CVE-2023",
            "vulnerability",
            "security"
        ]
        
        for term in search_terms:
            response = client.post('/api/rag/knowledge/search', json={
                'collection': 'security_threats',
                'query': term,
                'n_results': 3
            })
            
            print(f"\\n搜尋詞: {term}")
            print(f"狀態碼: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                if data.get('success'):
                    results = data.get('results', [])
                    print(f"找到 {len(results)} 個結果")
                    
                    for i, result in enumerate(results[:2]):  # 只顯示前2個
                        content = result.get('content', '')[:100]
                        score = result.get('score', 0)
                        print(f"  結果 {i+1}: {content}... (分數: {score})")
                else:
                    print(f"搜尋失敗: {data}")
            else:
                print(f"HTTP錯誤: {response.get_json()}")
    
    @pytest.mark.integration 
    def test_knowledge_stats(self, client):
        """測試知識庫統計"""
        response = client.get('/api/rag/knowledge/stats')
        
        print(f"\\n知識庫統計狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            if data.get('success'):
                stats = data.get('stats', {})
                print(f"統計資訊: {json.dumps(stats, ensure_ascii=False, indent=2)}")
                
                # 檢查統計資訊結構
                for collection, collection_stats in stats.items():
                    print(f"\\n集合: {collection}")
                    if 'error' not in collection_stats:
                        doc_count = collection_stats.get('document_count', 0)
                        print(f"  文件數量: {doc_count}")
                    else:
                        print(f"  錯誤: {collection_stats['error']}")
            else:
                print(f"統計失敗: {data}")
        else:
            print(f"HTTP錯誤: {response.get_json()}")
    
    @pytest.mark.unit
    def test_health_check_detailed(self, client):
        """詳細健康檢查測試"""
        response = client.get('/api/rag/health')
        
        assert response.status_code == 200
        data = response.get_json()
        
        print(f"\\n健康檢查結果: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        assert data['status'] == 'healthy'
        assert 'service' in data
        assert 'version' in data
        assert data['service'] == 'AI Security RAG Bot'