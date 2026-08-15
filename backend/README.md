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

The feature routes intentionally return HTTP `501` until their owner connects an implementation. This keeps the OpenAPI contract usable without shipping fake behavior.

## Setup

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn roomswipe_api.main:app --reload
```

### Configure and test image generation

Copy `.env.example` to `.env` and set `OPENAI_API_KEY` to an API key. Do not commit `.env`: it is a local secrets file. Open `http://127.0.0.1:8000/docs` and use **POST `/api/v1/images/generate-designs`**. Send the empty-room photo in the `image` form field, its questionnaire JSON (including one `userAge`) in the `questionnaire` form field, and set `count` to `10`. Each result is an edit of that uploaded room, including a browser-displayable image URL, style name, warmth, lighting, included items, numeric attributes, and the complete questionnaire used to create it.

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
