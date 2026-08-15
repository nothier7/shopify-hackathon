from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from roomswipe_api.api.dependencies import (
    get_shopify_cart_service,
    get_shopify_catalog_service,
)
from roomswipe_api.schemas import (
    CreateCartsRequest,
    CreateCartsResponse,
    ProductOffer,
    SearchProductsRequest,
)
from roomswipe_api.services.shopify_carts import ShopifyCartService
from roomswipe_api.services.shopify_catalog import ShopifyCatalogService
from roomswipe_api.services.shopify_mcp import ShopifyMcpError

router = APIRouter(prefix="/commerce", tags=["commerce"])

CatalogService = Annotated[ShopifyCatalogService, Depends(get_shopify_catalog_service)]
CartService = Annotated[ShopifyCartService, Depends(get_shopify_cart_service)]


@router.post("/search", response_model=list[ProductOffer])
async def search_products(
    request: SearchProductsRequest,
    catalog_service: CatalogService,
) -> list[ProductOffer]:
    try:
        return await catalog_service.search_offers(
            manifest=request.manifest,
            budget_minor=request.budget_minor,
            currency=request.currency,
            country=request.country,
            region=request.region,
            postal_code=request.postal_code,
            candidates_per_slot=request.candidates_per_slot,
        )
    except ShopifyMcpError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.detail,
        ) from exc


@router.post("/carts", response_model=CreateCartsResponse)
async def create_carts(
    request: CreateCartsRequest,
    cart_service: CartService,
) -> CreateCartsResponse:
    try:
        return await cart_service.create_merchant_carts(
            offers=request.offers,
            country=request.country,
        )
    except ShopifyMcpError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.detail,
        ) from exc
