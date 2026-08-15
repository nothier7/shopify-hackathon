from typing import Any

import httpx

from roomswipe_api.schemas import ProductOffer
from roomswipe_api.services.shopify_carts import MerchantEndpointResolver, ShopifyCartService
from roomswipe_api.services.shopify_mcp import ShopifyMcpError


def offer(
    *,
    slot_id: str,
    merchant_domain: str = "lamp-shop.myshopify.com",
    variant_id: str = "gid://shopify/ProductVariant/lamp",
) -> ProductOffer:
    return ProductOffer(
        product_id=f"gid://shopify/p/{slot_id}",
        variant_id=variant_id,
        slot_id=slot_id,
        title=f"Product for {slot_id}",
        merchant_name="Lamp Shop" if "lamp" in merchant_domain else "Rug Shop",
        merchant_domain=merchant_domain,
        price_minor=10_000,
        currency="USD",
        image_url=None,
        checkout_url=f"https://{merchant_domain}/products/{slot_id}",
        available=True,
    )


class StubCatalogService:
    async def refresh_offer(self, *, offer: ProductOffer, country: str) -> ProductOffer:
        assert country == "US"
        return offer


class StubEndpointResolver:
    async def resolve(self, checkout_url: str) -> str:
        origin = checkout_url.split("/products/")[0]
        return f"{origin}/api/ucp/mcp"


class StubMcpClient:
    def __init__(self, *, failing_domain: str | None = None) -> None:
        self.failing_domain = failing_domain
        self.calls: list[dict[str, Any]] = []

    async def call_tool(self, **call: Any) -> dict[str, Any]:
        self.calls.append(call)
        endpoint = call["endpoint"]
        if self.failing_domain and self.failing_domain in endpoint:
            raise ShopifyMcpError("merchant cart is temporarily unavailable")

        lines = call["arguments"]["cart"]["line_items"]
        return {
            "id": f"gid://shopify/Cart/{len(self.calls)}",
            "currency": "USD",
            "line_items": lines,
            "totals": [{"type": "subtotal", "amount": 10_000 * len(lines)}],
            "continue_url": f"{endpoint}/continue",
        }


async def test_endpoint_resolver_uses_well_known_mcp_service() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://lamp-shop.com/.well-known/ucp"
        return httpx.Response(
            200,
            json={
                "ucp": {
                    "services": {
                        "dev.ucp.shopping": [
                            {
                                "transport": "mcp",
                                "endpoint": "https://lamp-shop.myshopify.com/api/ucp/mcp",
                            }
                        ]
                    }
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        resolver = MerchantEndpointResolver(http_client=http_client)
        endpoint = await resolver.resolve("https://lamp-shop.com/cart/variant:1")

    assert endpoint == "https://lamp-shop.myshopify.com/api/ucp/mcp"


async def test_endpoint_resolver_falls_back_to_checkout_origin() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        resolver = MerchantEndpointResolver(http_client=http_client)
        endpoint = await resolver.resolve("https://lamp-shop.com/cart/variant:1")

    assert endpoint == "https://lamp-shop.com/api/ucp/mcp"


async def test_cart_service_groups_by_merchant_and_keeps_partial_success() -> None:
    mcp = StubMcpClient(failing_domain="rug-shop")
    service = ShopifyCartService(
        catalog_service=StubCatalogService(),  # type: ignore[arg-type]
        mcp_client=mcp,  # type: ignore[arg-type]
        endpoint_resolver=StubEndpointResolver(),  # type: ignore[arg-type]
    )
    selected = [
        offer(slot_id="lamp-1"),
        offer(slot_id="lamp-2", variant_id="gid://shopify/ProductVariant/lamp-2"),
        offer(
            slot_id="rug-1",
            merchant_domain="rug-shop.myshopify.com",
            variant_id="gid://shopify/ProductVariant/rug",
        ),
    ]

    response = await service.create_merchant_carts(offers=selected, country="US")

    assert len(mcp.calls) == 2
    assert len(response.carts) == 1
    assert response.carts[0].slot_ids == ["lamp-1", "lamp-2"]
    assert response.carts[0].subtotal_minor == 20_000
    assert len(response.failures) == 1
    assert response.failures[0].merchant_domain == "rug-shop.myshopify.com"
    assert response.failures[0].slot_ids == ["rug-1"]
    assert response.failures[0].detail == "merchant cart is temporarily unavailable"

    successful_call = next(call for call in mcp.calls if "lamp-shop" in call["endpoint"])
    cart = successful_call["arguments"]["cart"]
    assert cart["context"] == {"address_country": "US"}
    assert cart["attribution"]["utm_source"] == "roomswipe"
    assert [line["quantity"] for line in cart["line_items"]] == [1, 1]
