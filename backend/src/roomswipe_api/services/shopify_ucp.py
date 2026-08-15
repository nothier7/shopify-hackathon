"""Thierno's Shopify Global Catalog and merchant-cart service boundary."""

from typing import Protocol

from roomswipe_api.schemas import FinalDesignManifest, MerchantCart, ProductOffer


class ShopifyCommerceService(Protocol):
    async def search_offers(
        self,
        *,
        manifest: FinalDesignManifest,
        budget_minor: int,
        currency: str,
        country: str,
        region: str | None,
        postal_code: str | None,
        candidates_per_slot: int,
    ) -> list[ProductOffer]: ...

    async def refresh_offer(self, *, offer: ProductOffer) -> ProductOffer: ...

    async def create_merchant_carts(
        self,
        *,
        offers: list[ProductOffer],
        country: str,
    ) -> list[MerchantCart]: ...
