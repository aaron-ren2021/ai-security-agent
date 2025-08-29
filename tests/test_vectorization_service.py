import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import pytest
from src.services.vectorization_service import VectorizationService

def test_vectorization_service_initialization():
    service = VectorizationService()
    assert service is not None

def test_vectorization_service_some_functionality():
    service = VectorizationService()
    # 模擬測試邏輯
    result = service.some_functionality()
    assert result == "預期結果"
