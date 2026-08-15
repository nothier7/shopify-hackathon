from httpx import ASGITransport, AsyncClient

from roomswipe_api.main import app


async def test_health() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "roomswipe-api"}


async def test_unconnected_service_is_explicit() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/commerce/search",
            json={"slots": [], "country": "US"},
        )

    assert response.status_code == 501
    assert response.json()["detail"] == "Shopify Global Catalog service is not connected yet."
