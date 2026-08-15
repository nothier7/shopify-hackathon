"""Construct shared Shopify services for FastAPI dependency injection."""

from dataclasses import dataclass
from functools import lru_cache

from roomswipe_api.config import get_settings
from roomswipe_api.services.recommendation import LocalRecommendationService
from roomswipe_api.services.reference_images import ReferenceImageService
from roomswipe_api.services.shopify_carts import MerchantEndpointResolver, ShopifyCartService
from roomswipe_api.services.shopify_catalog import ShopifyCatalogService
from roomswipe_api.services.shopify_mcp import ShopifyMcpClient


@dataclass(frozen=True, slots=True)
class ShopifyServices:
    catalog: ShopifyCatalogService
    carts: ShopifyCartService


@lru_cache
def get_recommendation_service() -> LocalRecommendationService:
    return LocalRecommendationService()


@lru_cache
def get_shopify_services() -> ShopifyServices:
    settings = get_settings()
    mcp_client = ShopifyMcpClient(
        agent_profile_url=settings.shopify_agent_profile_url,
        timeout_seconds=settings.shopify_request_timeout_seconds,
    )
    image_service = ReferenceImageService(
        max_bytes=settings.shopify_reference_image_max_bytes,
        timeout_seconds=settings.shopify_request_timeout_seconds,
    )
    catalog = ShopifyCatalogService(
        mcp_client=mcp_client,
        image_service=image_service,
        catalog_endpoint=settings.shopify_global_catalog_mcp_url,
    )
    carts = ShopifyCartService(
        catalog_service=catalog,
        mcp_client=mcp_client,
        endpoint_resolver=MerchantEndpointResolver(
            timeout_seconds=settings.shopify_request_timeout_seconds
        ),
    )
    return ShopifyServices(catalog=catalog, carts=carts)


def get_shopify_catalog_service() -> ShopifyCatalogService:
    return get_shopify_services().catalog


def get_shopify_cart_service() -> ShopifyCartService:
    return get_shopify_services().carts
