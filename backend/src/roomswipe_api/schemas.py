from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(word.capitalize() for word in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
    )


class EffortLevel(StrEnum):
    BUY_ONLY = "buy_only"
    SOME_DIY = "some_diy"
    MAJOR_CHANGES = "major_changes"


class Questionnaire(ApiModel):
    room_type: str
    budget_minor: int = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    effort: EffortLevel
    goals: list[str]
    optional_styles: list[str] = Field(default_factory=list)


class RoomAnalysis(ApiModel):
    room_type: str
    palette: list[str]
    existing_furniture: list[str]
    empty_zones: list[str]
    lighting: str
    architectural_constraints: list[str]
    confidence: float = Field(ge=0, le=1)


class DesignCandidate(ApiModel):
    id: str
    name: str
    image_url: str
    attributes: dict[str, float]


class SwipeEvent(ApiModel):
    candidate_id: str
    liked: bool


class PreferenceProfile(ApiModel):
    attributes: dict[str, float]
    confidence: float = Field(ge=0, le=1)
    liked_signals: list[str]
    disliked_signals: list[str]


class ProductChangeType(StrEnum):
    ADDED = "added"
    REPLACED = "replaced"


class BoundingBox(ApiModel):
    """A normalized rectangle in the final generated image."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def fit_inside_image(self) -> "BoundingBox":
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("bounding box must fit inside the image")
        return self


class ProductSlot(ApiModel):
    id: str
    category: str
    search_query: str
    colors: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    shape: str | None = None
    change_type: ProductChangeType
    must_match: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    budget_weight: float = Field(gt=0)
    confidence: float = Field(ge=0, le=1)
    bounding_box: BoundingBox | None = None


class FinalDesignManifest(ApiModel):
    final_image_url: str
    product_slots: list[ProductSlot] = Field(min_length=1)


class ProductOffer(ApiModel):
    product_id: str
    variant_id: str
    slot_id: str
    title: str
    merchant_name: str
    merchant_domain: str
    price_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    image_url: str
    checkout_url: str
    available: bool
    match_score: float | None = Field(default=None, ge=0, le=1)
    relaxed_preferences: list[str] = Field(default_factory=list)


class MerchantCart(ApiModel):
    cart_id: str
    merchant_name: str
    merchant_domain: str
    slot_ids: list[str]
    variant_ids: list[str]
    subtotal_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    continue_url: str


class MerchantCartFailure(ApiModel):
    merchant_domain: str
    slot_ids: list[str]
    detail: str


class CreateCartsResponse(ApiModel):
    carts: list[MerchantCart]
    failures: list[MerchantCartFailure]


class GenerateDesignsRequest(ApiModel):
    room: RoomAnalysis
    questionnaire: Questionnaire
    count: int = Field(default=6, ge=1, le=10)


class UpdatePreferencesRequest(ApiModel):
    candidates: list[DesignCandidate]
    swipes: list[SwipeEvent]
    prior: PreferenceProfile | None = None


class SelectProductsRequest(ApiModel):
    profile: PreferenceProfile
    offers: list[ProductOffer]
    budget_minor: int = Field(ge=0)


class SearchProductsRequest(ApiModel):
    manifest: FinalDesignManifest
    budget_minor: int = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    country: str = Field(default="US", min_length=2, max_length=2)
    region: str | None = None
    postal_code: str | None = None
    candidates_per_slot: int = Field(default=3, ge=1, le=10)

    @field_validator("country", "currency")
    @classmethod
    def uppercase_code(cls, value: str) -> str:
        return value.upper()


class CreateCartsRequest(ApiModel):
    offers: list[ProductOffer] = Field(min_length=1)
    country: str = Field(default="US", min_length=2, max_length=2)

    @field_validator("country")
    @classmethod
    def uppercase_country(cls, value: str) -> str:
        return value.upper()
