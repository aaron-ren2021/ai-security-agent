import pytest
from src.main import app

@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        yield client


def test_providers_endpoint(client):
    """Test the /auth/providers endpoint returns configured providers list"""
    response = client.get('/auth/providers')
    assert response.status_code == 200
    data = response.get_json()
    assert 'providers' in data, 'Missing providers key in response'
    # GitHub provider should exist
    assert 'github' in data['providers'], 'GitHub provider not listed'


def test_status_unauthenticated(client):
    """Test the /auth/status endpoint for unauthenticated user"""
    response = client.get('/auth/status')
    assert response.status_code == 200
    data = response.get_json()
    assert data.get('authenticated') is False, 'User should be unauthenticated by default'
    assert 'user' not in data or data['user'] is None


def test_login_github_returns_url_and_state(client):
    """Test the /auth/login/github endpoint returns authorization_url and state"""
    response = client.get('/auth/login/github')
    assert response.status_code == 200
    data = response.get_json()
    assert 'authorization_url' in data, 'authorization_url missing'
    assert 'state' in data, 'state token missing'
    assert data.get('provider') == 'github'


def test_debug_config_endpoint(client):
    """Test the /auth/debug/config endpoint returns config info"""
    response = client.get('/auth/debug/config')
    assert response.status_code == 200
    data = response.get_json()
    assert 'providers' in data
    assert 'github' in data['providers']
    provider_cfg = data['providers']['github']
    assert provider_cfg.get('configured') in [True, False]


def test_login_with_invalid_provider(client):
    """Test login with an invalid provider returns 404 or error"""
    response = client.get('/auth/login/unknownprovider')
    assert response.status_code in (400, 404)


def test_status_authenticated(client, monkeypatch):
    """Test /auth/status for authenticated user (mock session)"""
    class DummyUser:
        def __init__(self):
            self.id = "testuser"
            self.name = "Test User"
            self.email = "test@example.com"
    # 假設你的 app 使用 session['user'] 儲存登入資訊
    with client.session_transaction() as sess:
        sess['user'] = {
            'id': 'testuser',
            'name': 'Test User',
            'email': 'test@example.com'
        }
    response = client.get('/auth/status')
    assert response.status_code == 200
    data = response.get_json()
    assert data.get('authenticated') is True
    assert data.get('user', {}).get('id') == 'testuser'


def test_logout_endpoint(client):
    """Test the /auth/logout endpoint (如果有的話)"""
    response = client.get('/auth/logout')
    assert response.status_code in (200, 302)  # 可能會 redirect
