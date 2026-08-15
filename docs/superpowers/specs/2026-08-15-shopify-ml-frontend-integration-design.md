# RoomSwipe Shopify, ML, and Frontend Integration

## Goal

Connect the existing RoomSwipe React experience directly to the FastAPI backend so the demo follows one real vertical workflow:

1. Generate ten room candidates from the uploaded room and questionnaire.
2. Learn from ten swipes and produce the ML-recommended final room description.
3. Generate the final room image from that description and the original room photo.
4. Turn the recommendation into Shopify catalog search slots.
5. Search live Shopify offers, rank them with the learned preference profile, and let the user choose products.
6. Create one Shopify cart per merchant and expose each checkout URL.

Base44 remains the source of the React UI skeleton and may still host the frontend. Base44 Functions, Entities, and file upload are not dependencies of the critical demo path.

## Scope

### Included

- A frontend API client for RoomSwipe FastAPI endpoints.
- Local React session state for the questionnaire, original photo, candidates, swipes, recommendation, product offers, selections, and carts.
- Working ML preference, finalization, and product-selection endpoints.
- A final-image endpoint driven by the ML recommendation.
- A deterministic adapter from recommended items to Shopify `ProductSlot` values.
- Shopify Global Catalog search and merchant-cart calls from the frontend flow.
- Visible loading, error, retry, empty, and partial-cart states.
- Backend contract tests and frontend lint/build verification.

### Not included

- Durable sessions or restoring a session after a browser refresh.
- User accounts or moving Base44 authentication into FastAPI.
- Bounding-box detection for objects in the final image.
- Checkout or payment processing inside RoomSwipe.
- Support for destinations outside the United States or budgets outside USD.
- Refactoring unrelated frontend components or backend services.

## Architecture

The browser calls FastAPI directly through a small client configured by `VITE_ROOMSWIPE_API_BASE_URL`. The default development URL is `http://127.0.0.1:8000/api/v1`. FastAPI CORS uses `ALLOWED_ORIGINS`; its development default will include the Vite origins `http://localhost:5173` and `http://127.0.0.1:5173` in addition to the existing local origin.

No new all-in-one orchestration endpoint is introduced. Keeping the stages as separate API calls makes the Shopify and ML work visible in the hackathon demo and preserves the existing ownership boundaries.

```text
Questionnaire + original File
  -> POST /images/generate-designs
  -> ten DesignCandidate objects
  -> ten local SwipeEvent objects
  -> POST /recommendations/preferences
  -> POST /recommendations/finalize
  -> PreferenceProfile + RecommendedDesign
  -> POST /images/generate-final
  -> FinalDesignManifest with final image URL and product slots
  -> POST /commerce/search
  -> candidate ProductOffer objects
  -> POST /recommendations/select-products
  -> ranked, budget-compatible ProductOffer objects
  -> user selection
  -> POST /commerce/carts
  -> merchant carts, checkout URLs, and independent failures
```

## Backend Design

### Recommendation services

Keep the existing `POST /api/v1/recommendations/finalize` request and response contract. Connect the other two existing routes without replacing the shared schemas:

- `POST /api/v1/recommendations/preferences` calls the ML preference learner with the ten candidates and swipes and returns a `PreferenceProfile`.
- `POST /api/v1/recommendations/select-products` calls the ML rank-and-optimize function with that profile, Shopify offers, and the total budget. It returns the selected offers with their ML match scores.

The implementation may reuse the adapter logic on `origin/ML`, but it must be applied selectively. That branch must not overwrite the current recommendation finalization contract, US/USD commerce validation, or newer backend tests.

### Final-image endpoint

Add `POST /api/v1/images/generate-final` as a multipart endpoint with:

- `image`: the original JPEG, PNG, or WebP room photo.
- `recommended_design`: JSON matching `RecommendedDesign`.

The image service edits the original room using the recommendation name, description, item descriptions, and budget. The response is a `FinalDesignManifest`:

- `finalImageUrl` is the generated image URL or data URL.
- One `ProductSlot` is created for each recommended item.
- Slot IDs are stable within the result: `item-1`, `item-2`, and so on.
- `category` is the recommended item name.
- `searchQuery` is the recommended item description.
- `mustMatch` contains the category name.
- `budgetWeight` is `max(1, maxPriceMinor)`; Shopify's commerce service normalizes these relative weights when allocating the total budget.
- `confidence` is `matchPercent / 100`.
- Optional colors, materials, styles, shapes, and bounding boxes remain empty when the ML result does not provide them.
- `changeType` is `added` for the MVP.

