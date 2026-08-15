from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# valid JSON

# valid JSON


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


class PreferenceProfile(ApiModel):
    attributes: dict[str, float]
    confidence: float = Field(ge=0, le=1)
    liked_signals: list[str]
    disliked_signals: list[str]


class ProductSlot(ApiModel):
    id: str
    category: str
    query: str
    preferred_colors: list[str] = Field(default_factory=list)
    preferred_materials: list[str] = Field(default_factory=list)
    max_price_minor: int = Field(ge=0)


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


class MerchantCart(ApiModel):
    merchant_name: str
    merchant_domain: str
    offer_ids: list[str]
    subtotal_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    continue_url: str


class UpdatePreferencesRequest(ApiModel):
    candidates: list[DesignCandidate]
    swipes: list[SwipeEvent]
    prior: PreferenceProfile | None = None


class SelectProductsRequest(ApiModel):
    profile: PreferenceProfile
    offers: list[ProductOffer]
    budget_minor: int = Field(ge=0)


class SearchProductsRequest(ApiModel):
    slots: list[ProductSlot]
    country: str = Field(default="US", min_length=2, max_length=2)


class CreateCartsRequest(ApiModel):
    offers: list[ProductOffer]
