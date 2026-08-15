import json
import random

import httpx

from roomswipe_api.config import Settings
from roomswipe_api.schemas import Questionnaire, RecommendedDesign, RoomAnalysis
from roomswipe_api.services.image_generation import (
    STYLES,
    OpenAIImageGenerationService,
    choose_styles,
)


def room() -> RoomAnalysis:
    return RoomAnalysis(
        room_type="living room",
        palette=["white", "beige"],
        existing_furniture=["gray sofa"],
        empty_zones=["corner by window"],
        lighting="one window",
        architectural_constraints=[],
        confidence=0.9,
    )


def test_choose_styles_returns_unique_styles() -> None:
    selected = choose_styles(10, rng=random.Random(7))

    assert len(selected) == len(STYLES)
    assert len({style.name for style in selected}) == len(STYLES)


async def test_generate_designs_maps_image_and_frontend_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/images/edits"
        request_data = json.loads(request.content)
        assert request_data["images"][0]["image_url"].startswith("data:image/jpeg;base64,")
        assert "minimalist" in request_data["prompt"]
        return httpx.Response(200, json={"data": [{"b64_json": "image-bytes"}]})

    service = OpenAIImageGenerationService(
        Settings(openai_api_key="test-key"), transport=httpx.MockTransport(handler)
    )
    questionnaire = Questionnaire(
        room_type="living room",
        budget_minor=50000,
        effort="buy_only",
        design_density="minimalist",
        user_age=28,
        goals=["more seating"],
    )

    designs = await service.generate_designs(
        image=b"empty-room", content_type="image/jpeg", questionnaire=questionnaire, count=1
    )

    assert len(designs) == 1
    assert designs[0].image_url == "data:image/png;base64,image-bytes"
    assert designs[0].lighting
    assert designs[0].items
    assert 0 <= designs[0].warmth <= 1
    assert designs[0].questionnaire == questionnaire


async def test_generate_final_design_returns_commerce_manifest() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/images/edits"
        request_data = json.loads(request.content)
        assert request_data["images"][0]["image_url"].startswith("data:image/jpeg;base64,")
        assert "low-profile oak furniture" in request_data["prompt"].lower()
        return httpx.Response(200, json={"data": [{"b64_json": "final-image"}]})

    service = OpenAIImageGenerationService(
        Settings(openai_api_key="test-key"), transport=httpx.MockTransport(handler)
    )
    recommendation = RecommendedDesign.model_validate(
        {
            "name": "Japandi",
            "description": "A warm minimalist living room.",
            "matchPercent": 91,
            "items": [
                {
                    "name": "low-profile wood furniture",
                    "description": "Low-profile oak furniture in Japandi style.",
                    "maxPriceMinor": 30000,
                    "currency": "USD",
                },
                {
                    "name": "paper lantern",
                    "description": "A warm paper lantern with soft light.",
                    "maxPriceMinor": 20000,
                    "currency": "USD",
                },
            ],
            "budget": {"maxTotalMinor": 50000, "currency": "USD"},
        }
    )

    manifest = await service.generate_final_design(
        image=b"original-room",
        content_type="image/jpeg",
        recommendation=recommendation,
    )

    assert manifest.final_image_url == "data:image/png;base64,final-image"
    assert [slot.id for slot in manifest.product_slots] == [
        "low-profile-wood-furniture-1",
        "paper-lantern-2",
    ]
    assert manifest.product_slots[0].search_query == ("Low-profile oak furniture in Japandi style.")
    assert manifest.product_slots[0].confidence == 0.91
