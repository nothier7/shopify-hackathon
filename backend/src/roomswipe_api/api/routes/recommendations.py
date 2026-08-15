from fastapi import APIRouter, HTTPException, status

from roomswipe_api.schemas import (
    PreferenceProfile,
    ProductOffer,
    SelectProductsRequest,
    UpdatePreferencesRequest,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations — Nikita"])


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
