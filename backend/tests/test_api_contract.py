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
            json={
                "manifest": {
                    "finalImageUrl": "https://images.example.com/final-room.jpg",
                    "productSlots": [
                        {
                            "id": "lamp-1",
                            "category": "floor lamp",
                            "searchQuery": "arched brass floor lamp",
                            "changeType": "added",
                            "budgetWeight": 1,
                            "confidence": 0.9,
                        }
                    ],
                },
                "budgetMinor": 30_000,
                "country": "US",
            },
        )

    assert response.status_code == 501
    assert response.json()["detail"] == "Shopify Global Catalog service is not connected yet."
