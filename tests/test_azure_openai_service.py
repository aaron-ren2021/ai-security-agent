import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import pytest
from src.services.azure_openai_service import AzureOpenAIService

def test_azure_openai_service_initialization():
    service = AzureOpenAIService()
    assert service is not None

def test_azure_openai_service_some_functionality():
    service = AzureOpenAIService()
    # 模擬測試邏輯
    result = service.some_functionality()
    assert result == "預期結果"
