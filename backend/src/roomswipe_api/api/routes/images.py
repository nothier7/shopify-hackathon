from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from roomswipe_api.schemas import (
    DesignCandidate,
    FinalDesignManifest,
    Questionnaire,
    RecommendedDesign,
    RoomAnalysis,
)
from roomswipe_api.services.image_generation import (
    ImageGenerationError,
    ImageGenerationNotConfiguredError,
    OpenAIImageGenerationService,
)

router = APIRouter(prefix="/images", tags=["images — Urja"])


# full endpoint: /api/v1/images/analyze-room
# receives the uploaded photo, and raise errors if cannot read
@router.post("/analyze-room", response_model=RoomAnalysis)
async def analyze_room(image: Annotated[UploadFile, File(...)]) -> RoomAnalysis:
    # check img format
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG, or WebP image.",
        )
    try:
        return await OpenAIImageGenerationService().analyze_room(
            # read image
            image=await image.read(),
            content_type=image.content_type,
        )
    except ImageGenerationNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ImageGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


# full endpoint: /api/v1/images/generate-designs
@router.post("/generate-designs", response_model=list[DesignCandidate])
async def generate_designs(
    image: Annotated[UploadFile, File(...)],
    questionnaire: Annotated[str, Form(...)],
    count: Annotated[int, Form(ge=1, le=10)] = 10,
) -> list[DesignCandidate]:
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG, or WebP image.",
        )
    try:
        questionnaire_data = Questionnaire.model_validate_json(questionnaire)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The questionnaire form field must contain valid questionnaire JSON.",
        ) from exc
    try:
        return await OpenAIImageGenerationService().generate_designs(
            image=await image.read(),
            content_type=image.content_type,
            questionnaire=questionnaire_data,
            count=count,
        )
    except ImageGenerationNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ImageGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/generate-final", response_model=FinalDesignManifest)
async def generate_final_design(
    image: Annotated[UploadFile, File(...)],
    recommended_design: Annotated[str, Form(...)],
) -> FinalDesignManifest:
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG, or WebP image.",
        )
    try:
        recommendation = RecommendedDesign.model_validate_json(recommended_design)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The recommended_design form field must contain a valid "
                "RecommendedDesign JSON object."
            ),
        ) from exc
    try:
        return await OpenAIImageGenerationService().generate_final_design(
            image=await image.read(),
            content_type=image.content_type,
            recommendation=recommendation,
        )
    except ImageGenerationNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ImageGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
