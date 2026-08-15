from __future__ import annotations

import json
import unittest
from pathlib import Path

from ML import (
    DesignCandidate,
    PreferenceProfile,
    ProductOffer,
    Questionnaire,
    SwipeEvent,
    rank_and_optimize,
    recommend_payload,
    update_after_swipe,
)


REPOSITORY_ROOT = Path(__file__).parents[2]


def candidate(candidate_id: str, **attributes: float) -> DesignCandidate:
    return DesignCandidate(
        id=candidate_id, name=candidate_id.replace("_", " "), attributes=attributes
    )


def offer(
    product_id: str,
    slot_id: str,
    title: str,
    price_minor: int,
    match_score: float,
) -> ProductOffer:
    return ProductOffer(
        product_id=product_id,
        variant_id=f"variant-{product_id}",
        slot_id=slot_id,
        title=title,
        merchant_name="Example merchant",
        merchant_domain="example.com",
        price_minor=price_minor,
        currency="USD",
        image_url="https://example.com/product.jpg",
        checkout_url="https://example.com/checkout",
        available=True,
        match_score=match_score,
    )


class RecommendationTests(unittest.TestCase):
    def test_like_updates_probability_and_predictions(self) -> None:
        warm = candidate("warm", **{"style:warm": 1, "material:wood": 1})
        cold = candidate("cold", **{"style:modern": 1, "color:cool": 1})
        result = update_after_swipe(
            [warm, cold],
            SwipeEvent(candidate_id="warm", liked=True, comment="More plants and wood"),
            questionnaire=Questionnaire(
                room_type="bedroom",
                budget_minor=100_000,
                effort="buy_only",
                goals=("cozy",),
            ),
        )
        self.assertEqual(result.profile.model_version, 1)
        self.assertEqual(result.profile.positive_count, 1)
        self.assertIn("feature:plants", result.profile.liked_signals)
        self.assertEqual(result.predictions[0].candidate_id, "cold")

    def test_pass_reduces_similar_prediction(self) -> None:
        cold = candidate("cold", **{"style:modern": 1, "color:cool": 1})
        first = update_after_swipe([cold], SwipeEvent(candidate_id="cold", liked=False))
        second = update_after_swipe(
            [cold],
            SwipeEvent(candidate_id="cold", liked=False),
            prior=first.profile,
        )
        self.assertLess(
            second.observed_like_probability, first.observed_like_probability
        )

    def test_product_selection_respects_budget_and_slots(self) -> None:
        profile = PreferenceProfile(
            attributes={"material:wood": 1.2, "style:warm": 0.8},
            confidence=0.8,
            liked_signals=("material:wood",),
            model_version=5,
            positive_count=3,
            negative_count=2,
        )
        offers = [
            offer("chair-expensive", "chair", "Warm wood chair", 7000, 0.95),
            offer("chair-value", "chair", "Warm wood chair", 4500, 0.88),
            offer("lamp", "lighting", "Warm linen lamp", 3500, 0.84),
        ]
        selected = rank_and_optimize(profile, offers, 8000)
        self.assertLessEqual(sum(item.price_minor for item in selected), 8000)
        self.assertEqual(
            {item.product_id for item in selected}, {"chair-value", "lamp"}
        )

    def test_shared_input_produces_documented_output(self) -> None:
        payload = json.loads(
            (REPOSITORY_ROOT / "model_input.example.json").read_text(encoding="utf-8")
        )
        expected = json.loads(
            (REPOSITORY_ROOT / "model_output.example.json").read_text(encoding="utf-8")
        )
        actual = recommend_payload(payload)
        self.assertEqual(actual, expected)
        self.assertEqual(set(actual), {"recommendedDesign"})
        item_caps = [
            item["maxPriceMinor"] for item in actual["recommendedDesign"]["items"]
        ]
        self.assertLessEqual(
            sum(item_caps), actual["recommendedDesign"]["budget"]["maxTotalMinor"]
        )

    def test_shared_input_is_strict_and_comment_is_optional(self) -> None:
        payload = json.loads(
            (REPOSITORY_ROOT / "model_input.example.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("comment", payload[4])
        recommend_payload(payload)

        payload[0]["photoData"] = "not accepted"
        with self.assertRaisesRegex(ValueError, "extra=.*photoData"):
            recommend_payload(payload)

    def test_shared_input_requires_exactly_ten_swipes(self) -> None:
        payload = json.loads(
            (REPOSITORY_ROOT / "model_input.example.json").read_text(encoding="utf-8")
        )
        with self.assertRaisesRegex(ValueError, "exactly 10"):
            recommend_payload(payload[:-1])


if __name__ == "__main__":
    unittest.main()
