from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

from roomswipe_api.config import get_settings
from roomswipe_api.schemas import (
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
STREAM_CHUNK_BYTES = 64 * 1024


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
            image=await _read_room_image(image),
            content_type=image.content_type,
        )
    except ImageGenerationNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ImageGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


# full endpoint: /api/v1/images/generate-designs
@router.post("/generate-designs", response_model=None)
async def generate_designs(
    image: Annotated[UploadFile, File(...)],
    questionnaire: Annotated[str, Form(...)],
    count: Annotated[int, Form(ge=1, le=10)] = 10,
) -> StreamingResponse:
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
        designs = await OpenAIImageGenerationService().generate_designs(
            image=await _read_room_image(image),
            content_type=image.content_type,
            questionnaire=questionnaire_data,
            count=count,
        )
        return _stream_models(designs)
    except ImageGenerationNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ImageGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/generate-final", response_model=None)
async def generate_final_design(
    image: Annotated[UploadFile, File(...)],
    recommended_design: Annotated[str, Form(...)],
) -> StreamingResponse:
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
        manifest = await OpenAIImageGenerationService().generate_final_design(
            image=await _read_room_image(image),
            content_type=image.content_type,
            recommendation=recommendation,
        )
        return _stream_models(manifest)
    except ImageGenerationNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ImageGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


async def _read_room_image(image: UploadFile) -> bytes:
    content = await image.read()
    if len(content) > get_settings().room_image_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Choose a room image smaller than 4MB.",
        )
    return content


def _stream_models(value: BaseModel | list[BaseModel]) -> StreamingResponse:
    if isinstance(value, list):
        payload = "[" + ",".join(model.model_dump_json(by_alias=True) for model in value) + "]"
    else:
        payload = value.model_dump_json(by_alias=True)

    async def chunks() -> AsyncIterator[str]:
        for offset in range(0, len(payload), STREAM_CHUNK_BYTES):
            yield payload[offset : offset + STREAM_CHUNK_BYTES]

    return StreamingResponse(chunks(), media_type="application/json")
