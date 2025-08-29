import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import pytest
from src.routes.rag_api import some_route_function
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_rag_api_some_route():
    response = client.get("/some-route")
    assert response.status_code == 200
    assert response.json() == {"message": "預期結果"}
