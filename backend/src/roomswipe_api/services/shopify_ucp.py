"""Thierno's Shopify Global Catalog and merchant-cart service boundary."""

from typing import Protocol

from roomswipe_api.schemas import MerchantCart, ProductOffer, ProductSlot


class ShopifyCommerceService(Protocol):
    async def search_offers(
        self,
        *,
        slots: list[ProductSlot],
        country: str,
    ) -> list[ProductOffer]: ...

    async def refresh_offer(self, *, offer: ProductOffer) -> ProductOffer: ...

    async def create_merchant_carts(
        self,
        *,
        offers: list[ProductOffer],
    ) -> list[MerchantCart]: ...
