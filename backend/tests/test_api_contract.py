from typing import Any

from httpx import ASGITransport, AsyncClient

from roomswipe_api.api.dependencies import get_shopify_catalog_service
from roomswipe_api.main import app
from roomswipe_api.schemas import ProductOffer
from roomswipe_api.services.shopify_mcp import ShopifyMcpError


def search_payload() -> dict[str, Any]:
    return {
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
    }


class StubCatalogService:
    async def search_offers(self, **request: Any) -> list[ProductOffer]:
        assert request["budget_minor"] == 30_000
        assert request["manifest"].product_slots[0].id == "lamp-1"
        return [
            ProductOffer(
                product_id="gid://shopify/p/lamp",
                variant_id="gid://shopify/ProductVariant/lamp",
                slot_id="lamp-1",
                title="Arched Brass Floor Lamp",
                merchant_name="Lamp Shop",
                merchant_domain="lamp-shop.myshopify.com",
                price_minor=17_999,
                currency="USD",
                image_url="https://cdn.example.com/lamp.jpg",
                checkout_url="https://lamp-shop.example/cart/lamp:1",
                available=True,
            )
        ]


class FailingCatalogService:
    async def search_offers(self, **request: Any) -> list[ProductOffer]:
        raise ShopifyMcpError("Shopify catalog is temporarily unavailable")


async def test_health() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "roomswipe-api"}


async def test_search_route_returns_catalog_offers() -> None:
    transport = ASGITransport(app=app)
    app.dependency_overrides[get_shopify_catalog_service] = StubCatalogService

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/commerce/search", json=search_payload())
    finally:
        app.dependency_overrides.pop(get_shopify_catalog_service, None)

    assert response.status_code == 200
    assert response.json()[0]["slotId"] == "lamp-1"
    assert response.json()[0]["priceMinor"] == 17_999


async def test_search_route_maps_shopify_failures_to_bad_gateway() -> None:
    transport = ASGITransport(app=app)
    app.dependency_overrides[get_shopify_catalog_service] = FailingCatalogService

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/commerce/search", json=search_payload())
    finally:
        app.dependency_overrides.pop(get_shopify_catalog_service, None)

    assert response.status_code == 502
    assert response.json()["detail"] == "Shopify catalog is temporarily unavailable"
