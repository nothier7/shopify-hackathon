"""Preference-aware product scoring and hard-budget optimization."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import replace

from .contracts import PreferenceProfile, ProductOffer


def _sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(-60, min(60, value))))


def rank_and_optimize(
    profile: PreferenceProfile,
    offers: list[ProductOffer],
    budget_minor: int,
) -> tuple[ProductOffer, ...]:
    weighted: list[ProductOffer] = []
    for offer in offers:
        if not offer.available or offer.price_minor > budget_minor:
            continue
        searchable = offer.title.lower().replace("-", "_")
        matched = [
            value
            for key, value in profile.attributes.items()
            if key.split(":")[-1] in searchable
        ]
        preference_score = _sigmoid(sum(matched)) if matched else 0.5
        catalog_score = offer.match_score if offer.match_score is not None else 0.5
        score = round(
            max(0.0, min(1.0, 0.65 * catalog_score + 0.35 * preference_score)), 4
        )
        weighted.append(replace(offer, match_score=score))

    groups: dict[str, list[ProductOffer]] = defaultdict(list)
    for offer in weighted:
        groups[offer.slot_id].append(offer)

    states: dict[int, tuple[float, tuple[ProductOffer, ...]]] = {0: (0.0, ())}
    for slot_offers in groups.values():
        next_states = dict(states)
        for spent, (score, selected) in states.items():
            for offer in slot_offers:
                new_spent = spent + offer.price_minor
                if new_spent > budget_minor:
                    continue
                new_score = score + (offer.match_score or 0.0)
                if (
                    new_spent not in next_states
                    or new_score > next_states[new_spent][0]
                ):
                    next_states[new_spent] = (new_score, (*selected, offer))
        best_score = -1.0
        states = {}
        for spent, state in sorted(next_states.items()):
            if state[0] > best_score:
                states[spent] = state
                best_score = state[0]

    return max(
        states.values(),
        key=lambda state: (state[0], -sum(item.price_minor for item in state[1])),
    )[1]
