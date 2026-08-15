"""Nikita's preference-learning and product-selection service boundary."""

from typing import Protocol

from roomswipe_api.schemas import (
    DesignCandidate,
    PreferenceProfile,
    ProductOffer,
    SwipeEvent,
)


class RecommendationService(Protocol):
    def update_preferences(
        self,
        *,
        candidates: list[DesignCandidate],
        swipes: list[SwipeEvent],
        prior: PreferenceProfile | None = None,
    ) -> PreferenceProfile: ...

    def rank_and_optimize(
        self,
        *,
        profile: PreferenceProfile,
        offers: list[ProductOffer],
        budget_minor: int,
    ) -> list[ProductOffer]: ...
