"""Canonical blue-collar trade categories and keyword sets.

Used by:
  * The matching engine (to bucket a free-text listing into a category)
  * The homepage category buttons (slugs match the onclick handlers)
  * Future Stripe / analytics queries that want a category dimension

Keep slugs lowercase ASCII; keep keyword lists alphabetized within a category;
prefer short noun forms (the matcher applies word-boundary regex).
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

TRADE_CATEGORIES: Dict[str, List[str]] = {
    "plumbing": [
        "drain", "drain clearing", "faucet", "leak", "pipe", "pipe repair",
        "plumber", "plumbing", "sewer", "toilet", "water heater",
    ],
    "electrical": [
        "amp", "breaker", "circuit", "electric", "electrical", "electrician",
        "outlet", "panel", "rewire", "voltage", "wiring",
    ],
    "carpentry": [
        "cabinet", "carpenter", "carpentry", "deck", "drywall", "drywall patching",
        "framing", "trim", "wood", "woodwork",
    ],
    "hvac": [
        "ac", "air conditioner", "ductwork", "furnace", "heat pump", "hvac",
        "mini split", "refrigerant", "thermostat", "vent",
    ],
    "roofing": [
        "flashing", "gutter", "roof", "roofer", "roofing", "shingle",
        "skylight", "tile roof",
    ],
    "landscaping": [
        "irrigation", "landscaping", "lawn", "lawn care", "leaf removal",
        "mowing", "mulch", "snow removal", "sprinkler", "tree",
    ],
    "auto_repair": [
        "auto", "auto repair", "brake", "car repair", "engine", "mechanic",
        "muffler", "oil change", "tire", "transmission",
    ],
    "painting": [
        "exterior paint", "interior paint", "paint", "painter", "painting",
        "primer", "stain",
    ],
    "moving": [
        "haul", "loading", "move", "mover", "moving", "moving help", "packing",
    ],
    "handyman": [
        "fix", "handyman", "install", "odd jobs", "repair", "small repair",
    ],
}

# Pre-compile word-boundary regexes once per process. Slugs are returned in
# (slug, hits) tuples so callers can rank by match count.
_CATEGORY_PATTERNS: Dict[str, re.Pattern[str]] = {
    slug: re.compile(
        r"\b(" + "|".join(re.escape(k) for k in keywords) + r")\b",
        re.IGNORECASE,
    )
    for slug, keywords in TRADE_CATEGORIES.items()
}


def categorize_text(text: str) -> List[Tuple[str, int]]:
    """Return matching categories with hit counts, ranked highest first.

    Empty list when nothing matches. Callers usually want ``[0][0]`` for the
    best-guess category.
    """
    if not text:
        return []
    scored: List[Tuple[str, int]] = []
    for slug, pat in _CATEGORY_PATTERNS.items():
        n = len(pat.findall(text))
        if n:
            scored.append((slug, n))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


def primary_category(text: str) -> str | None:
    ranked = categorize_text(text)
    return ranked[0][0] if ranked else None
