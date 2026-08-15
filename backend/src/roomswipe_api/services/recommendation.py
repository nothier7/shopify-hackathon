"""Backend adapter for Nikita's RoomSwipe recommendation engine."""

from typing import Protocol

from ML import (
    DesignCandidate as MlDesignCandidate,
)
from ML import (
    PreferenceProfile as MlPreferenceProfile,
)
from ML import (
    ProductOffer as MlProductOffer,
)
from ML import (
    SwipeEvent as MlSwipeEvent,
)
from ML import (
    rank_and_optimize as ml_rank_and_optimize,
)
from ML import (
    recommend_payload,
)
from ML import (
    update_preferences as ml_update_preferences,
)

from roomswipe_api.schemas import (
    DesignCandidate,
    FinalRecommendationCandidate,
    FinalRecommendationResponse,
    PreferenceProfile,
    ProductOffer,
    SwipeEvent,
)


class RecommendationService(Protocol):
    def recommend_final_design(
        self, *, candidates: list[FinalRecommendationCandidate]
    ) -> FinalRecommendationResponse: ...

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


class LocalRecommendationService:
    """Translate API schemas to the dependency-free ML contracts."""

    def recommend_final_design(
        self, *, candidates: list[FinalRecommendationCandidate]
    ) -> FinalRecommendationResponse:
        payload = [
            candidate.model_dump(mode="json", by_alias=True, exclude_none=True)
            for candidate in candidates
        ]
        return FinalRecommendationResponse.model_validate(recommend_payload(payload))

    def update_preferences(
        self,
        *,
        candidates: list[DesignCandidate],
        swipes: list[SwipeEvent],
        prior: PreferenceProfile | None = None,
    ) -> PreferenceProfile:
        learned = ml_update_preferences(
            [
                MlDesignCandidate(
                    id=candidate.id,
                    name=candidate.name,
                    image_url=candidate.image_url,
                    attributes=candidate.attributes,
                )
                for candidate in candidates
            ],
            [
                MlSwipeEvent(
                    candidate_id=swipe.candidate_id,
                    liked=swipe.liked,
                    comment=swipe.comment,
                )
                for swipe in swipes
            ],
            self._to_ml_profile(prior) if prior else None,
        )
        return self._from_ml_profile(learned)

    def rank_and_optimize(
        self,
        *,
        profile: PreferenceProfile,
        offers: list[ProductOffer],
        budget_minor: int,
    ) -> list[ProductOffer]:
        selected = ml_rank_and_optimize(
            self._to_ml_profile(profile),
            [self._to_ml_offer(offer) for offer in offers],
            budget_minor,
        )
        selected_by_id = {offer.product_id: offer for offer in selected}
        return [
            offer.model_copy(update={"match_score": selected_by_id[offer.product_id].match_score})
            for offer in offers
            if offer.product_id in selected_by_id
        ]

    @staticmethod
    def _to_ml_profile(profile: PreferenceProfile) -> MlPreferenceProfile:
        return MlPreferenceProfile(
            attributes=dict(profile.attributes),
            confidence=profile.confidence,
            liked_signals=tuple(profile.liked_signals),
            disliked_signals=tuple(profile.disliked_signals),
            model_version=profile.model_version,
            positive_count=profile.positive_count,
            negative_count=profile.negative_count,
        )

    @staticmethod
    def _from_ml_profile(profile: MlPreferenceProfile) -> PreferenceProfile:
        return PreferenceProfile(
            attributes=profile.attributes,
            confidence=profile.confidence,
            liked_signals=list(profile.liked_signals),
            disliked_signals=list(profile.disliked_signals),
            model_version=profile.model_version,
            positive_count=profile.positive_count,
            negative_count=profile.negative_count,
        )

    @staticmethod
    def _to_ml_offer(offer: ProductOffer) -> MlProductOffer:
        return MlProductOffer(
            product_id=offer.product_id,
            variant_id=offer.variant_id,
            slot_id=offer.slot_id,
            title=offer.title,
            merchant_name=offer.merchant_name,
            merchant_domain=offer.merchant_domain,
            price_minor=offer.price_minor,
            currency=offer.currency,
            image_url=offer.image_url or "",
            checkout_url=offer.checkout_url,
            available=offer.available,
            match_score=offer.match_score,
        )
