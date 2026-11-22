import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_and_correlation_header(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Correlation-ID": "corr-123"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "catalog-service"}
    assert response.headers.get("X-Correlation-ID") == "corr-123"


@pytest.mark.asyncio
async def test_ready_probe(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}