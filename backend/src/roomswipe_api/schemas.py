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


class DesignDensity(StrEnum):
    MINIMALIST = "minimalist"
    MAXIMALIST = "maximalist"


class Questionnaire(ApiModel):
    room_type: str
    budget_minor: int = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    effort: EffortLevel
    design_density: DesignDensity
    user_age: int = Field(ge=0, le=120)
    goals: list[str] = Field(default_factory=list)
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
    warmth: float = Field(ge=0, le=1)
    lighting: str
    items: list[str]
    questionnaire: Questionnaire


class SwipeEvent(ApiModel):
    candidate_id: str
    liked: bool
    comment: str | None = None


class PreferenceProfile(ApiModel):
    attributes: dict[str, float]
    confidence: float = Field(ge=0, le=1)
    liked_signals: list[str]
    disliked_signals: list[str]
    model_version: int = Field(default=0, ge=0)
    positive_count: int = Field(default=0, ge=0)
    negative_count: int = Field(default=0, ge=0)


class RecommendedItem(ApiModel):
    name: str
    description: str
    max_price_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class RecommendedBudget(ApiModel):
    max_total_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class RecommendedDesign(ApiModel):
    name: str
    description: str
    match_percent: int = Field(ge=0, le=100)
    items: list[RecommendedItem] = Field(min_length=1)
    budget: RecommendedBudget


class FinalizeRecommendationRequest(ApiModel):
    candidates: list[DesignCandidate] = Field(min_length=10, max_length=10)
    swipes: list[SwipeEvent] = Field(min_length=10, max_length=10)

    @model_validator(mode="after")
    def require_one_swipe_per_candidate(self) -> "FinalizeRecommendationRequest":
        candidate_ids = [candidate.id for candidate in self.candidates]
        swipe_ids = [swipe.candidate_id for swipe in self.swipes]
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("candidate ids must be unique")
        if len(set(swipe_ids)) != len(swipe_ids):
            raise ValueError("each candidate must have exactly one swipe")
        if set(candidate_ids) != set(swipe_ids):
            raise ValueError("swipes must match the candidate ids")
        return self


class FinalizeRecommendationResponse(ApiModel):
    recommended_design: RecommendedDesign


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
    description: str = ""
    merchant_name: str
    merchant_domain: str
    price_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    image_url: str | None = None
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

    @field_validator("country")
    @classmethod
    def require_us_delivery(cls, value: str) -> str:
        country = value.upper()
        if country != "US":
            raise ValueError("only US delivery is supported")
        return country

    @field_validator("currency")
    @classmethod
    def require_usd_budget(cls, value: str) -> str:
        currency = value.upper()
        if currency != "USD":
            raise ValueError("only USD budgets are supported")
        return currency


class CreateCartsRequest(ApiModel):
    offers: list[ProductOffer] = Field(min_length=1)
    country: str = Field(default="US", min_length=2, max_length=2)

    @field_validator("country")
    @classmethod
    def require_us_delivery(cls, value: str) -> str:
        country = value.upper()
        if country != "US":
            raise ValueError("only US delivery is supported")
        return country
