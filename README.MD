# RoomSwipe — Shopify Hackathon

RoomSwipe turns a photo of a room and a few constraints into a personalized room concept, then connects its major elements to visually matching products from Shopify merchants.

## Workstreams

| Owner | Area | Primary backend module |
| --- | --- | --- |
| Anastasia | Frontend and user experience | Separate frontend workstream |
| Nikita | Preference learning and product ranking | `backend/src/roomswipe_api/services/recommendation.py` |
| Thierno | Shopify MCP/UCP and backend integration | `backend/src/roomswipe_api/services/shopify_ucp.py` |
| Urja | Room analysis and image generation | `backend/src/roomswipe_api/services/image_generation.py` |

The initial backend skeleton lives in [`backend/`](backend/README.md). It exposes a health endpoint and OpenAPI contracts for the three independently owned service boundaries.

## Backend quick start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn roomswipe_api.main:app --reload
```

Open `http://localhost:8000/docs` for the API contract and `http://localhost:8000/health` for the health check.
