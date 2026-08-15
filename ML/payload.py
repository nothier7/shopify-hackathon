"""Strict adapter for the shared RoomSwipe model input and output JSON."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .contracts import DesignCandidate, ProductOffer, Questionnaire, SwipeEvent
from .model import OnlinePreferenceModel
from .ranking import rank_and_optimize, score_offers


STYLE_FIELDS = (
    "warmth",
    "minimalism",
    "natural_materials",
    "colorfulness",
    "modern",
    "vintage",
)
STYLE_FEATURES = {
    "warmth": "style:warm",
    "minimalism": "style:minimalist",
    "natural_materials": "feature:natural_materials",
    "colorfulness": "color:bold",
    "modern": "style:modern",
    "vintage": "style:vintage",
}
GOAL_ALIASES = {
    "cozy": "cozy",
    "expensive_looking": "look_expensive",
    "look_expensive": "look_expensive",
    "more_functional": "more_functional",
    "functional": "more_functional",
    "organized": "more_storage",
    "more_storage": "more_storage",
    "guest_ready": "guest_ready",
    "completely_new_vibe": "new_vibe",
}
STYLE_ALIASES = {"minimal": "minimalist"}


@dataclass(frozen=True, slots=True)
class ParsedPayload:
    raw: Mapping[str, Any]
    questionnaire: Questionnaire
    designs: tuple[DesignCandidate, ...]
    swipes: tuple[SwipeEvent, ...]
    comments: tuple[str, ...]
    offers: tuple[ProductOffer, ...]
    style_metadata: tuple[dict[str, float], ...]


def _slug(value: str) -> str:
    return "_".join(value.lower().replace("-", " ").split())


def _object(value: Any, path: str, keys: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise ValueError(f"{path} has missing={missing} extra={extra}")
    return value


def _array(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value.strip()


def _strings(value: Any, path: str) -> tuple[str, ...]:
    return tuple(_string(item, f"{path}[]") for item in _array(value, path))


def _number(value: Any, path: str, *, minimum: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{path} must be finite and >= {minimum}")
    return number


def _parse_payload(payload: Mapping[str, Any]) -> ParsedPayload:
    root = _object(
        payload,
        "$",
        {
            "questionnaire",
            "room_analysis",
            "designs_and_swipes",
            "iteration_request",
            "shopify_product_candidates",
        },
    )
    questionnaire_raw = _object(
        root["questionnaire"],
        "questionnaire",
        {"room_type", "budget", "effort_level", "goals", "style_preferences"},
    )
    budget = _object(
        questionnaire_raw["budget"], "questionnaire.budget", {"min_usd", "max_usd"}
    )
    minimum = _number(budget["min_usd"], "questionnaire.budget.min_usd")
    maximum = _number(budget["max_usd"], "questionnaire.budget.max_usd")
    if maximum < minimum:
        raise ValueError("questionnaire.budget.max_usd must be >= min_usd")
    goals = _strings(questionnaire_raw["goals"], "questionnaire.goals")
    styles = _strings(
        questionnaire_raw["style_preferences"], "questionnaire.style_preferences"
    )
    questionnaire = Questionnaire(
        room_type=_string(questionnaire_raw["room_type"], "questionnaire.room_type"),
        budget_minor=round(maximum * 100),
        effort=_string(questionnaire_raw["effort_level"], "questionnaire.effort_level"),
        goals=tuple(GOAL_ALIASES.get(_slug(goal), _slug(goal)) for goal in goals),
        optional_styles=tuple(
            STYLE_ALIASES.get(_slug(style), _slug(style)) for style in styles
        ),
    )

    room = _object(
        root["room_analysis"],
        "room_analysis",
        {
            "room_description",
            "approximate_geometry",
            "existing_furniture",
            "existing_colors",
            "lighting",
            "empty_spaces",
            "architectural_constraints",
        },
    )
    _string(room["room_description"], "room_analysis.room_description")
    _string(room["approximate_geometry"], "room_analysis.approximate_geometry")
    _strings(room["existing_furniture"], "room_analysis.existing_furniture")
    _strings(room["existing_colors"], "room_analysis.existing_colors")
    _string(room["lighting"], "room_analysis.lighting")
    _strings(room["empty_spaces"], "room_analysis.empty_spaces")
    _strings(
        room["architectural_constraints"],
        "room_analysis.architectural_constraints",
    )

    designs: list[DesignCandidate] = []
    swipes: list[SwipeEvent] = []
    metadata_rows: list[dict[str, float]] = []
    design_ids: set[str] = set()
    for index, value in enumerate(
        _array(root["designs_and_swipes"], "designs_and_swipes")
    ):
        path = f"designs_and_swipes[{index}]"
        design = _object(
            value,
            path,
            {
                "design_id",
                "name",
                "description",
                "style_metadata",
                "swipe",
                "user_comment",
            },
        )
        design_id = _string(design["design_id"], f"{path}.design_id")
        if design_id in design_ids:
            raise ValueError(f"duplicate design_id: {design_id}")
        design_ids.add(design_id)
        raw_metadata = _object(
            design["style_metadata"], f"{path}.style_metadata", set(STYLE_FIELDS)
        )
        metadata: dict[str, float] = {}
        attributes: dict[str, float] = {}
        for field in STYLE_FIELDS:
            score = _number(raw_metadata[field], f"{path}.style_metadata.{field}")
            if score > 1:
                raise ValueError(f"{path}.style_metadata.{field} must be <= 1")
            metadata[field] = score
            attributes[STYLE_FEATURES[field]] = 2 * score - 1
        swipe = _string(design["swipe"], f"{path}.swipe").lower()
        if swipe not in {"like", "pass"}:
            raise ValueError(f"{path}.swipe must be 'like' or 'pass'")
        comment = design["user_comment"]
        if not isinstance(comment, str):
            raise ValueError(f"{path}.user_comment must be a string")
        designs.append(
            DesignCandidate(
                id=design_id,
                name=_string(design["name"], f"{path}.name"),
                attributes=attributes,
            )
        )
        swipes.append(
            SwipeEvent(candidate_id=design_id, liked=swipe == "like", comment=comment)
        )
        metadata_rows.append(metadata)
    if not designs:
        raise ValueError("designs_and_swipes must not be empty")

    iteration = _object(
        root["iteration_request"], "iteration_request", {"user_comments"}
    )
    comments = _strings(iteration["user_comments"], "iteration_request.user_comments")

    offers: list[ProductOffer] = []
    product_ids: set[str] = set()
    product_keys = {
        "product_id",
        "title",
        "description",
        "category",
        "appearance",
        "style",
        "color",
        "material",
        "price_usd",
        "merchant",
    }
    for index, value in enumerate(
        _array(root["shopify_product_candidates"], "shopify_product_candidates")
    ):
        path = f"shopify_product_candidates[{index}]"
        product = _object(value, path, product_keys)
        product_id = _string(product["product_id"], f"{path}.product_id")
        if product_id in product_ids:
            raise ValueError(f"duplicate product_id: {product_id}")
        product_ids.add(product_id)
        category = _string(product["category"], f"{path}.category")
        offers.append(
            ProductOffer(
                product_id=product_id,
                variant_id="",
                slot_id=_slug(category),
                title=_string(product["title"], f"{path}.title"),
                merchant_name=_string(product["merchant"], f"{path}.merchant"),
                merchant_domain="",
                price_minor=round(
                    _number(product["price_usd"], f"{path}.price_usd") * 100
                ),
                currency="USD",
                image_url="",
                checkout_url="",
                available=True,
                description=_string(product["description"], f"{path}.description"),
                category=category,
                appearance=_string(product["appearance"], f"{path}.appearance"),
                style=_string(product["style"], f"{path}.style"),
                color=_string(product["color"], f"{path}.color"),
                material=_string(product["material"], f"{path}.material"),
            )
        )

    return ParsedPayload(
        raw=root,
        questionnaire=questionnaire,
        designs=tuple(designs),
        swipes=tuple(swipes),
        comments=comments,
        offers=tuple(offers),
        style_metadata=tuple(metadata_rows),
    )


def _sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(-60, min(60, value))))


def _profile_dimensions(model: OnlinePreferenceModel) -> dict[str, float]:
    return {
        field: round(_sigmoid(model.weights.get(feature, 0.0)), 4)
        for field, feature in STYLE_FEATURES.items()
    }


def _novelty(metadata: dict[str, float], liked: Sequence[dict[str, float]]) -> float:
    if not liked:
        return 1.0
    nearest = min(
        sum(abs(metadata[field] - other[field]) for field in STYLE_FIELDS)
        / len(STYLE_FIELDS)
        for other in liked
    )
    return max(0.0, min(1.0, nearest))


def _product_json(offer: ProductOffer) -> dict[str, Any]:
    score = offer.match_score or 0.0
    return {
        "product_id": offer.product_id,
        "title": offer.title,
        "category": offer.category,
        "merchant": offer.merchant_name,
        "price_usd": round(offer.price_minor / 100, 2),
        "score": round(score, 4),
        "match_percent": round(score * 100),
    }


def recommend_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the shared JSON and return the complete recommendation response."""
    parsed = _parse_payload(payload)
    model = OnlinePreferenceModel.from_questionnaire(parsed.questionnaire)
    for design, swipe in zip(parsed.designs, parsed.swipes, strict=True):
        model.observe(design, swipe)
    for comment in parsed.comments:
        model.observe_comment(comment)
    profile = model.to_profile()
    dimensions = _profile_dimensions(model)

    liked_metadata = [
        metadata
        for metadata, swipe in zip(parsed.style_metadata, parsed.swipes, strict=True)
        if swipe.liked
    ]
    exploration_weight = 0.25 * (1 - profile.confidence)
    ranked_designs: list[dict[str, Any]] = []
    for design, swipe, metadata in zip(
        parsed.designs, parsed.swipes, parsed.style_metadata, strict=True
    ):
        preference_match = model.predict(design)
        exploration_bonus = _novelty(metadata, liked_metadata)
        score = (1 - exploration_weight) * preference_match
        score += exploration_weight * exploration_bonus
        ranked_designs.append(
            {
                "design_id": design.id,
                "name": design.name,
                "score": round(max(0.0, min(1.0, score)), 4),
                "preference_match": preference_match,
                "exploration_bonus": round(exploration_bonus, 4),
                "original_swipe": "like" if swipe.liked else "pass",
            }
        )
    ranked_designs.sort(key=lambda item: (-item["score"], item["design_id"]))

    budget_minor = parsed.questionnaire.budget_minor
    ranked_offer_models = score_offers(profile, list(parsed.offers), budget_minor)
    selected_offer_models = rank_and_optimize(
        profile, list(parsed.offers), budget_minor
    )
    ranked_products = [_product_json(offer) for offer in ranked_offer_models]
    selected_products = [_product_json(offer) for offer in selected_offer_models]
    total_minor = sum(offer.price_minor for offer in selected_offer_models)
    average_product_score = (
        sum(offer.match_score or 0.0 for offer in selected_offer_models)
        / len(selected_offer_models)
        if selected_offer_models
        else ranked_designs[0]["preference_match"]
    )
    match_percent = round(
        100 * (0.8 * average_product_score + 0.2 * profile.confidence)
    )

    strongest = sorted(dimensions, key=dimensions.get, reverse=True)[:3]
    room_type = parsed.questionnaire.room_type.lower()
    raw_goals = parsed.raw["questionnaire"]["goals"]
    goal_text = ", ".join(str(goal).lower() for goal in raw_goals)
    direction = (
        f"A {', '.join(field.replace('_', '-') for field in strongest)} {room_type} "
        f"focused on {goal_text}, while preserving the listed room constraints."
    )
    positive_terms = [signal.split(":")[-1] for signal in profile.liked_signals]
    negative_terms = [signal.split(":")[-1] for signal in profile.disliked_signals]

    return {
        "preference_profile": {
            **dimensions,
            "confidence": profile.confidence,
            "positive_terms": positive_terms,
            "negative_terms": negative_terms,
        },
        "ranked_designs": ranked_designs,
        "ranked_products": ranked_products,
        "final_room": {
            "recommended_style": ranked_designs[0]["name"],
            "design_direction": direction,
            "match_percent": match_percent,
            "selected_products": selected_products,
            "total_usd": round(total_minor / 100, 2),
            "budget_max_usd": round(budget_minor / 100, 2),
            "remaining_usd": round((budget_minor - total_minor) / 100, 2),
        },
    }


__all__ = ["recommend_payload"]
