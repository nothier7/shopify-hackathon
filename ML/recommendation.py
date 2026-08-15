"""Public functions for online preference learning and product ranking."""

from __future__ import annotations

from .contracts import (
    CandidatePrediction,
    DesignCandidate,
    OnlineSwipeResult,
    PreferenceProfile,
    ProductOffer,
    Questionnaire,
    SwipeEvent,
)
from .model import OnlinePreferenceModel
from .ranking import rank_and_optimize, score_offers


def update_after_swipe(
    candidates: list[DesignCandidate],
    swipe: SwipeEvent,
    prior: PreferenceProfile | None = None,
    questionnaire: Questionnaire | None = None,
) -> OnlineSwipeResult:
    candidate_by_id = {candidate.id: candidate for candidate in candidates}
    candidate = candidate_by_id.get(swipe.candidate_id)
    if candidate is None:
        raise ValueError("The swiped candidate is missing from candidates.")
    model = (
        OnlinePreferenceModel.from_profile(prior)
        if prior is not None
        else OnlinePreferenceModel.from_questionnaire(questionnaire)
    )
    observed = model.observe(candidate, swipe)
    remaining = [item for item in candidates if item.id != candidate.id]
    return OnlineSwipeResult(
        profile=model.to_profile(),
        observed_like_probability=observed,
        predictions=model.predict_many(remaining),
    )


def update_preferences(
    candidates: list[DesignCandidate],
    swipes: list[SwipeEvent],
    prior: PreferenceProfile | None = None,
) -> PreferenceProfile:
    model = OnlinePreferenceModel.from_profile(prior)
    candidate_by_id = {candidate.id: candidate for candidate in candidates}
    for swipe in swipes:
        candidate = candidate_by_id.get(swipe.candidate_id)
        if candidate is not None:
            model.observe(candidate, swipe)
    return model.to_profile()


def predict_candidates(
    candidates: list[DesignCandidate],
    profile: PreferenceProfile,
) -> tuple[CandidatePrediction, ...]:
    return OnlinePreferenceModel.from_profile(profile).predict_many(candidates)


__all__ = [
    "ProductOffer",
    "predict_candidates",
    "rank_and_optimize",
    "score_offers",
    "update_after_swipe",
    "update_preferences",
]
