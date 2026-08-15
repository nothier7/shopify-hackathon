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

MIN_UPSTREAM_CANDIDATES = 5


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
        upstream_limit = max(MIN_UPSTREAM_CANDIDATES, limit)
        offers: list[ProductOffer] = []
        seen_variants: set[tuple[str, str]] = set()
        seen_descriptions: set[str] = set()

        for query, relaxed_preferences in self._query_stages(slot):
            content = await self._search_catalog(
                query=query,
                image=image,
                max_price_minor=max_price_minor,
                currency=currency,
                country=country,
                region=region,
                postal_code=postal_code,
                limit=upstream_limit,
            )
            products = content.get("products")
            if not isinstance(products, list):
                continue

            stage_offers = self._normalize_products(
                products,
                slot_id=slot.id,
                max_price_minor=max_price_minor,
                requested_currency=currency,
                relaxed_preferences=relaxed_preferences,
            )
            for offer in stage_offers:
                identity = (offer.product_id, offer.variant_id)
                description_key = self._description_key(offer)
                if identity in seen_variants or description_key in seen_descriptions:
                    continue
                seen_variants.add(identity)
                seen_descriptions.add(description_key)
                offers.append(offer)

            requested_currency_count = sum(
                offer.currency.upper() == currency.upper() for offer in offers
            )
            if requested_currency_count >= limit:
                break

        offers.sort(key=lambda offer: offer.currency.upper() != currency.upper())
        return offers[:limit]

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

    @classmethod
    def _query_stages(cls, slot: ProductSlot) -> list[tuple[str, list[str]]]:
        soft_preferences = cls._soft_preference_names(slot)
        candidates = [
            (cls._query_for(slot, include_soft_preferences=True), []),
            (
                cls._query_for(slot, include_soft_preferences=False),
                soft_preferences,
            ),
            (
                cls._broad_query_for(slot),
                [*soft_preferences, "descriptive wording"],
            ),
        ]

        stages: list[tuple[str, list[str]]] = []
        seen_queries: set[str] = set()
        for query, relaxed_preferences in candidates:
            if query in seen_queries:
                continue
            seen_queries.add(query)
            stages.append((query, relaxed_preferences))
        return stages

    @staticmethod
    def _broad_query_for(slot: ProductSlot) -> str:
        parts = [slot.category]
        if slot.must_match:
            parts.append(f"Required: {', '.join(slot.must_match)}")
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
        requested_currency: str,
        relaxed_preferences: list[str],
    ) -> ProductOffer | None:
        product_id = product.get("id")
        title = product.get("title")
        variants = product.get("variants")
        if not isinstance(product_id, str) or not isinstance(title, str):
            return None
        if not isinstance(variants, list):
            return None

        eligible: list[tuple[bool, int, int, Mapping[str, Any]]] = []
        for index, variant in enumerate(variants):
            if not isinstance(variant, Mapping):
                continue
            price = variant.get("price")
            availability = variant.get("availability")
            if not isinstance(price, Mapping) or not isinstance(availability, Mapping):
                continue
            amount = price.get("amount")
            variant_currency = price.get("currency")
            if (
                isinstance(amount, int)
                and not isinstance(amount, bool)
                and isinstance(variant_currency, str)
                and availability.get("available") is True
            ):
                currency_matches = variant_currency.upper() == requested_currency.upper()
                if currency_matches and amount > max_price_minor:
                    continue
                eligible.append((not currency_matches, amount, index, variant))

        if not eligible:
            return None
        _, price_minor, _, variant = min(
            eligible,
            key=lambda candidate: (
                candidate[0],
                candidate[1] if not candidate[0] else candidate[2],
            ),
        )
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
            description=(
                product.get("description")
                if isinstance(product.get("description"), str)
                else ""
            ),
            merchant_name=merchant_name,
            merchant_domain=merchant_domain,
            price_minor=price_minor,
            currency=currency,
            image_url=cls._image_url(variant) or cls._image_url(product),
            checkout_url=checkout_url,
            available=True,
            relaxed_preferences=relaxed_preferences,
        )

    @classmethod
    def _normalize_products(
        cls,
        products: list[Any],
        *,
        slot_id: str,
        max_price_minor: int,
        requested_currency: str,
        relaxed_preferences: list[str],
    ) -> list[ProductOffer]:
        offers: list[ProductOffer] = []
        for product in products:
            if not isinstance(product, Mapping):
                continue
            offer = cls._normalize_product(
                product,
                slot_id=slot_id,
                max_price_minor=max_price_minor,
                requested_currency=requested_currency,
                relaxed_preferences=relaxed_preferences,
            )
            if offer is not None:
                offers.append(offer)

        offers.sort(
            key=lambda offer: offer.currency.upper() != requested_currency.upper()
        )
        return offers

    @staticmethod
    def _description_key(offer: ProductOffer) -> str:
        value = offer.description or offer.title
        return " ".join(value.casefold().split())

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
                "description": (
                    product.get("description")
                    if isinstance(product.get("description"), str)
                    else offer.description
                ),
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
