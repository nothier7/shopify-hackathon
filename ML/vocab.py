"""Fixed model vocabulary and questionnaire priors."""

STYLE_TAGS = frozenset(
    {
        "minimalist",
        "warm",
        "modern",
        "vintage",
        "industrial",
        "japandi",
        "cozy",
        "maximalist",
        "scandinavian",
        "coastal",
    }
)
MATERIAL_TAGS = frozenset(
    {"wood", "linen", "metal", "rattan", "velvet", "glass", "stone"}
)
COLOR_TAGS = frozenset({"neutral", "warm", "cool", "bold", "pastel", "dark", "white"})
FEATURE_TAGS = frozenset({"plants", "natural_materials", "white_furniture"})

GOAL_PRIORS = {
    "cozy": {"style:cozy": 0.25, "style:warm": 0.20, "material:linen": 0.12},
    "more_storage": {"style:minimalist": 0.15},
    "look_expensive": {"material:stone": 0.16, "material:wood": 0.12},
    "more_functional": {"style:minimalist": 0.16, "style:modern": 0.10},
    "guest_ready": {"style:cozy": 0.16, "style:warm": 0.12},
    "new_vibe": {"style:modern": 0.12},
}
