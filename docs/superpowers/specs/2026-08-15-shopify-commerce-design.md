# Shopify commerce integration design

## Objective

Convert Urja's structured final-room manifest into real Shopify product candidates, then create one resumable cart per merchant for the selected variants.

## Boundary with image generation

The image pipeline is the source of truth for which objects were intentionally added or replaced. It returns the final image URL and structured product slots. Each slot contains:

- stable slot ID and furniture category
- natural-language search query
- color, material, and style attributes
- `added` or `replaced` change type
- normalized bounding box when available
- hard requirements and soft preferences
- budget weight and extraction confidence

The commerce service does not rediscover the whole room. If a bounding box is present, it crops that object from the final image and uses the crop as optional visual context. Without a bounding box, search remains text-driven.

## Catalog flow

1. Validate the manifest and allocate a maximum price to each slot.
2. Fetch the final image once when at least one slot has a bounding box.
3. Crop each applicable item and encode it as an image input.
4. Call Global Catalog MCP `search_catalog` with the text query, optional image, buyer location, price ceiling, and `available: true`.
5. Normalize the response into `ProductOffer` records tied to the source slot.
6. Return several candidates per slot for Nikita's ranking layer.
7. Before cart creation, call `get_product` for the selected product or variant and reject stale or unavailable selections.

Hard requirements such as category, maximum price, destination, and availability are never relaxed silently. Soft attributes such as color, material, shape, and style may be relaxed when no result exists, and the response records that relaxation.

## Cart flow

1. Group selected offers by `merchant_domain`.
2. Refresh every selected variant before constructing the cart.
3. Call the merchant's Cart MCP endpoint at `https://{merchant-domain}/api/ucp/mcp` using `create_cart`.
4. Include the UCP agent profile, buyer localization, RoomSwipe attribution, variant IDs, and quantities.
5. Return one `MerchantCart` per merchant with the validated subtotal and `continue_url`.

RoomSwipe does not attempt unified cross-merchant checkout. Checkout MCP and payment are outside this feature.

## Components

- `ShopifyMcpClient`: JSON-RPC transport, timeouts, Shopify error normalization.
- `CatalogSearchService`: manifest-to-search requests and offer normalization.
- `ReferenceImageService`: bounded image download and normalized bounding-box cropping.
- `CartService`: merchant grouping, variant refresh, and `create_cart` calls.
- Commerce routes: HTTP adapters for candidate search and cart creation.

## Failure handling

- Invalid or missing agent profile: fail configuration at service construction.
- Shopify JSON-RPC errors: return a typed upstream error without leaking request metadata.
- Missing catalog results: return an empty candidate list for that slot.
- Invalid image or bounding box: continue with text-only search for that slot.
- Stale or unavailable variant: reject the selection instead of placing it in a cart.
- Merchant cart failure: report that merchant independently so successful merchant carts remain usable.

## Testing

- Unit-test JSON-RPC request envelopes and response parsing with `httpx.MockTransport`.
- Unit-test multimodal search payloads, text-only fallback, price filters, and seller normalization.
- Unit-test merchant grouping and cart payloads.
- Route tests verify successful responses and typed upstream failures.
- A manual live smoke test uses Shopify's public Global Catalog endpoint and a development agent profile.

## Delivery sequence

1. Manifest and commerce schemas.
2. JSON-RPC transport and Global Catalog search.
3. Cart MCP grouping and creation.
4. Route wiring, documentation, and live smoke test.
