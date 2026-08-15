"""Nikita's preference-learning adapter and service boundary."""

from collections.abc import Mapping
from typing import Any, Protocol

from ML import recommend_payload

from roomswipe_api.schemas import (
    DesignCandidate,
    FinalizeRecommendationRequest,
    FinalizeRecommendationResponse,
    PreferenceProfile,
    ProductOffer,
    SwipeEvent,
)


class RecommendationInputError(ValueError):
    """The recommendation payload does not satisfy the ML contract."""


class MlRecommendationService:
    def finalize(
        self,
        request: FinalizeRecommendationRequest,
    ) -> FinalizeRecommendationResponse:
        swipes = {swipe.candidate_id: swipe for swipe in request.swipes}
        payload: list[dict[str, Any]] = []
        for candidate in request.candidates:
            item = candidate.model_dump(mode="json", by_alias=True)
            swipe = swipes[candidate.id]
            item["like"] = "Yes" if swipe.liked else "No"
            if swipe.comment is not None:
                item["comment"] = swipe.comment
            payload.append(item)

        try:
            result = recommend_payload(payload)
            if not isinstance(result, Mapping):
                raise ValueError("recommendation output must be an object")
            return FinalizeRecommendationResponse.model_validate(result)
        except ValueError as exc:
            raise RecommendationInputError(str(exc)) from exc


class RecommendationService(Protocol):
    def finalize(
        self,
        request: FinalizeRecommendationRequest,
    ) -> FinalizeRecommendationResponse: ...

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
