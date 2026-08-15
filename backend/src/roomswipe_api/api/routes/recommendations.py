from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from roomswipe_api.api.dependencies import get_recommendation_service
from roomswipe_api.schemas import (
    FinalizeRecommendationRequest,
    FinalizeRecommendationResponse,
    FinalRecommendationCandidate,
    FinalRecommendationResponse,
    PreferenceProfile,
    ProductOffer,
    SelectProductsRequest,
    UpdatePreferencesRequest,
)
from roomswipe_api.services.recommendation import (
    LocalRecommendationService,
    RecommendationInputError,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations — Nikita"])
RecommendationDependency = Annotated[
    LocalRecommendationService,
    Depends(get_recommendation_service),
]


@router.post("/finalize", response_model=FinalizeRecommendationResponse)
def finalize_recommendation(
    request: FinalizeRecommendationRequest,
    service: RecommendationDependency,
) -> FinalizeRecommendationResponse:
    try:
        return service.finalize(request)
    except RecommendationInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

FinalCandidatesBody = Annotated[
    list[FinalRecommendationCandidate], Body(min_length=10, max_length=10)
]


@router.post("/final-design", response_model=FinalRecommendationResponse)
async def recommend_final_design(
    candidates: FinalCandidatesBody,
    service: RecommendationDependency,
) -> FinalRecommendationResponse:
    try:
        return service.recommend_final_design(candidates=candidates)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.post("/preferences", response_model=PreferenceProfile)
async def update_preferences(
    request: UpdatePreferencesRequest,
    service: RecommendationDependency,
) -> PreferenceProfile:
    return service.update_preferences(
        candidates=request.candidates,
        swipes=request.swipes,
        prior=request.prior,
    )


@router.post("/select-products", response_model=list[ProductOffer])
async def select_products(
    request: SelectProductsRequest,
    service: RecommendationDependency,
) -> list[ProductOffer]:
    return service.rank_and_optimize(
        profile=request.profile,
        offers=request.offers,
        budget_minor=request.budget_minor,
    )
