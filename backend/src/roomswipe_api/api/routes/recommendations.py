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
async def update_preferences(
    request: UpdatePreferencesRequest,
    service: RecommendationEngine,
) -> PreferenceProfile:
    return service.update_preferences(
        candidates=request.candidates,
        swipes=request.swipes,
        prior=request.prior,
    )


@router.post("/select-products", response_model=list[ProductOffer])
async def select_products(
    request: SelectProductsRequest,
    service: RecommendationEngine,
) -> list[ProductOffer]:
    return service.rank_and_optimize(
        profile=request.profile,
        offers=request.offers,
        budget_minor=request.budget_minor,
    )
