import pytest
from pydantic import ValidationError

from roomswipe_api.schemas import (
    BoundingBox,
    CreateCartsResponse,
    PreferenceProfile,
    SearchProductsRequest,
    SwipeEvent,
)


def search_payload() -> dict[str, object]:
    return {
        "manifest": {
            "finalImageUrl": "https://images.example.com/final-room.jpg",
            "productSlots": [
                {
                    "id": "floor-lamp-1",
                    "category": "floor lamp",
                    "searchQuery": "arched antique brass floor lamp",
                    "colors": ["antique brass"],
                    "materials": ["metal", "marble"],
                    "styles": ["warm minimalist", "mid-century"],
                    "shape": "arched",
                    "changeType": "added",
                    "mustMatch": ["floor lamp", "under budget"],
                    "niceToHave": ["marble base"],
                    "budgetWeight": 0.2,
                    "confidence": 0.94,
                    "boundingBox": {
                        "x": 0.65,
                        "y": 0.1,
                        "width": 0.25,
                        "height": 0.8,
                    },
                }
            ],
        },
        "budgetMinor": 100_000,
        "currency": "usd",
        "country": "us",
        "candidatesPerSlot": 4,
    }


def test_final_design_manifest_accepts_frontend_camel_case() -> None:
    request = SearchProductsRequest.model_validate(search_payload())

    assert request.country == "US"
    assert request.currency == "USD"
    assert request.manifest.product_slots[0].search_query == "arched antique brass floor lamp"
    assert request.manifest.product_slots[0].bounding_box == BoundingBox(
        x=0.65,
        y=0.1,
        width=0.25,
        height=0.8,
    )


def test_bounding_box_must_stay_inside_the_image() -> None:
    payload = search_payload()
    slot = payload["manifest"]["productSlots"][0]  # type: ignore[index]
    slot["boundingBox"] = {"x": 0.9, "y": 0.1, "width": 0.2, "height": 0.5}

    with pytest.raises(ValidationError, match="bounding box must fit inside the image"):
        SearchProductsRequest.model_validate(payload)


def test_manifest_requires_at_least_one_product_slot() -> None:
    payload = search_payload()
    payload["manifest"]["productSlots"] = []  # type: ignore[index]

    with pytest.raises(ValidationError):
        SearchProductsRequest.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("country", "CA", "only US delivery is supported"),
        ("currency", "CAD", "only USD budgets are supported"),
    ],
)
def test_search_is_scoped_to_us_delivery_and_usd_budget(
    field: str,
    value: str,
    message: str,
) -> None:
    payload = search_payload()
    payload[field] = value

    with pytest.raises(ValidationError, match=message):
        SearchProductsRequest.model_validate(payload)


def test_shared_recommendation_and_cart_contracts_are_available() -> None:
    swipe = SwipeEvent(candidateId="design-1", liked=True, comment="more wood")
    profile = PreferenceProfile(
        attributes={"material:wood": 0.8},
        confidence=0.5,
        likedSignals=["material:wood"],
        dislikedSignals=[],
        modelVersion=2,
        positiveCount=1,
        negativeCount=1,
    )
    carts = CreateCartsResponse(carts=[], failures=[])

    assert swipe.comment == "more wood"
    assert profile.model_version == 2
    assert carts.failures == []
