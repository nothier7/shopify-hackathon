"""Cross-service dependency container for the RoomSwipe workflow."""

from dataclasses import dataclass

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
