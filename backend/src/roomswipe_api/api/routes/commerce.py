from fastapi import APIRouter, HTTPException, status

from roomswipe_api.schemas import (
    CreateCartsRequest,
    MerchantCart,
    ProductOffer,
    SearchProductsRequest,
)

router = APIRouter(prefix="/commerce", tags=["commerce — Thierno"])


@router.post("/search", response_model=list[ProductOffer])
async def search_products(request: SearchProductsRequest) -> list[ProductOffer]:
    del request
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Shopify Global Catalog service is not connected yet.",
    )


@router.post("/carts", response_model=list[MerchantCart])
async def create_carts(request: CreateCartsRequest) -> list[MerchantCart]:
    del request
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Shopify cart service is not connected yet.",
    )
