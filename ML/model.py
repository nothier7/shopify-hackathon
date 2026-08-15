"""Online logistic-regression model updated after every swipe."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .comments import parse_comment
from .contracts import (
    CandidatePrediction,
    DesignCandidate,
    PreferenceProfile,
    Questionnaire,
    SwipeEvent,
)
from .vocab import COLOR_TAGS, FEATURE_TAGS, GOAL_PRIORS, MATERIAL_TAGS


def _sigmoid(value: float) -> float:
    if value >= 0:
        exponent = math.exp(-min(value, 60))
        return 1 / (1 + exponent)
    exponent = math.exp(max(value, -60))
    return exponent / (1 + exponent)


def _attribute_key(raw: str) -> str:
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if ":" in key:
        return key
    if key in MATERIAL_TAGS:
        return f"material:{key}"
    if key in COLOR_TAGS and key != "warm":
        return f"color:{key}"
    if key in FEATURE_TAGS:
        return f"feature:{key}"
    return f"style:{key}"


def _features(candidate: DesignCandidate) -> dict[str, float]:
    features: dict[str, float] = {}
    for key, raw_value in candidate.attributes.items():
        value = float(raw_value)
        if not math.isfinite(value) or value == 0:
            continue
        features[_attribute_key(key)] = max(-1.0, min(1.0, value))
    return features


@dataclass(slots=True)
class OnlinePreferenceModel:
    weights: dict[str, float] = field(default_factory=dict)
    model_version: int = 0
    positive_count: int = 0
    negative_count: int = 0
    learning_rate: float = 0.9
    l2: float = 0.015
    dislike_weight: float = 0.65
    comment_step: float = 0.75

    @classmethod
    def from_profile(cls, profile: PreferenceProfile | None) -> OnlinePreferenceModel:
        if profile is None:
            return cls()
        return cls(
            weights=dict(profile.attributes),
            model_version=profile.model_version,
            positive_count=profile.positive_count,
            negative_count=profile.negative_count,
        )

    @classmethod
    def from_questionnaire(
        cls, questionnaire: Questionnaire | None
    ) -> OnlinePreferenceModel:
        model = cls()
        if questionnaire is None:
            return model
        for goal in questionnaire.goals:
            for key, value in GOAL_PRIORS.get(goal, {}).items():
                model.weights[key] = model.weights.get(key, 0.0) + value
        for style in questionnaire.optional_styles:
            key = _attribute_key(style)
            model.weights[key] = model.weights.get(key, 0.0) + 0.35
        return model

    def _raw_probability(self, candidate: DesignCandidate) -> float:
        features = _features(candidate)
        if not features:
            return 0.5
        norm = math.sqrt(sum(value * value for value in features.values())) or 1.0
        score = (
            sum(self.weights.get(key, 0.0) * value for key, value in features.items())
            / norm
        )
        return _sigmoid(score)

    def predict(self, candidate: DesignCandidate) -> float:
        raw = self._raw_probability(candidate)
        confidence = 1 - math.exp(-self.model_version / 3.0)
        return round(0.5 + (raw - 0.5) * (0.35 + 0.65 * confidence), 4)

    def observe(self, candidate: DesignCandidate, swipe: SwipeEvent) -> float:
        probability_before = self.predict(candidate)
        features = _features(candidate)
        target = 1.0 if swipe.liked else 0.0
        sample_weight = 1.0 if swipe.liked else self.dislike_weight
        error = (target - self._raw_probability(candidate)) * sample_weight
        norm = math.sqrt(sum(value * value for value in features.values())) or 1.0

        for key in list(self.weights):
            self.weights[key] *= 1 - self.learning_rate * self.l2
        for key, value in features.items():
            self.weights[key] = (
                self.weights.get(key, 0.0) + self.learning_rate * error * value / norm
            )

        reinforced, suppressed = parse_comment(swipe.comment)
        for key in reinforced:
            self.weights[key] = self.weights.get(key, 0.0) + self.comment_step
        for key in suppressed:
            self.weights[key] = self.weights.get(key, 0.0) - self.comment_step

        self.model_version += 1
        self.positive_count += int(swipe.liked)
        self.negative_count += int(not swipe.liked)
        return probability_before

    def to_profile(self) -> PreferenceProfile:
        ranked = sorted(self.weights.items(), key=lambda item: item[1], reverse=True)
        return PreferenceProfile(
            attributes={key: round(value, 5) for key, value in self.weights.items()},
            confidence=round(1 - math.exp(-self.model_version / 4.0), 4),
            liked_signals=tuple(key for key, value in ranked if value > 0.05)[:6],
            disliked_signals=tuple(
                key
                for key, value in sorted(self.weights.items(), key=lambda item: item[1])
                if value < -0.05
            )[:6],
            model_version=self.model_version,
            positive_count=self.positive_count,
            negative_count=self.negative_count,
        )

    def predict_many(
        self, candidates: list[DesignCandidate]
    ) -> tuple[CandidatePrediction, ...]:
        ranked = sorted(
            ((candidate.id, self.predict(candidate)) for candidate in candidates),
            key=lambda item: item[1],
            reverse=True,
        )
        return tuple(
            CandidatePrediction(
                candidate_id=candidate_id, like_probability=score, rank=index
            )
            for index, (candidate_id, score) in enumerate(ranked, start=1)
        )
