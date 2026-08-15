"""Urja's room-analysis and image-generation service boundary."""

from typing import Protocol

from roomswipe_api.schemas import (
    DesignCandidate,
    FinalDesignManifest,
    Questionnaire,
    RecommendedDesign,
    RoomAnalysis,
)


class ImageGenerationService(Protocol):
    async def analyze_room(self, *, image: bytes, content_type: str) -> RoomAnalysis: ...

    async def generate_designs(
        self,
        *,
        room: RoomAnalysis,
        questionnaire: Questionnaire,
        count: int,
    ) -> list[DesignCandidate]: ...

    async def generate_final_design(
        self,
        *,
        room: RoomAnalysis,
        recommendation: RecommendedDesign,
        refinement: str | None = None,
    ) -> FinalDesignManifest: ...
