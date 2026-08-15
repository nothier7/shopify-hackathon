"""Refresh selected variants and create one Shopify cart per merchant."""

import asyncio
from collections import defaultdict
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

import httpx

from roomswipe_api.schemas import (
    CreateCartsResponse,
    MerchantCart,
    MerchantCartFailure,
    ProductOffer,
)
from roomswipe_api.services.shopify_catalog import (
    ProductOfferUnavailable,
    ShopifyCatalogService,
)
from roomswipe_api.services.shopify_mcp import ShopifyMcpClient, ShopifyMcpError


class CartCreationError(RuntimeError):
    pass


class MerchantEndpointResolver:
    def __init__(
        self,
        *,
        timeout_seconds: float = 10,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = http_client is None

    async def resolve(self, checkout_url: str) -> str:
        checkout = urlsplit(checkout_url)
        if checkout.scheme != "https" or not checkout.netloc:
            raise CartCreationError("merchant checkout URL is invalid")
        origin = f"https://{checkout.netloc}"
        fallback = f"{origin}/api/ucp/mcp"

        try:
            response = await self._client.get(f"{origin}/.well-known/ucp")
            response.raise_for_status()
            profile = response.json()
        except (httpx.HTTPError, ValueError):
            return fallback

        endpoint = self._mcp_endpoint(profile)
        return endpoint or fallback

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _mcp_endpoint(profile: Any) -> str | None:
        if not isinstance(profile, Mapping):
            return None
        ucp = profile.get("ucp")
        services = ucp.get("services") if isinstance(ucp, Mapping) else None
        shopping = services.get("dev.ucp.shopping") if isinstance(services, Mapping) else None
        if not isinstance(shopping, list):
            return None

        for service in shopping:
            if not isinstance(service, Mapping) or service.get("transport") != "mcp":
                continue
            endpoint = service.get("endpoint")
            if isinstance(endpoint, str):
                parsed = urlsplit(endpoint)
                if parsed.scheme == "https" and parsed.netloc:
                    return endpoint
        return None


class ShopifyCartService:
    def __init__(
        self,
        *,
        catalog_service: ShopifyCatalogService,
        mcp_client: ShopifyMcpClient,
        endpoint_resolver: MerchantEndpointResolver,
    ) -> None:
        self.catalog_service = catalog_service
        self.mcp_client = mcp_client
        self.endpoint_resolver = endpoint_resolver

    async def create_merchant_carts(
        self,
        *,
        offers: list[ProductOffer],
        country: str,
    ) -> CreateCartsResponse:
        refreshed, failures = await self._refresh_offers(offers, country)
        groups: dict[str, list[ProductOffer]] = defaultdict(list)
        for offer in refreshed:
            groups[offer.merchant_domain].append(offer)

        merchant_groups = list(groups.items())
        outcomes = await asyncio.gather(
            *(
                self._create_merchant_cart(
                    merchant_domain=merchant_domain,
                    offers=merchant_offers,
                    country=country,
                )
                for merchant_domain, merchant_offers in merchant_groups
            ),
            return_exceptions=True,
        )

        carts: list[MerchantCart] = []
        for (merchant_domain, merchant_offers), outcome in zip(
            merchant_groups, outcomes, strict=True
        ):
            if isinstance(outcome, BaseException):
                failures.append(
                    MerchantCartFailure(
                        merchant_domain=merchant_domain,
                        slot_ids=[offer.slot_id for offer in merchant_offers],
                        detail=self._safe_error_detail(outcome),
                    )
                )
            else:
                carts.append(outcome)
        return CreateCartsResponse(carts=carts, failures=failures)

    async def _refresh_offers(
        self,
        offers: list[ProductOffer],
        country: str,
    ) -> tuple[list[ProductOffer], list[MerchantCartFailure]]:
        outcomes = await asyncio.gather(
            *(
                self.catalog_service.refresh_offer(offer=offer, country=country)
                for offer in offers
            ),
            return_exceptions=True,
        )
        refreshed: list[ProductOffer] = []
        failures: list[MerchantCartFailure] = []
        for original, outcome in zip(offers, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                failures.append(
                    MerchantCartFailure(
                        merchant_domain=original.merchant_domain,
                        slot_ids=[original.slot_id],
                        detail=self._safe_error_detail(outcome),
                    )
                )
            else:
                refreshed.append(outcome)
        return refreshed, failures

    async def _create_merchant_cart(
        self,
        *,
        merchant_domain: str,
        offers: list[ProductOffer],
        country: str,
    ) -> MerchantCart:
        endpoint = await self.endpoint_resolver.resolve(offers[0].checkout_url)
        content = await self.mcp_client.call_tool(
            endpoint=endpoint,
            name="create_cart",
            arguments={
                "cart": {
                    "line_items": [
                        {"quantity": 1, "item": {"id": offer.variant_id}} for offer in offers
                    ],
                    "context": {"address_country": country},
                    "attribution": {
                        "utm_source": "roomswipe",
                        "utm_medium": "agent",
                        "utm_campaign": "shop_the_room",
                    },
                }
            },
        )
        cart = content.get("cart")
        if not isinstance(cart, Mapping):
            raise CartCreationError("merchant returned an invalid cart")

        cart_id = cart.get("id")
        continue_url = cart.get("continue_url")
        currency = cart.get("currency")
        if not all(isinstance(value, str) for value in (cart_id, continue_url, currency)):
            raise CartCreationError("merchant returned incomplete cart details")

        requested_variants = [offer.variant_id for offer in offers]
        returned_variants = self._returned_variant_ids(cart)
        if not set(requested_variants).issubset(returned_variants):
            raise CartCreationError("merchant rejected one or more selected items")

        return MerchantCart(
            cart_id=cart_id,
            merchant_name=offers[0].merchant_name,
            merchant_domain=merchant_domain,
            slot_ids=[offer.slot_id for offer in offers],
            variant_ids=requested_variants,
            subtotal_minor=self._subtotal(cart, offers),
            currency=currency,
            continue_url=continue_url,
        )

    @staticmethod
    def _returned_variant_ids(cart: Mapping[str, Any]) -> set[str]:
        line_items = cart.get("line_items")
        if not isinstance(line_items, list):
            return set()
        variant_ids: set[str] = set()
        for line_item in line_items:
            if not isinstance(line_item, Mapping):
                continue
            item = line_item.get("item")
            variant_id = item.get("id") if isinstance(item, Mapping) else None
            if isinstance(variant_id, str):
                variant_ids.add(variant_id)
        return variant_ids

    @staticmethod
    def _subtotal(cart: Mapping[str, Any], offers: list[ProductOffer]) -> int:
        totals = cart.get("totals")
        if isinstance(totals, list):
            for total in totals:
                if not isinstance(total, Mapping) or total.get("type") != "subtotal":
                    continue
                amount = total.get("amount")
                if isinstance(amount, int) and not isinstance(amount, bool):
                    return amount
        return sum(offer.price_minor for offer in offers)

    @staticmethod
    def _safe_error_detail(error: BaseException) -> str:
        if isinstance(error, (CartCreationError, ProductOfferUnavailable, ShopifyMcpError)):
            return str(error)
        return "merchant cart could not be created"
