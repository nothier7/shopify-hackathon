# Roomly — Shopify Hackathon

Roomly turns a photo of a room and a few constraints into a personalized room concept, then connects its major elements to visually matching products from Shopify merchants.

Sample Input Room:

![input room example](https://github.com/nothier7/shopify-hackathon/blob/master/images/empty_room.jpg?raw=true)


Sample Output Room:

![output room example](https://github.com/nothier7/shopify-hackathon/blob/master/images/post_roomly.png?raw=true)


## Workstreams

| Owner | Area | Primary backend module |
| --- | --- | --- |
| Anastasia | Frontend and user experience | Separate frontend workstream |
| Nikita | Preference learning and product ranking | `backend/src/Roomly_api/services/recommendation.py` |
| Thierno | Shopify MCP/UCP and backend integration | `backend/src/Roomly_api/services/shopify_ucp.py` |
| Urja | Room analysis and image generation | `backend/src/Roomly_api/services/image_generation.py` |

The initial backend skeleton lives in [`backend/`](backend/README.md). It exposes a health endpoint and OpenAPI contracts for the three independently owned service boundaries.

## Backend quick start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn Roomly_api.main:app --reload
```

Open `http://localhost:8000/docs` for the API contract and `http://localhost:8000/health` for the health check.

## Full-stack local run

The browser flow now calls the shared FastAPI contracts directly:

`questionnaire + photo -> 10 designs -> swipes/comments -> ML recommendation -> final room manifest -> Shopify products -> merchant carts`

### 1. Start FastAPI

PowerShell:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
# Set OPENAI_API_KEY in backend/.env.
python -m uvicorn Roomly_api.main:app --reload --port 8000
```

macOS/Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
# Set OPENAI_API_KEY in backend/.env.
python -m uvicorn Roomly_api.main:app --reload --port 8000
```

### 2. Start the frontend

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. Vite proxies `/api/v1` and `/health` to FastAPI on port 8000, so Base44 login is not required for the local core flow.

If port 8000 is unavailable, run FastAPI on another port and set the proxy target before starting Vite. PowerShell example:

```powershell
$env:Roomly_BACKEND_URL="http://127.0.0.1:8088"
npm run dev
```

### 3. Verify the integration

```bash
curl http://localhost:8000/health
python -m pytest backend/tests ML/tests
python -m ML model_input.example.json
cd frontend
npm run lint
npm run build
```

Then complete the UI flow and confirm these requests in the browser Network panel:

1. Upload: `POST /api/v1/images/generate-designs` returns 10 candidates.
2. After the tenth swipe: `POST /api/v1/recommendations/finalize` returns one `recommendedDesign`.
3. Final Look: `POST /api/v1/images/generate-final-design` returns `finalImageUrl` and `productSlots`.
4. Build This Room: `POST /api/v1/commerce/search` returns Shopify offers.
5. Create Cart: `POST /api/v1/commerce/carts` returns one cart/continue URL per merchant.

Image endpoints require `OPENAI_API_KEY`. Shopify search/cart calls require network access to the configured MCP/UCP endpoints. For a separately hosted frontend, set `VITE_Roomly_API_URL=https://your-api.example.com/api/v1` and add the frontend origin to backend `ALLOWED_ORIGINS`.

## ML payload

The final recommendation model accepts exactly 10 design dictionaries. Each dictionary contains the shared questionnaire, design metadata, `like: "Yes" | "No"`, and an optional `comment`. It returns one recommended design with budget-capped product descriptions for Shopify search.

```bash
python -m ML model_input.example.json
```

See `model_input.example.json` and `model_output.example.json` for the complete contract.
