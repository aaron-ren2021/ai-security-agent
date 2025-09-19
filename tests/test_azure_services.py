#!/usr/bin/env python3
"""
Azure服務功能測試腳本
測試Azure OpenAI和Azure AI Search整合
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設定API基礎URL
BASE_URL = "http://localhost:5002/api/rag"

def test_health_check():
    """測試健康檢查端點"""
    print("=== 測試健康檢查 ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 健康檢查通過: {result}")
            return True
        else:
            print(f"✗ 健康檢查失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 健康檢查錯誤: {e}")
        return False

def test_config_check():
    """測試配置檢查端點"""
    print("\n=== 測試配置檢查 ===")
    try:
        response = requests.get(f"{BASE_URL}/config/check")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 配置檢查通過:")
            print(f"  - Azure OpenAI: {'✓' if result['config_status']['openai_configured'] else '✗'}")
            print(f"  - Azure AI Search: {'✓' if result['config_status']['search_configured'] else '✗'}")
            print(f"  - Azure Storage: {'✓' if result['config_status']['storage_configured'] else '✗'}")
            
            if result['config_status']['missing_configs']:
                print(f"  缺少的配置:")
                for config in result['config_status']['missing_configs']:
                    print(f"    - {config}")
            
            return result['config_status']['openai_configured']
        else:
            print(f"✗ 配置檢查失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 配置檢查錯誤: {e}")
        return False

def test_azure_openai():
    """測試Azure OpenAI連接"""
    print("\n=== 測試Azure OpenAI ===")
    try:
        response = requests.get(f"{BASE_URL}/azure/test")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Azure OpenAI連接成功:")
            print(f"  - API Base: {result.get('api_base', 'N/A')}")
            print(f"  - Chat模型狀態: {result.get('chat_completion', {}).get('status', 'N/A')}")
            print(f"  - Embedding模型狀態: {result.get('embedding', {}).get('status', 'N/A')}")
            return True
        else:
            print(f"✗ Azure OpenAI連接失敗: {response.status_code}")
            if response.text:
                print(f"  錯誤訊息: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Azure OpenAI測試錯誤: {e}")
        return False

def test_azure_search():
    """測試Azure AI Search連接"""
    print("\n=== 測試Azure AI Search ===")
    try:
        response = requests.get(f"{BASE_URL}/azure/search/test")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Azure AI Search連接成功:")
            if 'stats' in result:
                stats = result['stats']
                print(f"  - 索引名稱: {stats.get('index_name', 'N/A')}")
                print(f"  - 文件總數: {stats.get('total_documents', 'N/A')}")
                print(f"  - 欄位數量: {stats.get('fields_count', 'N/A')}")
            return True
        else:
            print(f"✗ Azure AI Search連接失敗: {response.status_code}")
            if response.text:
                print(f"  錯誤訊息: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Azure AI Search測試錯誤: {e}")
        return False

def test_document_indexing():
    """測試文件索引功能"""
    print("\n=== 測試文件索引 ===")
    try:
        test_document = {
            "title": "測試安全報告",
            "content": "這是一份測試用的安全報告，包含SQL注入、XSS攻擊等高風險漏洞。報告顯示系統存在critical級別的安全問題。",
            "category": "security_test",
            "tags": ["test", "security", "vulnerability"],
            "metadata": {
                "test_document": True,
                "created_by": "test_script"
            }
        }
        
        response = requests.post(f"{BASE_URL}/azure/search/index", json=test_document)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 文件索引成功:")
            print(f"  - 文件ID: {result.get('document_id', 'N/A')}")
            return result.get('document_id')
        else:
            print(f"✗ 文件索引失敗: {response.status_code}")
            if response.text:
                print(f"  錯誤訊息: {response.text}")
            return None
    except Exception as e:
        print(f"✗ 文件索引測試錯誤: {e}")
        return None

def test_document_search():
    """測試文件搜尋功能"""
    print("\n=== 測試文件搜尋 ===")
    try:
        search_query = {
            "query": "SQL注入漏洞",
            "top_k": 3,
            "semantic_search": True,
            "include_vectors": True
        }
        
        response = requests.post(f"{BASE_URL}/azure/search/query", json=search_query)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 文件搜尋成功:")
            print(f"  - 查詢: {result.get('query', 'N/A')}")
            print(f"  - 結果數量: {result.get('total_results', 0)}")
            
            for i, doc in enumerate(result.get('results', [])[:2], 1):
                print(f"  - 結果 {i}:")
                print(f"    標題: {doc.get('title', 'N/A')}")
                print(f"    分數: {doc.get('score', 'N/A'):.3f}")
                print(f"    內容預覽: {doc.get('content', 'N/A')[:100]}...")
            
            return True
        else:
            print(f"✗ 文件搜尋失敗: {response.status_code}")
            if response.text:
                print(f"  錯誤訊息: {response.text}")
            return False
    except Exception as e:
        print(f"✗ 文件搜尋測試錯誤: {e}")
        return False

def test_enhanced_chat():
    """測試增強聊天功能"""
    print("\n=== 測試增強聊天 ===")
    try:
        chat_query = {
            "query": "系統有哪些安全漏洞？請詳細說明。",
            "max_tokens": 500,
            "temperature": 0.7,
            "search_results": 2
        }
        
        response = requests.post(f"{BASE_URL}/azure/search/enhanced-chat", json=chat_query)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 增強聊天成功:")
            print(f"  - 查詢: {result.get('query', 'N/A')}")
            print(f"  - 來源數量: {result.get('search_results_count', 0)}")
            print(f"  - 回應: {result.get('response', 'N/A')[:200]}...")
            
            if 'usage' in result:
                usage = result['usage']
                print(f"  - Token使用: {usage.get('total_tokens', 'N/A')}")
            
            return True
        else:
            print(f"✗ 增強聊天失敗: {response.status_code}")
            if response.text:
                print(f"  錯誤訊息: {response.text}")
            return False
    except Exception as e:
        print(f"✗ 增強聊天測試錯誤: {e}")
        return False

def main():
    """主測試函數"""
    print("Azure服務功能測試開始")
    print("=" * 50)
    
    # 測試序列
    test_results = []
    
    # 1. 基礎健康檢查
    test_results.append(("健康檢查", test_health_check()))
    
    # 2. 配置檢查
    config_ok = test_config_check()
    test_results.append(("配置檢查", config_ok))
    
    # 3. Azure OpenAI測試
    if config_ok:
        test_results.append(("Azure OpenAI", test_azure_openai()))
        
        # 4. Azure AI Search測試
        search_ok = test_azure_search()
        test_results.append(("Azure AI Search", search_ok))
        
        # 5. 文件索引測試
        if search_ok:
            doc_id = test_document_indexing()
            test_results.append(("文件索引", doc_id is not None))
            
            # 6. 文件搜尋測試
            test_results.append(("文件搜尋", test_document_search()))
            
            # 7. 增強聊天測試
            test_results.append(("增強聊天", test_enhanced_chat()))
    
    # 測試結果摘要
    print("\n" + "=" * 50)
    print("測試結果摘要:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✓ 通過" if result else "✗ 失敗"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n總體結果: {passed}/{total} 項測試通過")
    
    if passed == total:
        print("🎉 所有測試都通過！Azure服務整合成功！")
        return True
    else:
        print("⚠️  部分測試失敗，請檢查配置和服務狀態。")
        return False

if __name__ == "__main__":
    # 檢查是否有必要的環境變數
    required_env_vars = ['OPENAI_API_KEY', 'OPENAI_API_BASE']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"錯誤: 缺少必要的環境變數: {', '.join(missing_vars)}")
        print("請檢查 .env 檔案配置")
        sys.exit(1)
    
    success = main()
    sys.exit(0 if success else 1)