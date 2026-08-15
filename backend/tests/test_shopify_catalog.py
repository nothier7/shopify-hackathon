from collections import deque
from typing import Any

from roomswipe_api.schemas import FinalDesignManifest, ProductOffer
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
        "description": "An arched antique brass floor lamp with a marble base.",
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
        candidates_per_slot=1,
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
    assert catalog["pagination"] == {"limit": 5}
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
        candidates_per_slot=1,
    )

    assert len(mcp.calls) == 2
    assert "Colors:" in mcp.calls[0]["arguments"]["catalog"]["query"]
    assert "Colors:" not in mcp.calls[1]["arguments"]["catalog"]["query"]
    assert "like" not in mcp.calls[1]["arguments"]["catalog"]
    assert offers[0].relaxed_preferences == ["colors", "materials", "styles", "shape"]


async def test_search_falls_back_when_raw_products_are_not_usable() -> None:
    over_budget = catalog_product()
    over_budget["variants"] = [over_budget["variants"][0]]
    mcp = StubMcpClient(
        [{"products": [over_budget]}, {"products": [catalog_product()]}]
    )
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
        candidates_per_slot=1,
    )

    assert len(mcp.calls) == 2
    assert offers[0].variant_id == "gid://shopify/ProductVariant/lamp"
    assert offers[0].relaxed_preferences == ["colors", "materials", "styles", "shape"]


async def test_search_uses_broad_category_fallback_and_marks_it() -> None:
    mcp = StubMcpClient(
        [{"products": []}, {"products": []}, {"products": [catalog_product()]}]
    )
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
        candidates_per_slot=1,
    )

    assert len(mcp.calls) == 3
    assert mcp.calls[2]["arguments"]["catalog"]["query"] == (
        "floor lamp. Required: floor lamp"
    )
    assert offers[0].relaxed_preferences == [
        "colors",
        "materials",
        "styles",
        "shape",
        "descriptive wording",
    ]


async def test_search_deduplicates_products_with_the_same_description() -> None:
    first = catalog_product()
    duplicate = catalog_product()
    duplicate["id"] = "gid://shopify/p/duplicate-lamp"
    duplicate["title"] = "A Different Product Title"
    duplicate["description"] = "  AN ARCHED ANTIQUE BRASS FLOOR LAMP WITH A MARBLE BASE. "
    duplicate["variants"] = [
        {
            **duplicate["variants"][1],
            "id": "gid://shopify/ProductVariant/duplicate-lamp",
        }
    ]
    responses = [
        {"products": [first, duplicate]},
        {"products": [first, duplicate]},
        {"products": [first, duplicate]},
    ]
    service = ShopifyCatalogService(
        mcp_client=StubMcpClient(responses),  # type: ignore[arg-type]
        image_service=StubImageService(),  # type: ignore[arg-type]
        catalog_endpoint="https://catalog.shopify.com/api/ucp/mcp",
    )

    offers = await service.search_offers(
        manifest=manifest(with_box=False),
        budget_minor=30_000,
        currency="USD",
        country="US",
        candidates_per_slot=2,
    )

    assert len(offers) == 1
    assert offers[0].product_id == "gid://shopify/p/lamp"


async def test_search_prioritizes_usd_over_native_currency_offer() -> None:
    cad_product = catalog_product()
    cad_product["id"] = "gid://shopify/p/cad-lamp"
    cad_product["description"] = "A distinct Canadian lamp."
    cad_product["variants"] = [
        {
            **cad_product["variants"][1],
            "id": "gid://shopify/ProductVariant/cad-lamp",
            "price": {"amount": 24_000, "currency": "CAD"},
        }
    ]
    mcp = StubMcpClient([{"products": [cad_product, catalog_product()]}])
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
        candidates_per_slot=1,
    )

    assert offers[0].currency == "USD"
    assert offers[0].product_id == "gid://shopify/p/lamp"


def test_budget_is_allocated_proportionally() -> None:
    room = manifest(with_box=False)
    first = room.product_slots[0]
    second = first.model_copy(update={"id": "sofa-1", "budget_weight": 3})

    assert ShopifyCatalogService._allocate_budget([first, second], 100_000) == {
        "lamp-1": 25_000,
        "sofa-1": 75_000,
    }


async def test_refresh_offer_uses_current_selected_variant_details() -> None:
    mcp = StubMcpClient([{"product": catalog_product()}])
    service = ShopifyCatalogService(
        mcp_client=mcp,  # type: ignore[arg-type]
        image_service=StubImageService(),  # type: ignore[arg-type]
        catalog_endpoint="https://catalog.shopify.com/api/ucp/mcp",
    )
    selected = ProductOffer(
        product_id="gid://shopify/p/lamp",
        variant_id="gid://shopify/ProductVariant/lamp",
        slot_id="lamp-1",
        title="Old title",
        merchant_name="Old merchant",
        merchant_domain="old.myshopify.com",
        price_minor=15_000,
        currency="USD",
        checkout_url="https://old.example.com/cart/lamp:1",
        available=True,
    )

    refreshed = await service.refresh_offer(offer=selected, country="US")

    assert mcp.calls[0]["name"] == "get_product"
    assert mcp.calls[0]["arguments"]["catalog"]["id"] == selected.product_id
    assert refreshed.title == "Venice Antique Brass Arc Floor Lamp"
    assert refreshed.price_minor == 17_999
    assert refreshed.merchant_domain == "lamp-shop.myshopify.com"
    assert refreshed.checkout_url == "https://lamp-shop.example/cart/lamp:1"
