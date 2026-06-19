"""
Basic API smoke tests.
"""


def test_ping_endpoint(test_client):
    """Test that API is running"""
    response = test_client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"pong": True}


def test_auth_health_endpoint(test_client):
    """Test auth health check"""
    response = test_client.get("/api/auth/health")
    assert response.status_code == 200
    assert "status" in response.json()
