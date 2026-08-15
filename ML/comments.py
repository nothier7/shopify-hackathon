"""Immediate local preference signals extracted from swipe comments."""

import re

COMMENT_RULES = (
    (
        re.compile(r"wood|oak|timber", re.IGNORECASE),
        ("material:wood", "feature:natural_materials"),
    ),
    (re.compile(r"linen|textile", re.IGNORECASE), ("material:linen",)),
    (
        re.compile(r"rattan|wicker|cane", re.IGNORECASE),
        ("material:rattan", "feature:natural_materials"),
    ),
    (re.compile(r"plant|greenery", re.IGNORECASE), ("feature:plants",)),
    (re.compile(r"warm|warmer|cozy|cosy", re.IGNORECASE), ("style:warm", "style:cozy")),
    (re.compile(r"minimal|uncluttered", re.IGNORECASE), ("style:minimalist",)),
    (
        re.compile(r"cold|sterile|clinical", re.IGNORECASE),
        ("color:cool", "color:white"),
    ),
    (
        re.compile(r"maximal|busy|too much", re.IGNORECASE),
        ("style:maximalist", "color:bold"),
    ),
)
NEGATIVE_CONTEXT = re.compile(
    r"\b(no|not|avoid|hate|dislike|less|too|without|never|sterile|busy)\b",
    re.IGNORECASE,
)


def parse_comment(comment: str | None) -> tuple[set[str], set[str]]:
    if not comment:
        return set(), set()
    reinforced: set[str] = set()
    suppressed: set[str] = set()
    for pattern, keys in COMMENT_RULES:
        match = pattern.search(comment)
        if not match:
            continue
        window = comment[max(0, match.start() - 24) : match.end() + 24]
        (suppressed if NEGATIVE_CONTEXT.search(window) else reinforced).update(keys)
    reinforced.difference_update(suppressed)
    return reinforced, suppressed
