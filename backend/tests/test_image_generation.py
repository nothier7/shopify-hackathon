import json
import random

import httpx

from roomswipe_api.config import Settings
from roomswipe_api.schemas import Questionnaire, RoomAnalysis
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
