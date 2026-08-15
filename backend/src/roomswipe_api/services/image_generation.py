"""OpenAI-backed room analysis and room-concept image generation."""

import base64
import json
import random
import re
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

import httpx

from roomswipe_api.config import Settings, get_settings
from roomswipe_api.schemas import (
    DesignCandidate,
    FinalDesignManifest,
    ProductChangeType,
    ProductSlot,
    Questionnaire,
    RecommendedDesign,
    RoomAnalysis,
)


class ImageGenerationService(Protocol):
    async def analyze_room(self, *, image: bytes, content_type: str) -> RoomAnalysis: ...
    async def generate_designs(
        self,
        *,
        image: bytes,
        content_type: str,
        questionnaire: Questionnaire,
        count: int,
    ) -> list[DesignCandidate]: ...
    async def generate_final_design(
        self,
        *,
        image: bytes,
        content_type: str,
        recommendation: RecommendedDesign,
        refinement: str | None = None,
    ) -> FinalDesignManifest: ...


class ImageGenerationError(RuntimeError):
    """An external image service could not complete the requested work."""


class ImageGenerationNotConfiguredError(ImageGenerationError):
    """The server has no OPENAI_API_KEY yet."""


@dataclass(frozen=True, slots=True)
class Style:
    name: str
    warmth: float
    lighting: str
    items: tuple[str, ...]
    attributes: dict[str, float]


STYLES: tuple[Style, ...] = (
    Style(
        "Scandinavian",
        0.70,
        "soft natural daylight",
        ("light oak furniture", "linen textiles", "simple pendant lamp"),
        {"minimalism": 0.85, "warmth": 0.70, "color": 0.25},
    ),
    Style(
        "Mid-century modern",
        0.72,
        "warm ambient lamps",
        ("walnut sideboard", "tapered-leg seating", "brass floor lamp"),
        {"minimalism": 0.55, "warmth": 0.72, "color": 0.55},
    ),
    Style(
        "Japandi",
        0.62,
        "diffused natural daylight",
        ("low-profile wood furniture", "paper lantern", "ceramic accents"),
        {"minimalism": 0.90, "warmth": 0.62, "color": 0.20},
    ),
    Style(
        "Industrial loft",
        0.35,
        "directional track lighting",
        ("metal shelving", "leather seating", "exposed-style fixtures"),
        {"minimalism": 0.45, "warmth": 0.35, "color": 0.35},
    ),
    Style(
        "Contemporary",
        0.50,
        "layered recessed and accent lighting",
        ("clean-lined sofa", "abstract art", "sculptural table lamp"),
        {"minimalism": 0.70, "warmth": 0.50, "color": 0.45},
    ),
    Style(
        "Bohemian",
        0.82,
        "golden table and floor lamps",
        ("woven rug", "plants", "textured pillows"),
        {"minimalism": 0.25, "warmth": 0.82, "color": 0.80},
    ),
    Style(
        "Coastal",
        0.68,
        "bright natural daylight",
        ("linen sofa", "rattan accents", "airy curtains"),
        {"minimalism": 0.60, "warmth": 0.68, "color": 0.45},
    ),
    Style(
        "Art Deco",
        0.60,
        "dramatic warm accent lighting",
        ("velvet chair", "geometric mirror", "brass details"),
        {"minimalism": 0.30, "warmth": 0.60, "color": 0.75},
    ),
    Style(
        "Modern farmhouse",
        0.78,
        "warm pendant and table lighting",
        ("wood dining table", "neutral upholstery", "vintage-style rug"),
        {"minimalism": 0.45, "warmth": 0.78, "color": 0.35},
    ),
    Style(
        "Eclectic",
        0.74,
        "layered lamps and natural light",
        ("gallery wall", "mixed-pattern textiles", "statement chair"),
        {"minimalism": 0.15, "warmth": 0.74, "color": 0.90},
    ),
)


