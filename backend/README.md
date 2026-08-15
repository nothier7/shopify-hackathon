# RoomSwipe backend

This directory is a deliberately small FastAPI skeleton for parallel hackathon development. It is one deployable backend with isolated service boundaries, not a set of microservices.

## Structure

```text
src/roomswipe_api/
├── api/routes/             HTTP contracts grouped by owner
├── services/               Replaceable service interfaces
├── config.py               Environment configuration
├── main.py                 FastAPI application
└── schemas.py              Shared request and response models
```

## Ownership boundaries

- **Urja:** `api/routes/images.py` and `services/image_generation.py`
- **Nikita:** `api/routes/recommendations.py` and `services/recommendation.py`
- **Thierno:** `api/routes/commerce.py`, `services/shopify_ucp.py`, and cross-service integration

The image-generation and recommendation routes remain service contracts until their owners connect implementations. The commerce routes call Shopify Global Catalog MCP and merchant Cart MCP directly.

## Setup

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn roomswipe_api.main:app --reload
```

## Checks

```bash
pytest
ruff check .
```

## API surface

- `GET /health`
- `POST /api/v1/images/analyze-room`
- `POST /api/v1/images/generate-designs`
- `POST /api/v1/recommendations/preferences`
- `POST /api/v1/recommendations/select-products`
- `POST /api/v1/commerce/search`
- `POST /api/v1/commerce/carts`

`commerce/search` accepts Urja's final-image product manifest and returns live offers grouped by `slotId`. Send Nikita's selected offers to `commerce/carts`; the response contains one cart and `continueUrl` per merchant, plus independent merchant failures.
