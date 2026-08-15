"""Turn final-room product slots into live Shopify catalog offers."""

import asyncio
from collections.abc import Mapping
from typing import Any

from roomswipe_api.schemas import FinalDesignManifest, ProductOffer, ProductSlot
from roomswipe_api.services.reference_images import (
    EncodedImage,
    ReferenceImageError,
    ReferenceImageService,
)
from roomswipe_api.services.shopify_mcp import ShopifyMcpClient


class ProductOfferUnavailable(RuntimeError):
    pass


class ShopifyCatalogService:
    def __init__(
        self,
        *,
        mcp_client: ShopifyMcpClient,
        image_service: ReferenceImageService,
        catalog_endpoint: str,
    ) -> None:
        self.mcp_client = mcp_client
        self.image_service = image_service
        self.catalog_endpoint = catalog_endpoint

    async def search_offers(
        self,
        *,
        manifest: FinalDesignManifest,
        budget_minor: int,
        currency: str,
        country: str,
        region: str | None = None,
        postal_code: str | None = None,
        candidates_per_slot: int = 3,
    ) -> list[ProductOffer]:
        image_bytes = await self._optional_final_image(manifest)
        price_limits = self._allocate_budget(manifest.product_slots, budget_minor)

        searches = [
            self._search_slot(
                slot=slot,
                max_price_minor=price_limits[slot.id],
                image_bytes=image_bytes,
                currency=currency,
                country=country,
                region=region,
                postal_code=postal_code,
                limit=candidates_per_slot,
            )
            for slot in manifest.product_slots
        ]
        results = await asyncio.gather(*searches)
        return [offer for slot_offers in results for offer in slot_offers]

    async def refresh_offer(self, *, offer: ProductOffer, country: str) -> ProductOffer:
        content = await self.mcp_client.call_tool(
            endpoint=self.catalog_endpoint,
            name="get_product",
            arguments={
                "catalog": {
                    "id": offer.product_id,
                    "filters": {
                        "available": True,
                        "ships_to": {"country": country},
                    },
                    "context": {
                        "address_country": country,
                        "currency": offer.currency,
                    },
                    "view": "summary",
                }
            },
        )
        product = content.get("product")
        if not isinstance(product, Mapping):
            raise ProductOfferUnavailable("selected product is no longer available")
        variants = product.get("variants")
        if not isinstance(variants, list):
            raise ProductOfferUnavailable("selected product has no purchasable variants")

        for variant in variants:
            if isinstance(variant, Mapping) and variant.get("id") == offer.variant_id:
                return self._refresh_from_variant(offer, product, variant)
        raise ProductOfferUnavailable("selected variant is no longer available")

    async def _optional_final_image(self, manifest: FinalDesignManifest) -> bytes | None:
        if not any(slot.bounding_box for slot in manifest.product_slots):
            return None
        try:
            return await self.image_service.download(manifest.final_image_url)
        except ReferenceImageError:
            return None

    async def _search_slot(
        self,
        *,
        slot: ProductSlot,
        max_price_minor: int,
        image_bytes: bytes | None,
        currency: str,
        country: str,
        region: str | None,
        postal_code: str | None,
        limit: int,
    ) -> list[ProductOffer]:
        image = self._optional_crop(slot, image_bytes)
        detailed_query = self._query_for(slot, include_soft_preferences=True)
        content = await self._search_catalog(
            query=detailed_query,
            image=image,
            max_price_minor=max_price_minor,
            currency=currency,
            country=country,
            region=region,
            postal_code=postal_code,
            limit=limit,
        )
        products = content.get("products")
        relaxed_preferences: list[str] = []

        if not isinstance(products, list) or not products:
            relaxed_preferences = self._soft_preference_names(slot)
            if relaxed_preferences:
                content = await self._search_catalog(
                    query=self._query_for(slot, include_soft_preferences=False),
                    image=image,
                    max_price_minor=max_price_minor,
                    currency=currency,
                    country=country,
                    region=region,
                    postal_code=postal_code,
                    limit=limit,
                )
                products = content.get("products")

        if not isinstance(products, list):
            return []

        offers: list[ProductOffer] = []
        for product in products:
            if not isinstance(product, Mapping):
                continue
            offer = self._normalize_product(
                product,
                slot_id=slot.id,
                max_price_minor=max_price_minor,
                relaxed_preferences=relaxed_preferences,
            )
            if offer is not None:
                offers.append(offer)
            if len(offers) == limit:
                break
        return offers

    async def _search_catalog(
        self,
        *,
        query: str,
        image: EncodedImage | None,
        max_price_minor: int,
        currency: str,
        country: str,
        region: str | None,
        postal_code: str | None,
        limit: int,
    ) -> dict[str, Any]:
        destination: dict[str, str] = {"country": country}
        context: dict[str, str] = {
            "address_country": country,
            "currency": currency,
            "intent": "Find purchasable furniture matching an AI-designed room",
        }
        if region:
            destination["region"] = region
            context["address_region"] = region
        if postal_code:
            destination["postal_code"] = postal_code
            context["postal_code"] = postal_code

        catalog: dict[str, Any] = {
            "query": query,
            "filters": {
                "available": True,
                "ships_to": destination,
                "price": {"max": max_price_minor},
            },
            "context": context,
            "pagination": {"limit": limit},
            "view": "offer",
        }
        if image is not None:
            catalog["like"] = [
                {"image": {"content_type": image.content_type, "data": image.data}}
            ]

        return await self.mcp_client.call_tool(
            endpoint=self.catalog_endpoint,
            name="search_catalog",
            arguments={"catalog": catalog},
        )

    def _optional_crop(self, slot: ProductSlot, image_bytes: bytes | None) -> EncodedImage | None:
        if image_bytes is None or slot.bounding_box is None:
            return None
        try:
            return self.image_service.crop(image_bytes, slot.bounding_box)
        except ReferenceImageError:
            return None

    @staticmethod
    def _allocate_budget(slots: list[ProductSlot], budget_minor: int) -> dict[str, int]:
        total_weight = sum(slot.budget_weight for slot in slots)
        return {
            slot.id: max(1, round(budget_minor * slot.budget_weight / total_weight))
            for slot in slots
        }

    @classmethod
    def _query_for(cls, slot: ProductSlot, *, include_soft_preferences: bool) -> str:
        parts = [slot.search_query, f"Category: {slot.category}"]
        if slot.must_match:
            parts.append(f"Required: {', '.join(slot.must_match)}")
        if include_soft_preferences:
            if slot.colors:
                parts.append(f"Colors: {', '.join(slot.colors)}")
            if slot.materials:
                parts.append(f"Materials: {', '.join(slot.materials)}")
            if slot.styles:
                parts.append(f"Styles: {', '.join(slot.styles)}")
            if slot.shape:
                parts.append(f"Shape: {slot.shape}")
        return ". ".join(parts)

    @staticmethod
    def _soft_preference_names(slot: ProductSlot) -> list[str]:
        return [
            name
            for name, value in (
                ("colors", slot.colors),
                ("materials", slot.materials),
                ("styles", slot.styles),
                ("shape", slot.shape),
            )
            if value
        ]

    @classmethod
    def _normalize_product(
        cls,
        product: Mapping[str, Any],
        *,
        slot_id: str,
        max_price_minor: int,
        relaxed_preferences: list[str],
    ) -> ProductOffer | None:
        product_id = product.get("id")
        title = product.get("title")
        variants = product.get("variants")
        if not isinstance(product_id, str) or not isinstance(title, str):
            return None
        if not isinstance(variants, list):
            return None

        eligible: list[tuple[int, Mapping[str, Any]]] = []
        for variant in variants:
            if not isinstance(variant, Mapping):
                continue
            price = variant.get("price")
            availability = variant.get("availability")
            if not isinstance(price, Mapping) or not isinstance(availability, Mapping):
                continue
            amount = price.get("amount")
            if (
                isinstance(amount, int)
                and not isinstance(amount, bool)
                and amount <= max_price_minor
                and availability.get("available") is True
            ):
                eligible.append((amount, variant))

        if not eligible:
            return None
        price_minor, variant = min(eligible, key=lambda candidate: candidate[0])
        price = variant["price"]
        seller = variant.get("seller")
        variant_id = variant.get("id")
        checkout_url = variant.get("checkout_url")
        currency = price.get("currency") if isinstance(price, Mapping) else None
        if not isinstance(seller, Mapping):
            return None
        merchant_domain = seller.get("domain")
        merchant_name = seller.get("name")
        if not all(
            isinstance(value, str)
            for value in (variant_id, checkout_url, currency, merchant_domain, merchant_name)
        ):
            return None

        return ProductOffer(
            product_id=product_id,
            variant_id=variant_id,
            slot_id=slot_id,
            title=title,
            merchant_name=merchant_name,
            merchant_domain=merchant_domain,
            price_minor=price_minor,
            currency=currency,
            image_url=cls._image_url(variant) or cls._image_url(product),
            checkout_url=checkout_url,
            available=True,
            relaxed_preferences=relaxed_preferences,
        )

    @staticmethod
    def _image_url(item: Mapping[str, Any]) -> str | None:
        media = item.get("media")
        if not isinstance(media, list):
            return None
        for entry in media:
            if isinstance(entry, Mapping) and entry.get("type") == "image":
                url = entry.get("url")
                if isinstance(url, str):
                    return url
        return None

    @classmethod
    def _refresh_from_variant(
        cls,
        offer: ProductOffer,
        product: Mapping[str, Any],
        variant: Mapping[str, Any],
    ) -> ProductOffer:
        availability = variant.get("availability")
        price = variant.get("price")
        seller = variant.get("seller")
        if not isinstance(availability, Mapping) or availability.get("available") is not True:
            raise ProductOfferUnavailable("selected variant is no longer available")
        if not isinstance(price, Mapping) or not isinstance(seller, Mapping):
            raise ProductOfferUnavailable("selected variant details are incomplete")

        amount = price.get("amount")
        currency = price.get("currency")
        merchant_name = seller.get("name")
        merchant_domain = seller.get("domain")
        checkout_url = variant.get("checkout_url")
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ProductOfferUnavailable("selected variant price is invalid")
        if not all(
            isinstance(value, str)
            for value in (currency, merchant_name, merchant_domain, checkout_url)
        ):
            raise ProductOfferUnavailable("selected variant details are incomplete")

        return offer.model_copy(
            update={
                "title": product.get("title", offer.title),
                "merchant_name": merchant_name,
                "merchant_domain": merchant_domain,
                "price_minor": amount,
                "currency": currency,
                "image_url": cls._image_url(variant)
                or cls._image_url(product)
                or offer.image_url,
                "checkout_url": checkout_url,
                "available": True,
            }
        )
