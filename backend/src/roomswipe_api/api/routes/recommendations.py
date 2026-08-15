from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from roomswipe_api.api.dependencies import get_recommendation_service
from roomswipe_api.schemas import (
    FinalizeRecommendationRequest,
    FinalizeRecommendationResponse,
    PreferenceProfile,
    ProductOffer,
    SelectProductsRequest,
    UpdatePreferencesRequest,
)
from roomswipe_api.services.recommendation import (
    MlRecommendationService,
    RecommendationInputError,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations — Nikita"])
RecommendationEngine = Annotated[
    MlRecommendationService,
    Depends(get_recommendation_service),
]


@router.post("/finalize", response_model=FinalizeRecommendationResponse)
def finalize_recommendation(
    request: FinalizeRecommendationRequest,
    service: RecommendationEngine,
) -> FinalizeRecommendationResponse:
    try:
        return service.finalize(request)
    except RecommendationInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.post("/preferences", response_model=PreferenceProfile)
async def update_preferences(request: UpdatePreferencesRequest) -> PreferenceProfile:
    del request
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Recommendation service is not connected yet.",
    )


@router.post("/select-products", response_model=list[ProductOffer])
async def select_products(request: SelectProductsRequest) -> list[ProductOffer]:
    del request
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Product ranking service is not connected yet.",
    )
