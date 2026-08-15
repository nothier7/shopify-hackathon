from collections import deque
from typing import Any

from roomswipe_api.schemas import FinalDesignManifest
from roomswipe_api.services.reference_images import EncodedImage
from roomswipe_api.services.shopify_catalog import ShopifyCatalogService


class StubMcpClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = deque(responses)
        self.calls: list[dict[str, Any]] = []

    async def call_tool(self, **call: Any) -> dict[str, Any]:
        self.calls.append(call)
        return self.responses.popleft()


class StubImageService:
    def __init__(self) -> None:
        self.downloaded_urls: list[str] = []

    async def download(self, image_url: str) -> bytes:
        self.downloaded_urls.append(image_url)
        return b"final-image"

    def crop(self, image_bytes: bytes, bounding_box: object) -> EncodedImage:
        assert image_bytes == b"final-image"
        return EncodedImage(content_type="image/jpeg", data="encoded-crop")


def manifest(*, with_box: bool = True) -> FinalDesignManifest:
    slot: dict[str, Any] = {
        "id": "lamp-1",
        "category": "floor lamp",
        "searchQuery": "arched floor lamp",
        "colors": ["antique brass"],
        "materials": ["metal", "marble"],
        "styles": ["mid-century"],
        "shape": "arched",
        "changeType": "added",
        "mustMatch": ["floor lamp"],
        "niceToHave": ["foot switch"],
        "budgetWeight": 1,
        "confidence": 0.95,
    }
    if with_box:
        slot["boundingBox"] = {"x": 0.6, "y": 0.1, "width": 0.3, "height": 0.8}
    return FinalDesignManifest.model_validate(
        {
            "finalImageUrl": "https://images.example.com/final-room.jpg",
            "productSlots": [slot],
        }
    )


def catalog_product() -> dict[str, Any]:
    return {
        "id": "gid://shopify/p/lamp",
        "title": "Venice Antique Brass Arc Floor Lamp",
        "media": [{"type": "image", "url": "https://cdn.example.com/lamp.jpg"}],
        "variants": [
            {
                "id": "gid://shopify/ProductVariant/expensive",
                "price": {"amount": 35_000, "currency": "USD"},
                "availability": {"available": True},
                "seller": {"name": "Lamp Shop", "domain": "lamp-shop.myshopify.com"},
                "checkout_url": "https://lamp-shop.example/cart/expensive:1",
            },
            {
                "id": "gid://shopify/ProductVariant/lamp",
                "price": {"amount": 17_999, "currency": "USD"},
                "availability": {"available": True},
                "seller": {"name": "Lamp Shop", "domain": "lamp-shop.myshopify.com"},
                "checkout_url": "https://lamp-shop.example/cart/lamp:1",
            },
        ],
    }


async def test_search_uses_multimodal_catalog_filters_and_normalizes_offer() -> None:
    mcp = StubMcpClient([{"products": [catalog_product()]}])
    images = StubImageService()
    service = ShopifyCatalogService(
        mcp_client=mcp,  # type: ignore[arg-type]
        image_service=images,  # type: ignore[arg-type]
        catalog_endpoint="https://catalog.shopify.com/api/ucp/mcp",
    )

    offers = await service.search_offers(
        manifest=manifest(),
        budget_minor=30_000,
        currency="USD",
        country="US",
        region="NY",
        postal_code="10001",
        candidates_per_slot=3,
    )

    catalog = mcp.calls[0]["arguments"]["catalog"]
    assert images.downloaded_urls == ["https://images.example.com/final-room.jpg"]
    assert catalog["like"] == [
        {"image": {"content_type": "image/jpeg", "data": "encoded-crop"}}
    ]
    assert catalog["filters"] == {
        "available": True,
        "ships_to": {"country": "US", "region": "NY", "postal_code": "10001"},
        "price": {"max": 30_000},
    }
    assert catalog["view"] == "offer"
    assert offers[0].variant_id == "gid://shopify/ProductVariant/lamp"
    assert offers[0].merchant_domain == "lamp-shop.myshopify.com"
    assert offers[0].price_minor == 17_999
    assert offers[0].image_url == "https://cdn.example.com/lamp.jpg"


async def test_search_relaxes_soft_preferences_after_empty_result() -> None:
    mcp = StubMcpClient([{"products": []}, {"products": [catalog_product()]}])
    service = ShopifyCatalogService(
        mcp_client=mcp,  # type: ignore[arg-type]
        image_service=StubImageService(),  # type: ignore[arg-type]
        catalog_endpoint="https://catalog.shopify.com/api/ucp/mcp",
    )

    offers = await service.search_offers(
        manifest=manifest(with_box=False),
        budget_minor=30_000,
        currency="USD",
        country="US",
    )

    assert len(mcp.calls) == 2
    assert "Colors:" in mcp.calls[0]["arguments"]["catalog"]["query"]
    assert "Colors:" not in mcp.calls[1]["arguments"]["catalog"]["query"]
    assert "like" not in mcp.calls[1]["arguments"]["catalog"]
    assert offers[0].relaxed_preferences == ["colors", "materials", "styles", "shape"]


def test_budget_is_allocated_proportionally() -> None:
    room = manifest(with_box=False)
    first = room.product_slots[0]
    second = first.model_copy(update={"id": "sofa-1", "budget_weight": 3})

    assert ShopifyCatalogService._allocate_budget([first, second], 100_000) == {
        "lamp-1": 25_000,
        "sofa-1": 75_000,
    }
