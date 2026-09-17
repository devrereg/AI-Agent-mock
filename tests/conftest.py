import pytest
from app.main import app
from app.utils.jwt_utils import decode_access_token, oauth2_scheme

def mock_decode_access_token():
    return {"id": "test-user-id", "email": "test@example.com"}

def mock_oauth2_scheme():
    return "mock-token-123"

@pytest.fixture(autouse=True)
def override_auth_dependencies():
    app.dependency_overrides[decode_access_token] = mock_decode_access_token
    app.dependency_overrides[oauth2_scheme] = mock_oauth2_scheme
    yield
    app.dependency_overrides = {}
