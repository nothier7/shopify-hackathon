"""Dependency-free contracts for the standalone ML module."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Questionnaire:
    room_type: str
    budget_minor: int
    effort: str
    goals: tuple[str, ...] = ()
    optional_styles: tuple[str, ...] = ()
    currency: str = "USD"


@dataclass(frozen=True, slots=True)
class DesignCandidate:
    id: str
    name: str
    attributes: dict[str, float]
    image_url: str = ""


@dataclass(frozen=True, slots=True)
class SwipeEvent:
    candidate_id: str
    liked: bool
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class PreferenceProfile:
    attributes: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    liked_signals: tuple[str, ...] = ()
    disliked_signals: tuple[str, ...] = ()
    model_version: int = 0
    positive_count: int = 0
    negative_count: int = 0


@dataclass(frozen=True, slots=True)
class CandidatePrediction:
    candidate_id: str
    like_probability: float
    rank: int


@dataclass(frozen=True, slots=True)
class OnlineSwipeResult:
    profile: PreferenceProfile
    observed_like_probability: float
    predictions: tuple[CandidatePrediction, ...]


@dataclass(frozen=True, slots=True)
class ProductOffer:
    product_id: str
    variant_id: str
    slot_id: str
    title: str
    merchant_name: str
    merchant_domain: str
    price_minor: int
    currency: str
    image_url: str
    checkout_url: str
    available: bool
    match_score: float | None = None
    description: str = ""
    category: str = ""
    appearance: str = ""
    style: str = ""
    color: str = ""
    material: str = ""
