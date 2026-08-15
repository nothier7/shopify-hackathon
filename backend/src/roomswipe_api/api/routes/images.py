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
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _validate_image(image: UploadFile) -> str:
    if image.content_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG, or WebP image.",
        )
    return image.content_type


def _image_error(exc: ImageGenerationError) -> HTTPException:
    status_code = (
        status.HTTP_503_SERVICE_UNAVAILABLE
        if isinstance(exc, ImageGenerationNotConfiguredError)
        else status.HTTP_502_BAD_GATEWAY
    )
    return HTTPException(status_code=status_code, detail=str(exc))


@router.post("/analyze-room", response_model=RoomAnalysis)
async def analyze_room(image: Annotated[UploadFile, File(...)]) -> RoomAnalysis:
    content_type = _validate_image(image)
    try:
        return await OpenAIImageGenerationService().analyze_room(
            image=await image.read(),
            content_type=content_type,
        )
    except ImageGenerationError as exc:
        raise _image_error(exc) from exc


@router.post("/generate-designs", response_model=list[DesignCandidate])
async def generate_designs(
    image: Annotated[UploadFile, File(...)],
    questionnaire: Annotated[str, Form(...)],
    count: Annotated[int, Form(ge=1, le=10)] = 10,
) -> list[DesignCandidate]:
    content_type = _validate_image(image)
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
            content_type=content_type,
            questionnaire=questionnaire_data,
            count=count,
        )
    except ImageGenerationError as exc:
        raise _image_error(exc) from exc


@router.post("/generate-final-design", response_model=FinalDesignManifest)
async def generate_final_design(
    image: Annotated[UploadFile, File(...)],
    recommendation: Annotated[str, Form(...)],
    refinement: Annotated[str | None, Form()] = None,
) -> FinalDesignManifest:
    content_type = _validate_image(image)
    try:
        recommendation_data = RecommendedDesign.model_validate_json(recommendation)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The recommendation form field must contain valid recommendedDesign JSON.",
        ) from exc
    try:
        return await OpenAIImageGenerationService().generate_final_design(
            image=await image.read(),
            content_type=content_type,
            recommendation=recommendation_data,
            refinement=refinement,
        )
    except ImageGenerationError as exc:
        raise _image_error(exc) from exc
