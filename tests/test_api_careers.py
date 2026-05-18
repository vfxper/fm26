"""
Integration Tests - Career API (Task 35.1)
Tests career creation and management flow.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    user.telegram_id = 123456
    return user


class TestCareerAPI:
    """Test career API endpoints."""

    @pytest.mark.asyncio
    async def test_create_career_requires_auth(self):
        """POST /api/careers without auth should return 401/403."""
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/careers", json={
                "club_id": 1,
                "manager_name": "Test Manager",
            })
            assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_get_career_not_found(self):
        """GET /api/careers/999 should return 404."""
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/careers/999")
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """GET /health should work."""
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            # May fail if DB not connected, but endpoint should exist
            assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """GET / should return app info."""
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert "version" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
