import json
from pathlib import Path
from typing import Any

from httpx import ASGITransport, AsyncClient

from roomswipe_api.main import app

REPOSITORY_ROOT = Path(__file__).parents[2]


def recommendation_request() -> dict[str, Any]:
    candidates = json.loads(
        (REPOSITORY_ROOT / "model_input.example.json").read_text(encoding="utf-8")
    )
    return {
        "candidates": [
            {
                key: value
                for key, value in candidate.items()
                if key not in {"like", "comment"}
            }
            for candidate in candidates
        ],
        "swipes": [
            {
                "candidateId": candidate["id"],
                "liked": candidate["like"] == "Yes",
                **(
                    {"comment": candidate["comment"]}
                    if "comment" in candidate
                    else {}
                ),
            }
            for candidate in candidates
        ],
    }


async def test_finalize_recommendation_returns_documented_model_output() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recommendations/finalize",
            json=recommendation_request(),
        )

    expected = json.loads(
        (REPOSITORY_ROOT / "model_output.example.json").read_text(encoding="utf-8")
    )
    assert response.status_code == 200
    assert response.json() == expected


async def test_finalize_recommendation_requires_one_swipe_per_candidate() -> None:
    payload = recommendation_request()
    payload["swipes"][1]["candidateId"] = payload["swipes"][0]["candidateId"]
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recommendations/finalize",
            json=payload,
        )

    assert response.status_code == 422
    assert "each candidate must have exactly one swipe" in response.text


async def test_finalize_recommendation_maps_ml_contract_errors_to_validation() -> None:
    payload = recommendation_request()
    payload["candidates"][1]["questionnaire"]["budgetMinor"] = 75_000
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recommendations/finalize",
            json=payload,
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "all 10 candidates must contain the same questionnaire"
    )


async def test_preferences_learns_from_frontend_swipes() -> None:
    payload = recommendation_request()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recommendations/preferences",
            json={
                "candidates": payload["candidates"],
                "swipes": payload["swipes"],
            },
        )

    assert response.status_code == 200
    profile = response.json()
    assert profile["positiveCount"] + profile["negativeCount"] == 10
    assert profile["confidence"] > 0
    assert profile["modelVersion"] == 10


async def test_select_products_ranks_one_offer_per_slot_under_budget() -> None:
    offers = [
        _offer("sofa-best", "sofa-slot", 12_000, 0.9),
        _offer("sofa-backup", "sofa-slot", 10_000, 0.2),
        _offer("lamp-best", "lamp-slot", 15_000, 0.8),
    ]
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recommendations/select-products",
            json={
                "profile": {
                    "attributes": {},
                    "confidence": 0.8,
                    "likedSignals": [],
                    "dislikedSignals": [],
                },
                "offers": offers,
                "budgetMinor": 30_000,
            },
        )

    assert response.status_code == 200
    selected = response.json()
    assert [offer["productId"] for offer in selected] == ["sofa-best", "lamp-best"]
    assert sum(offer["priceMinor"] for offer in selected) <= 30_000


def _offer(
    product_id: str,
    slot_id: str,
    price_minor: int,
    match_score: float,
) -> dict[str, Any]:
    return {
        "productId": product_id,
        "variantId": f"{product_id}-variant",
        "slotId": slot_id,
        "title": product_id.replace("-", " ").title(),
        "merchantName": "Demo Merchant",
        "merchantDomain": "demo.example.com",
        "priceMinor": price_minor,
        "currency": "USD",
        "imageUrl": "https://images.example.com/product.jpg",
        "checkoutUrl": "https://demo.example.com/products/item",
        "available": True,
        "matchScore": match_score,
    }
