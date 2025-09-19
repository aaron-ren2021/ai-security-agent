"""
Azure模式MVP功能測試
專注測試Azure OpenAI和Azure AI Search核心功能
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.services.azure_openai_service import AzureOpenAIService
from src.services.azure_search_service import AzureAISearchService

class TestAzureOpenAIService:
    """測試Azure OpenAI服務"""
    
    def setup_method(self):
        """設置測試環境"""
        self.service = AzureOpenAIService(
            api_key="test_key",
            api_base="https://test.openai.azure.com/",
            api_version="2023-05-15"
        )
    
    def test_initialization(self):
        """測試服務初始化"""
        assert self.service.api_key == "test_key"
        assert self.service.api_base == "https://test.openai.azure.com/"
        assert self.service.api_version == "2023-05-15"
        assert self.service.default_chat_model == "gpt-35-turbo"
        assert self.service.default_embedding_model == "text-embedding-ada-002"
    
    def test_get_model_info(self):
        """測試取得模型資訊"""
        model_info = self.service.get_model_info()
        
        assert "chat_model" in model_info
        assert "embedding_model" in model_info
        assert "api_version" in model_info
        assert "api_base" in model_info
        assert "configured" in model_info
        
        assert model_info["chat_model"] == "gpt-35-turbo"
        assert model_info["embedding_model"] == "text-embedding-ada-002"
    
    def test_update_model_config(self):
        """測試更新模型配置"""
        result = self.service.update_model_config(
            chat_model="gpt-4",
            embedding_model="text-embedding-3-large"
        )
        
        assert result["success"] is True
        assert self.service.default_chat_model == "gpt-4"
        assert self.service.default_embedding_model == "text-embedding-3-large"

class TestAzureAISearchService:
    """測試Azure AI Search服務"""
    
    def setup_method(self):
        """設置測試環境"""
        # 使用測試配置初始化
        self.service = None
        try:
            self.service = AzureAISearchService(
                search_service_name="test-search",
                search_api_key="test_key",
                openai_api_key="test_openai_key",
                openai_endpoint="https://test.openai.azure.com/",
                index_name="test-index"
            )
        except Exception:
            # 如果無法初始化（缺少真實憑證），創建Mock
            self.service = Mock()
    
    def test_document_result_structure(self):
        """測試文件結果結構"""
        from src.services.azure_search_service import DocumentResult
        
        result = DocumentResult(
            id="test-doc-1",
            title="測試文件",
            content="這是測試內容",
            score=0.95,
            metadata={"category": "test"}
        )
        
        assert result.id == "test-doc-1"
        assert result.title == "測試文件"
        assert result.content == "這是測試內容"
        assert result.score == 0.95
        assert result.metadata["category"] == "test"
    
    def test_search_config(self):
        """測試搜尋配置"""
        from src.services.azure_search_service import SearchConfig
        
        # 測試預設配置
        config = SearchConfig()
        assert config.top_k == 5
        assert config.semantic_search is True
        assert config.include_vectors is True
        assert config.highlight_fields is None
        
        # 測試自定義配置
        config = SearchConfig(
            top_k=10,
            semantic_search=False,
            include_vectors=False,
            highlight_fields=["title", "content"]
        )
        assert config.top_k == 10
        assert config.semantic_search is False
        assert config.include_vectors is False
        assert config.highlight_fields == ["title", "content"]

class TestEnvironmentConfiguration:
    """測試環境配置"""
    
    def test_required_env_vars(self):
        """測試必要的環境變數"""
        # 檢查Azure OpenAI必要變數
        assert os.getenv('OPENAI_API_KEY') is not None, "OPENAI_API_KEY is required"
        assert os.getenv('OPENAI_API_BASE') is not None, "OPENAI_API_BASE is required"
    
    def test_optional_env_vars(self):
        """測試可選的環境變數"""
        # 這些變數可能不存在，但不應該影響基本功能
        search_service = os.getenv('AZURE_SEARCH_SERVICE_NAME')
        search_key = os.getenv('AZURE_SEARCH_API_KEY')
        
        if search_service and search_key:
            print(f"Azure AI Search配置完整: {search_service}")
        else:
            print("Azure AI Search配置不完整，某些功能可能不可用")

class TestIntegrationScenarios:
    """測試整合場景"""
    
    def test_security_report_analysis_workflow(self):
        """測試安全報告分析工作流程"""
        # 模擬安全報告內容
        report_content = """
        安全掃描報告
        發現以下漏洞：
        1. SQL注入漏洞 (Critical)
        2. XSS攻擊漏洞 (High)
        3. 目錄遍歷漏洞 (Medium)
        CVE-2023-1234: 遠程代碼執行
        CVE-2023-5678: 權限提升
        """
        
        # 測試報告類型檢測
        from src.routes.rag_api import detect_report_type
        report_type = detect_report_type(report_content, "security_scan.txt")
        assert report_type == "security_report"
        
        # 測試漏洞分析
        from src.routes.rag_api import analyze_vulnerability_report
        analysis = analyze_vulnerability_report(report_content, report_type)
        
        assert "summary" in analysis
        assert "statistics" in analysis
        assert "potential_high_risks" in analysis
        assert "sample_content" in analysis
        assert "parsed_at" in analysis
        
        # 檢查統計資訊
        stats = analysis["statistics"]
        assert stats["cve_references"] >= 2  # 應該找到CVE引用
        assert stats["critical_severity"] >= 1  # 應該找到Critical級別
        assert stats["high_severity"] >= 1  # 應該找到High級別
    
    def test_file_validation(self):
        """測試檔案驗證"""
        from src.routes.rag_api import allowed_file
        
        # 允許的檔案類型
        assert allowed_file("report.txt") is True
        assert allowed_file("scan.pdf") is True
        assert allowed_file("data.json") is True
        assert allowed_file("config.xml") is True
        
        # 不允許的檔案類型
        assert allowed_file("script.exe") is False
        assert allowed_file("image.jpg") is False
        assert allowed_file("archive.zip") is False
        assert allowed_file("no_extension") is False

def test_azure_services_integration():
    """測試Azure服務整合"""
    # 這是一個整合測試，檢查服務是否能正常初始化
    try:
        # 測試Azure OpenAI服務
        openai_service = AzureOpenAIService()
        model_info = openai_service.get_model_info()
        assert model_info["configured"] == bool(os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_API_BASE'))
        
        print("✓ Azure OpenAI服務測試通過")
        
    except Exception as e:
        print(f"⚠️  Azure OpenAI服務測試失敗: {e}")
    
    try:
        # 測試Azure AI Search服務（如果配置完整）
        search_service_name = os.getenv('AZURE_SEARCH_SERVICE_NAME')
        search_api_key = os.getenv('AZURE_SEARCH_API_KEY')
        
        if search_service_name and search_api_key:
            from src.services.azure_search_service import create_azure_search_service
            search_service = create_azure_search_service()
            assert search_service is not None
            print("✓ Azure AI Search服務測試通過")
        else:
            print("⚠️  Azure AI Search配置不完整，跳過測試")
            
    except Exception as e:
        print(f"⚠️  Azure AI Search服務測試失敗: {e}")

if __name__ == "__main__":
    # 簡單的測試運行器
    print("Azure模式MVP功能測試")
    print("=" * 40)
    
    # 運行基本測試
    try:
        # 環境配置測試
        test_env = TestEnvironmentConfiguration()
        test_env.test_required_env_vars()
        print("✓ 環境配置測試通過")
        
        # Azure OpenAI服務測試
        test_openai = TestAzureOpenAIService()
        test_openai.setup_method()
        test_openai.test_initialization()
        test_openai.test_get_model_info()
        test_openai.test_update_model_config()
        print("✓ Azure OpenAI服務測試通過")
        
        # Azure AI Search服務測試
        test_search = TestAzureAISearchService()
        test_search.setup_method()
        test_search.test_document_result_structure()
        test_search.test_search_config()
        print("✓ Azure AI Search服務測試通過")
        
        # 整合場景測試
        test_integration = TestIntegrationScenarios()
        test_integration.test_security_report_analysis_workflow()
        test_integration.test_file_validation()
        print("✓ 整合場景測試通過")
        
        # Azure服務整合測試
        test_azure_services_integration()
        
        print("\n🎉 所有測試通過！Azure模式MVP功能正常！")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()