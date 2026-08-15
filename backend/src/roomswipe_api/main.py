from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from roomswipe_api.api.routes import commerce, health, images, recommendations
from roomswipe_api.config import get_settings

settings = get_settings()

app = FastAPI(
    title="RoomSwipe API",
    version="0.1.0",
    description="Room transformation, recommendation, and Shopify commerce contracts.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(images.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(commerce.router, prefix="/api/v1")