def choose_styles(count: int, *, rng: random.Random | None = None) -> list[Style]:
    """Return distinct styles in a fresh random order."""
    if not 1 <= count <= len(STYLES):
        raise ValueError(f"count must be between 1 and {len(STYLES)}")
    selected = list(STYLES)
    (rng or random.SystemRandom()).shuffle(selected)
    return selected[:count]


class OpenAIImageGenerationService:
    """Calls the OpenAI REST API without coupling the app to an SDK version."""

    def __init__(
        self, settings: Settings | None = None, *, transport: httpx.AsyncBaseTransport | None = None
    ):
        self.settings = settings or get_settings()
        self.transport = transport

    async def analyze_room(self, *, image: bytes, content_type: str) -> RoomAnalysis:
        self._require_key()
        # turn image bytes into base 64
        encoded_image = base64.b64encode(image).decode("ascii")
        payload = {
            "model": self.settings.openai_vision_model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Analyze this room. Return ONLY JSON with room_type, palette, "
                                "existing_furniture, empty_zones, lighting, "
                                "architectural_constraints, and confidence (0 to 1)."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:{content_type};base64,{encoded_image}",
                        },
                    ],
                }
            ],
        }
        # get text containing room info
        response = await self._post("/responses", payload)
        try:
            return RoomAnalysis.model_validate_json(_response_text(response))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ImageGenerationError(
                "OpenAI returned room analysis in an unexpected format."
            ) from exc

    async def generate_designs(
        self,
        *,
        image: bytes,
        content_type: str,
        questionnaire: Questionnaire,
        count: int,
    ) -> list[DesignCandidate]:
        return [
            await self._edit_style(image, content_type, questionnaire, style)
            for style in choose_styles(count)
        ]

    async def generate_final_design(
        self,
        *,
        image: bytes,
        content_type: str,
        recommendation: RecommendedDesign,
        refinement: str | None = None,
    ) -> FinalDesignManifest:
        self._require_key()
        image_url = f"data:{content_type};base64,{base64.b64encode(image).decode('ascii')}"
        response = await self._post(
            "/images/edits",
            {
                "model": self.settings.openai_image_model or "gpt-image-1.5",
                "images": [{"image_url": image_url}],
                "prompt": _final_room_edit_prompt(recommendation, refinement),
                "input_fidelity": "high",
                "size": "1536x1024",
                "quality": "medium",
                "output_format": "png",
            },
        )
        return FinalDesignManifest(
            final_image_url=_image_url_from_response(response),
            product_slots=_product_slots(recommendation),
        )

    async def _edit_style(
        self, image: bytes, content_type: str, questionnaire: Questionnaire, style: Style
    ) -> DesignCandidate:
        self._require_key()
        image_url = f"data:{content_type};base64,{base64.b64encode(image).decode('ascii')}"
        response = await self._post(
            "/images/edits",
            {
                "model": self.settings.openai_image_model or "gpt-image-1.5",
                "images": [{"image_url": image_url}],
                "prompt": _room_edit_prompt(questionnaire, style),
                "input_fidelity": "high",
                "size": "1536x1024",
                "quality": "medium",
                "output_format": "png",
            },
        )
        return _candidate_from_response(response, style, questionnaire)

    async def _generate_style(
        self, room: RoomAnalysis, questionnaire: Questionnaire, style: Style
    ) -> DesignCandidate:
        self._require_key()
        response = await self._post(
            "/images/generations",
            {
                "model": self.settings.openai_image_model or "gpt-image-1.5",
                "prompt": _design_prompt(room, questionnaire, style),
                "size": "1536x1024",
                "quality": "medium",
            },
        )
        return _candidate_from_response(response, style, questionnaire)

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url="https://api.openai.com/v1", timeout=90, transport=self.transport
            ) as client:
                response = await client.post(
                    path,
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise ImageGenerationError(
                f"OpenAI request failed ({exc.response.status_code})."
            ) from exc
        except httpx.HTTPError as exc:
            raise ImageGenerationError("Could not reach OpenAI.") from exc

    def _require_key(self) -> None:
        if not self.settings.openai_api_key:
            raise ImageGenerationNotConfiguredError(
                "OPENAI_API_KEY is not configured on this server."
            )


def _response_text(response: dict[str, Any]) -> str:
    for output in response.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                return content["text"]
    raise ImageGenerationError("OpenAI response did not contain text.")


def _candidate_from_response(
    response: dict[str, Any], style: Style, questionnaire: Questionnaire
) -> DesignCandidate:
    image_url = _image_url_from_response(response)
    return DesignCandidate(
        id=str(uuid4()),
        name=style.name,
        image_url=image_url,
        attributes=style.attributes,
        warmth=style.warmth,
        lighting=style.lighting,
        items=list(style.items),
        questionnaire=questionnaire,
    )


def _image_url_from_response(response: dict[str, Any]) -> str:
    try:
        image_data = response["data"][0]
        encoded = image_data.get("b64_json")
        return f"data:image/png;base64,{encoded}" if encoded else image_data["url"]
    except (IndexError, KeyError, TypeError) as exc:
        raise ImageGenerationError("OpenAI returned an image in an unexpected format.") from exc


def _product_slots(recommendation: RecommendedDesign) -> list[ProductSlot]:
    return [
        ProductSlot(
            id=f"{_slug(item.name)}-{index}",
            category=item.name,
            search_query=item.description,
            styles=[recommendation.name],
            change_type=ProductChangeType.ADDED,
            must_match=[item.name],
            budget_weight=max(1, item.max_price_minor),
            confidence=recommendation.match_percent / 100,
        )
        for index, item in enumerate(recommendation.items, start=1)
    ]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def _final_room_edit_prompt(recommendation: RecommendedDesign, refinement: str | None) -> str:
    item_descriptions = "; ".join(item.description for item in recommendation.items)
    refinement_text = f" Additional request: {refinement}." if refinement else ""
    return (
        "Use the uploaded room photo as the exact starting point. Preserve its architecture, "
        "dimensions, windows, doors, fixed features, camera angle, and perspective. "
        f"Create one photorealistic {recommendation.name} redesign. "
        f"Direction: {recommendation.description} Products to add: {item_descriptions}."
        f"{refinement_text} Do not include people, text, labels, collages, or watermarks."
    )


def _design_prompt(room: RoomAnalysis, questionnaire: Questionnaire, style: Style) -> str:
    existing_furniture = ", ".join(room.existing_furniture) or "none specified"
    palette = ", ".join(room.palette) or "designer-selected neutral palette"
    empty_zones = ", ".join(room.empty_zones) or "no specific zones"
    goals = ", ".join(questionnaire.goals)
    return (
        f"Create a photorealistic wide interior-design concept for a {room.room_type}. "
        f"Style: {style.name}. Preserve these existing features: {existing_furniture}. "
        f"Use this palette: {palette}. Address these empty zones: {empty_zones}. "
        f"Use {style.lighting}. Include: {', '.join(style.items)}. "
        f"The user goals are: {goals}. Budget: {questionnaire.budget_minor} "
        f"{questionnaire.currency}; effort level: {questionnaire.effort}. "
        "Show one coherent, realistic room only. Do not include people, text, labels, "
        "collages, or watermarks."
    )


def _room_edit_prompt(questionnaire: Questionnaire, style: Style) -> str:
    goals = ", ".join(questionnaire.goals) or "create a comfortable, functional room"
    return (
        "Use the uploaded empty room photo as the exact starting point. Preserve its architecture, "
        "room dimensions, windows, doors, fixed features, camera angle, and perspective. "
        "Furnish and "
        f"decorate it as a photorealistic {questionnaire.room_type} in {style.name} style. "
        f"The user wants a {questionnaire.design_density} design for a "
        f"{questionnaire.user_age}-year-old. Budget: {questionnaire.budget_minor} "
        f"{questionnaire.currency}; effort level: {questionnaire.effort}. Goals: {goals}. "
        f"Include {', '.join(style.items)} and use {style.lighting}. Return one coherent, "
        "realistic redesigned version of this same room. Do not include people, text, labels, "
        "collages, or watermarks."
    )
