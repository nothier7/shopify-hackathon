"""Strict adapter for the ten-design RoomSwipe input and final-design output."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .contracts import DesignCandidate, Questionnaire, SwipeEvent
from .model import OnlinePreferenceModel


CANDIDATE_KEYS = {
    "id",
    "name",
    "imageUrl",
    "attributes",
    "warmth",
    "lighting",
    "items",
    "questionnaire",
    "like",
}
QUESTIONNAIRE_KEYS = {
    "roomType",
    "budgetMinor",
    "currency",
    "effort",
    "designDensity",
    "userAge",
    "goals",
    "optionalStyles",
}
REQUIRED_ATTRIBUTES = {"minimalism", "warmth", "color"}
ATTRIBUTE_FEATURES = {
    "minimalism": "style:minimalist",
    "warmth": "style:warm",
    "color": "color:bold",
}
GOAL_ALIASES = {
    "comfortable_seating": "guest_ready",
    "cozy": "cozy",
    "expensive_looking": "look_expensive",
    "functional": "more_functional",
    "guest_ready": "guest_ready",
    "completely_new_vibe": "new_vibe",
    "more_functional": "more_functional",
    "more_storage": "more_storage",
    "organized": "more_storage",
    "small_work_corner": "more_functional",
}
STYLE_ALIASES = {"minimal": "minimalist"}
GOAL_ITEMS = {
    "seating": "compact comfortable seating",
    "work": "compact work desk",
    "storage": "space-saving storage unit",
    "lighting": "layered room lighting",
    "guest": "flexible guest seating",
}


@dataclass(frozen=True, slots=True)
class ParsedCandidate:
    model_candidate: DesignCandidate
    swipe: SwipeEvent
    lighting: str
    items: tuple[str, ...]
    attributes: dict[str, float]


@dataclass(frozen=True, slots=True)
class ParsedPayload:
    questionnaire: Questionnaire
    raw_goals: tuple[str, ...]
    design_density: str
    candidates: tuple[ParsedCandidate, ...]


def _slug(value: str) -> str:
    return "_".join(value.lower().replace("-", " ").split())


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    return value


def _array(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return value


def _string(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        qualifier = "a string" if allow_empty else "a non-empty string"
        raise ValueError(f"{path} must be {qualifier}")
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


def _parse_questionnaire(
    value: Any, path: str
) -> tuple[Questionnaire, str, tuple[str, ...], dict[str, Any]]:
    raw = _object(value, path)
    actual = set(raw)
    if actual != QUESTIONNAIRE_KEYS:
        raise ValueError(
            f"{path} has missing={sorted(QUESTIONNAIRE_KEYS - actual)} "
            f"extra={sorted(actual - QUESTIONNAIRE_KEYS)}"
        )
    budget = _number(raw["budgetMinor"], f"{path}.budgetMinor")
    if not float(budget).is_integer():
        raise ValueError(f"{path}.budgetMinor must be an integer")
    age = _number(raw["userAge"], f"{path}.userAge")
    if not float(age).is_integer():
        raise ValueError(f"{path}.userAge must be an integer")
    currency = _string(raw["currency"], f"{path}.currency").upper()
    if len(currency) != 3:
        raise ValueError(f"{path}.currency must have three characters")
    goals = _strings(raw["goals"], f"{path}.goals")
    optional_styles = _strings(raw["optionalStyles"], f"{path}.optionalStyles")
    density = _string(raw["designDensity"], f"{path}.designDensity")
    questionnaire = Questionnaire(
        room_type=_string(raw["roomType"], f"{path}.roomType"),
        budget_minor=int(budget),
        currency=currency,
        effort=_string(raw["effort"], f"{path}.effort"),
        goals=tuple(GOAL_ALIASES.get(_slug(goal), _slug(goal)) for goal in goals),
        optional_styles=(
            STYLE_ALIASES.get(_slug(density), _slug(density)),
            *(
                STYLE_ALIASES.get(_slug(style), _slug(style))
                for style in optional_styles
            ),
        ),
    )
    normalized_raw = {
        "roomType": questionnaire.room_type,
        "budgetMinor": questionnaire.budget_minor,
        "currency": questionnaire.currency,
        "effort": questionnaire.effort,
        "designDensity": density,
        "userAge": int(age),
        "goals": list(goals),
        "optionalStyles": list(optional_styles),
    }
    return questionnaire, density, goals, normalized_raw


def _parse_payload(payload: Sequence[Any]) -> ParsedPayload:
    candidates_raw = _array(payload, "$")
    if len(candidates_raw) != 10:
        raise ValueError("$ must contain exactly 10 design candidates")

    parsed: list[ParsedCandidate] = []
    expected_questionnaire: dict[str, Any] | None = None
    questionnaire: Questionnaire | None = None
    raw_goals: tuple[str, ...] = ()
    design_density = ""
    candidate_ids: set[str] = set()

    for index, value in enumerate(candidates_raw):
        path = f"$[{index}]"
        raw = _object(value, path)
        actual = set(raw)
        allowed = CANDIDATE_KEYS | {"comment"}
        missing = CANDIDATE_KEYS - actual
        extra = actual - allowed
        if missing or extra:
            raise ValueError(
                f"{path} has missing={sorted(missing)} extra={sorted(extra)}"
            )

        candidate_id = _string(raw["id"], f"{path}.id")
        if candidate_id in candidate_ids:
            raise ValueError(f"duplicate candidate id: {candidate_id}")
        candidate_ids.add(candidate_id)
        _string(
            raw["imageUrl"], f"{path}.imageUrl"
        )  # Transport-only; ML ignores pixels.
        lighting = _string(raw["lighting"], f"{path}.lighting")
        items = _strings(raw["items"], f"{path}.items")
        if not items:
            raise ValueError(f"{path}.items must not be empty")

        attributes_raw = _object(raw["attributes"], f"{path}.attributes")
        if set(attributes_raw) != REQUIRED_ATTRIBUTES:
            raise ValueError(
                f"{path}.attributes has missing="
                f"{sorted(REQUIRED_ATTRIBUTES - set(attributes_raw))} "
                f"extra={sorted(set(attributes_raw) - REQUIRED_ATTRIBUTES)}"
            )
        attributes: dict[str, float] = {}
        model_attributes: dict[str, float] = {}
        for attribute, feature in ATTRIBUTE_FEATURES.items():
            score = _number(attributes_raw[attribute], f"{path}.attributes.{attribute}")
            if score > 1:
                raise ValueError(f"{path}.attributes.{attribute} must be <= 1")
            attributes[attribute] = score
            model_attributes[feature] = 2 * score - 1
        warmth = _number(raw["warmth"], f"{path}.warmth")
        if warmth > 1 or not math.isclose(warmth, attributes["warmth"], abs_tol=0.001):
            raise ValueError(f"{path}.warmth must equal attributes.warmth")

        (
            current_questionnaire,
            current_density,
            current_goals,
            normalized_questionnaire,
        ) = _parse_questionnaire(raw["questionnaire"], f"{path}.questionnaire")
        if expected_questionnaire is None:
            expected_questionnaire = normalized_questionnaire
            questionnaire = current_questionnaire
            raw_goals = current_goals
            design_density = current_density
        elif normalized_questionnaire != expected_questionnaire:
            raise ValueError("all 10 candidates must contain the same questionnaire")

        like = _string(raw["like"], f"{path}.like").lower()
        if like not in {"yes", "no"}:
            raise ValueError(f"{path}.like must be 'Yes' or 'No'")
        comment_value = raw.get("comment", "")
        comment = _string(comment_value, f"{path}.comment", allow_empty=True)
        parsed.append(
            ParsedCandidate(
                model_candidate=DesignCandidate(
                    id=candidate_id,
                    name=_string(raw["name"], f"{path}.name"),
                    attributes=model_attributes,
                ),
                swipe=SwipeEvent(
                    candidate_id=candidate_id,
                    liked=like == "yes",
                    comment=comment,
                ),
                lighting=lighting,
                items=items,
                attributes=attributes,
            )
        )

    assert questionnaire is not None
    return ParsedPayload(
        questionnaire=questionnaire,
        raw_goals=raw_goals,
        design_density=design_density,
        candidates=tuple(parsed),
    )


def _goal_items(goals: Sequence[str]) -> list[tuple[str, str]]:
    inferred: list[tuple[str, str]] = []
    for goal in goals:
        lowered = goal.lower()
        for marker, item_name in GOAL_ITEMS.items():
            if marker in lowered:
                inferred.append((item_name, goal))
                break
    return inferred


def _item_predictions(
    chosen: ParsedCandidate,
    questionnaire: Questionnaire,
    raw_goals: Sequence[str],
    design_density: str,
) -> list[dict[str, Any]]:
    item_sources: list[tuple[str, str]] = [
        (item, "selected design") for item in chosen.items
    ]
    existing_tokens = " ".join(chosen.items).lower()
    for item, goal in _goal_items(raw_goals):
        significant_tokens = [token for token in item.split() if len(token) > 4]
        if any(token in existing_tokens for token in significant_tokens):
            continue
        item_sources.append((item, f'questionnaire goal "{goal}"'))

    budget = questionnaire.budget_minor
    base_cap, remainder = divmod(budget, len(item_sources))
    predictions: list[dict[str, Any]] = []
    for index, (item, source) in enumerate(item_sources):
        max_price = base_cap + (remainder if index == 0 else 0)
        description = (
            f"{item.capitalize()} matching the {chosen.model_candidate.name} direction, "
            f"with {chosen.lighting}, for a {design_density.lower()} "
            f"{questionnaire.room_type.lower()}; derived from the {source}."
        )
        predictions.append(
            {
                "name": item,
                "description": description,
                "maxPriceMinor": max_price,
                "currency": questionnaire.currency,
            }
        )
    return predictions


def recommend_payload(payload: Sequence[Any]) -> dict[str, Any]:
    """Learn from ten swipes and return one design with Shopify search descriptions."""
    parsed = _parse_payload(payload)
    model = OnlinePreferenceModel.from_questionnaire(parsed.questionnaire)
    for candidate in parsed.candidates:
        model.observe(candidate.model_candidate, candidate.swipe)

    eligible = [candidate for candidate in parsed.candidates if candidate.swipe.liked]
    if not eligible:
        eligible = list(parsed.candidates)
    chosen = max(
        eligible,
        key=lambda candidate: (
            model.predict(candidate.model_candidate),
            candidate.model_candidate.id,
        ),
    )
    match_score = model.predict(chosen.model_candidate)
    item_predictions = _item_predictions(
        chosen,
        parsed.questionnaire,
        parsed.raw_goals,
        parsed.design_density,
    )
    strongest = sorted(
        chosen.attributes,
        key=chosen.attributes.get,
        reverse=True,
    )[:2]
    design_description = (
        f"A {parsed.design_density.lower()} {parsed.questionnaire.room_type.lower()} "
        f"in the {chosen.model_candidate.name} direction, emphasizing "
        f"{strongest[0]} and {strongest[1]} with {chosen.lighting}."
    )

    return {
        "recommendedDesign": {
            "name": chosen.model_candidate.name,
            "description": design_description,
            "matchPercent": round(match_score * 100),
            "items": item_predictions,
            "budget": {
                "maxTotalMinor": parsed.questionnaire.budget_minor,
                "currency": parsed.questionnaire.currency,
            },
        }
    }


__all__ = ["recommend_payload"]
