import json
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from roomswipe_api.api.routes.images import _read_room_image, _stream_models
from roomswipe_api.schemas import DesignCandidate, Questionnaire


async def test_stream_models_emits_valid_camel_case_json() -> None:
    response = _stream_models([candidate()])
    chunks: list[str] = []

    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)

    payload = json.loads("".join(chunks))
    assert payload[0]["imageUrl"] == "data:image/png;base64,image"
    assert payload[0]["questionnaire"]["budgetMinor"] == 50_000
    assert response.headers["content-type"] == "application/json"


async def test_room_image_limit_stays_below_vercel_function_limit() -> None:
    upload = UploadFile(filename="room.jpg", file=BytesIO(b"x" * 4_000_001))

    with pytest.raises(HTTPException) as raised:
        await _read_room_image(upload)

    assert raised.value.status_code == 413
    assert raised.value.detail == "Choose a room image smaller than 4MB."


def candidate() -> DesignCandidate:
    return DesignCandidate(
        id="room-1",
        name="Japandi",
        image_url="data:image/png;base64,image",
        attributes={"warmth": 0.8},
        warmth=0.8,
        lighting="soft",
        items=["lamp"],
        questionnaire=Questionnaire(
            room_type="living room",
            budget_minor=50_000,
            effort="buy_only",
            design_density="minimalist",
            user_age=28,
            goals=["cozy"],
        ),
    )
