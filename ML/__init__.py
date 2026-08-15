"""Standalone RoomSwipe preference-learning module."""

from .contracts import (
    CandidatePrediction,
    DesignCandidate,
    OnlineSwipeResult,
    PreferenceProfile,
    ProductOffer,
    Questionnaire,
    SwipeEvent,
)
from .recommendation import (
    predict_candidates,
    rank_and_optimize,
    update_after_swipe,
    update_preferences,
)

__all__ = [
    "CandidatePrediction",
    "DesignCandidate",
    "OnlineSwipeResult",
    "PreferenceProfile",
    "ProductOffer",
    "Questionnaire",
    "SwipeEvent",
    "predict_candidates",
    "rank_and_optimize",
    "update_after_swipe",
    "update_preferences",
]