Manifest creation is a pure adapter with unit tests. Image generation and manifest construction remain separable so a later richer manifest from Urja can replace the adapter without changing commerce routes.

### Commerce services

Keep the existing commerce contracts:

- `POST /api/v1/commerce/search` receives the final manifest, USD budget in minor units, US destination, and desired candidates per slot.
- `POST /api/v1/commerce/carts` receives only the offers selected by the user and returns one cart per merchant plus independent failures.

The previously developed catalog fallback, US-delivery filtering, over-fetching, and duplicate-description protection will be recovered from the local stash only after comparing it with the current branch. It will be committed separately from the frontend integration.

## Frontend Design

### API boundary

Add one focused module under `frontend/src/api/` that:

- Resolves the API base URL.
- Sends JSON and multipart requests.
- Parses FastAPI error details into one `RoomSwipeApiError` shape.
- Converts frontend questionnaire values into backend camel-case contracts.
- Does not contain React state or presentation logic.

Questionnaire conversion is deterministic:

- The displayed dollar budget becomes `budgetMinor` by multiplying by 100.
- Currency is `USD`.
- Room labels become lowercase backend room types.
- The chosen age range becomes its integer midpoint; `65+` becomes `68`.
- The selected goal becomes a one-element `goals` array.
- The selected style becomes a one-element `optionalStyles` array unless it is `No preference`.
- `effort` is `buy_only` because the current questionnaire does not collect effort.
- `designDensity` is `maximalist` only for the Maximalist selection and `minimalist` otherwise.

### Session state

Refactor `SessionContext` to store browser-session data without Base44 entity writes:

- `questionnaire`
- `photoFile` and `photoPreviewUrl`
- `designs`
- `swipes`
- `preferenceProfile`
- `recommendedDesign`
- `manifest`
- `offers` and `selectedOffers`
- `merchantCarts` and `cartFailures`

Resetting the app clears this state and revokes any created object URL. Refreshing the page intentionally resets the current demo session.

### Page behavior

- `Upload` validates and previews the file, calls `generate-designs`, and stores the returned candidates. It does not upload to Base44.
- `Swipe` displays the returned candidate images immediately and records one swipe per candidate. It no longer generates images or updates Base44 records.
- `FinalLook` calls preference learning and finalization concurrently after all swipes exist. It then calls `generate-final`, displays the generated final image and ML description, and stores the manifest.
- `Products` searches Shopify once per manifest, sends all viable offers through ML selection, groups results by slot, and renders the selected recommendations using Shopify offer fields.
- The user can add or remove one offer per slot before opening the cart.
- The cart action calls `commerce/carts`. Successful merchants show checkout links; failures remain visible without hiding successful carts.

Base44 `computeFinalLook`, `matchProducts`, `generateRoomDesigns`, `generateRoomImage`, entity persistence, and file upload are removed from these pages and the session provider. Unused Base44 function source files may remain temporarily because they do not affect the runtime path; deleting them is not required for this integration.

## Error Handling

- Each network stage exposes an inline error and a retry action local to that stage.
- A failed request never silently falls back to a Base44 function or fake catalog data.
- Invalid image types are rejected before the request and still validated by FastAPI.
- A failure to generate the final image leaves the ML recommendation visible and retryable.
- Slots with no Shopify offers show an explicit no-match state while other slots remain usable.
- Merchant-cart failures are independent; successful checkout URLs are preserved.
- Buttons that cause network mutations are disabled while their request is in flight to prevent duplicate calls.

## Verification

Backend tests cover:

- Questionnaire and multipart validation.
- ML preference and product-selection route adapters.
- Final-image prompt inputs and `RecommendedDesign` to `FinalDesignManifest` conversion.
- Search requests using the generated manifest.
- Multiple merchant carts and partial merchant failures.
- Existing commerce, ML, and image-generation regressions.

Frontend verification covers:

- ESLint and a production Vite build.
- Questionnaire contract conversion for budget, age, density, and optional styles.
- A manual local browser run through upload, ten swipes, final generation, Shopify results, selection, and cart creation.
- Network inspection confirming that no Base44 Function or Entity call occurs in the critical flow.

## Commit Strategy

Keep changes reviewable and reduce merge conflicts with these commits:

1. Connect the existing ML preference and product-selection routes.
2. Add final-image generation and manifest conversion.
3. Add the frontend API client and local session state.
4. Migrate upload, swipe, and final-look pages.
5. Migrate Shopify products and merchant carts.
6. Restore catalog fallback and deduplication behavior if it remains compatible.

Before pushing, pull the latest remote changes, reconcile `origin/master`, run the complete checks, and push only this feature branch.
