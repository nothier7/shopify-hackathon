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
