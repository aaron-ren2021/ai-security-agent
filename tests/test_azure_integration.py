#!/usr/bin/env python3
"""
Azure Agents SDK 集成測試腳本
"""

import os
import sys
sys.path.append('/mnt/c/Users/AaronLiu劉自仁/Documents/xcloud_project/ai-security-agent-v2/src')

from services.ai_agent_service import ThreatAnalysisAgent
from services.vectorization_service import VectorizationService

def test_azure_integration():
    """測試Azure Agents SDK集成"""
    print("🔧 開始測試Azure Agents SDK集成...")
    
    # 初始化服務
    vectorization_service = VectorizationService(
        chroma_persist_directory="./chroma_db",
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        openai_api_base=os.getenv('OPENAI_API_BASE')
    )
    
    # 初始化威脅分析Agent
    threat_agent = ThreatAnalysisAgent(vectorization_service)
    
    # 測試查詢
    test_query = "分析最近的勒索軟體攻擊趨勢"
    
    print(f"📝 測試查詢: {test_query}")
    
    # 測試標準模式
    print("\n🔍 測試標準模式...")
    try:
        standard_result = threat_agent.analyze(test_query)
        print("✅ 標準模式測試成功")
        print(f"結果預覽: {standard_result.get('analysis', 'N/A')[:100]}...")
    except Exception as e:
        print(f"❌ 標準模式測試失敗: {e}")
    
    # 測試Azure模式
    print("\n☁️ 測試Azure模式...")
    
    # 檢查環境變數
    if not os.getenv('PROJECT_ENDPOINT') or not os.getenv('MODEL_DEPLOYMENT_NAME'):
        print("⚠️ Azure環境變數未設定，跳過Azure模式測試")
        print("請設定以下環境變數:")
        print("- PROJECT_ENDPOINT: Azure AI項目端點")
        print("- MODEL_DEPLOYMENT_NAME: 模型部署名稱")
        return
    
    try:
        azure_result = threat_agent.analyze_with_azure(test_query)
        if 'error' in azure_result:
            print(f"❌ Azure模式測試失敗: {azure_result['error']}")
        else:
            print("✅ Azure模式測試成功")
            print(f"Azure Agent ID: {azure_result.get('azure_agent_id', 'N/A')}")
            print(f"執行狀態: {azure_result.get('run_status', 'N/A')}")
            print(f"結果預覽: {azure_result.get('analysis', 'N/A')[:100]}...")
    except Exception as e:
        print(f"❌ Azure模式測試失敗: {e}")

def check_environment():
    """檢查環境配置"""
    print("🔍 檢查環境配置...")
    
    required_vars = [
        'OPENAI_API_KEY',
        'PROJECT_ENDPOINT', 
        'MODEL_DEPLOYMENT_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"✅ {var}: 已設定")
    
    if missing_vars:
        print(f"\n⚠️ 缺少環境變數: {', '.join(missing_vars)}")
        print("請在 .env 文件中設定這些變數")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("Azure Agents SDK 集成測試")
    print("=" * 50)
    
    # 檢查環境
    if not check_environment():
        print("\n請先設定環境變數後重新執行測試")
        sys.exit(1)
    
    # 執行測試
    test_azure_integration()
    
    print("\n" + "=" * 50)
    print("測試完成！")
    print("=" * 50)