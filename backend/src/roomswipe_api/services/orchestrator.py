"""Cross-service dependency container for the RoomSwipe workflow."""

from dataclasses import dataclass

from roomswipe_api.schemas import (
    FinalDesignManifest,
    FinalRecommendationCandidate,
    RoomAnalysis,
)
from roomswipe_api.services.image_generation import ImageGenerationService
from roomswipe_api.services.recommendation import RecommendationService
from roomswipe_api.services.shopify_ucp import ShopifyCommerceService


@dataclass(frozen=True, slots=True)
class RoomSwipeServices:
    images: ImageGenerationService
    recommendations: RecommendationService
    commerce: ShopifyCommerceService


class RoomSwipeOrchestrator:
    def __init__(self, services: RoomSwipeServices) -> None:
        self.services = services

    async def generate_recommended_room(
        self,
        *,
        room: RoomAnalysis,
        candidates: list[FinalRecommendationCandidate],
    ) -> FinalDesignManifest:
        recommendation = self.services.recommendations.recommend_final_design(candidates=candidates)
        return await self.services.images.generate_final_design(
            room=room,
            recommendation=recommendation.recommended_design,
        )
