import json
from pathlib import Path
from typing import Any

from httpx import ASGITransport, AsyncClient

from roomswipe_api.main import app
from roomswipe_api.schemas import (
    FinalDesignManifest,
    FinalRecommendationCandidate,
    ProductChangeType,
    ProductSlot,
    RecommendedDesign,
)
from roomswipe_api.services.orchestrator import RoomSwipeOrchestrator, RoomSwipeServices
from roomswipe_api.services.recommendation import LocalRecommendationService

REPOSITORY_ROOT = Path(__file__).parents[2]


def example_input() -> list[dict[str, Any]]:
    return json.loads((REPOSITORY_ROOT / "model_input.example.json").read_text(encoding="utf-8"))


def example_output() -> dict[str, Any]:
    return json.loads((REPOSITORY_ROOT / "model_output.example.json").read_text(encoding="utf-8"))


async def test_final_recommendation_route_runs_real_ml_model() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recommendations/final-design",
            json=example_input(),
        )

    assert response.status_code == 200
    assert response.json() == example_output()
    assert set(response.json()) == {"recommendedDesign"}


async def test_final_recommendation_route_requires_ten_candidates() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recommendations/final-design",
            json=example_input()[:-1],
        )

    assert response.status_code == 422


async def test_preference_and_product_selection_routes_use_ml_service() -> None:
    preference_payload = {
        "candidates": [
            {
                "id": "warm-room",
                "name": "Warm room",
                "imageUrl": "https://images.example.com/warm.jpg",
                "attributes": {"style:warm": 1, "material:wood": 1},
                "warmth": 1,
                "lighting": "warm lamps",
                "items": ["wood chair"],
                "questionnaire": {
                    "roomType": "living room",
                    "budgetMinor": 30000,
                    "currency": "USD",
                    "effort": "buy_only",
                    "designDensity": "minimalist",
                    "userAge": 28,
                    "goals": ["comfortable seating"],
                    "optionalStyles": [],
                },
            }
        ],
        "swipes": [
            {
                "candidateId": "warm-room",
                "liked": True,
                "comment": "More plants and wood",
            }
        ],
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        profile_response = await client.post(
            "/api/v1/recommendations/preferences",
            json=preference_payload,
        )
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["modelVersion"] == 1

        selection_response = await client.post(
            "/api/v1/recommendations/select-products",
            json={
                "profile": profile,
                "offers": [
                    {
                        "productId": "chair",
                        "variantId": "chair-variant",
                        "slotId": "seating",
                        "title": "Warm wood chair",
                        "merchantName": "Chair Store",
                        "merchantDomain": "chair.example",
                        "priceMinor": 20000,
                        "currency": "USD",
                        "checkoutUrl": "https://chair.example/cart",
                        "available": True,
                        "matchScore": 0.9,
                    },
                    {
                        "productId": "lamp",
                        "variantId": "lamp-variant",
                        "slotId": "lighting",
                        "title": "Warm floor lamp",
                        "merchantName": "Lamp Store",
                        "merchantDomain": "lamp.example",
                        "priceMinor": 10000,
                        "currency": "USD",
                        "checkoutUrl": "https://lamp.example/cart",
                        "available": True,
                        "matchScore": 0.8,
                    },
                ],
                "budgetMinor": 30000,
            },
        )

    assert selection_response.status_code == 200
    assert {offer["productId"] for offer in selection_response.json()} == {
        "chair",
        "lamp",
    }


def test_recommendation_output_fits_room_generation_contract() -> None:
    recommendation = RecommendedDesign.model_validate(example_output()["recommendedDesign"])

    assert recommendation.name == "Japandi"
    assert sum(item.max_price_minor for item in recommendation.items) <= 50_000


class StubImageService:
    async def generate_final_design(self, **request: Any) -> FinalDesignManifest:
        assert request["image"] == b"original-room"
        assert request["content_type"] == "image/jpeg"
        assert request["recommendation"].name == "Japandi"
        first_item = request["recommendation"].items[0]
        return FinalDesignManifest(
            final_image_url="https://images.example.com/final-room.jpg",
            product_slots=[
                ProductSlot(
                    id="recommended-item-1",
                    category=first_item.name,
                    search_query=first_item.description,
                    styles=[request["recommendation"].name],
                    change_type=ProductChangeType.ADDED,
                    must_match=[first_item.name],
                    budget_weight=first_item.max_price_minor,
                    confidence=request["recommendation"].match_percent / 100,
                )
            ],
        )


async def test_orchestrator_passes_ml_recommendation_to_room_generation() -> None:
    candidates = [
        FinalRecommendationCandidate.model_validate(candidate) for candidate in example_input()
    ]
    orchestrator = RoomSwipeOrchestrator(
        RoomSwipeServices(
            images=StubImageService(),  # type: ignore[arg-type]
            recommendations=LocalRecommendationService(),
            commerce=object(),  # type: ignore[arg-type]
        )
    )

    manifest = await orchestrator.generate_recommended_room(
        image=b"original-room",
        content_type="image/jpeg",
        candidates=candidates,
    )

    assert manifest.product_slots[0].search_query.startswith("Low-profile wood furniture")
