from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from roomswipe_api.schemas import DesignCandidate, GenerateDesignsRequest, RoomAnalysis

router = APIRouter(prefix="/images", tags=["images — Urja"])


@router.post("/analyze-room", response_model=RoomAnalysis)
async def analyze_room(image: Annotated[UploadFile, File(...)]) -> RoomAnalysis:
    del image
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Room analysis service is not connected yet.",
    )


@router.post("/generate-designs", response_model=list[DesignCandidate])
async def generate_designs(request: GenerateDesignsRequest) -> list[DesignCandidate]:
    del request
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Image generation service is not connected yet.",
    )
