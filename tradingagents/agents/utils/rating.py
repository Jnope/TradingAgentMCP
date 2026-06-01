"""Shared 5-tier rating vocabulary and a deterministic heuristic parser.

The same five-tier scale (买入, 增持, 持有, 减持, 卖出) is used by:
- The Research Manager (investment plan recommendation)
- The Portfolio Manager (final position decision)
- The signal processor (rating extracted for downstream consumers)
- The memory log (rating tag stored alongside each decision entry)

Centralising it here avoids drift between those call sites.
"""

from __future__ import annotations

import re
from typing import Tuple


# Canonical, ordered 5-tier scale (most bullish to most bearish).
RATINGS_5_TIER: Tuple[str, ...] = (
    "买入", "增持", "持有", "减持", "卖出",
)

_RATING_SET = {r.lower() for r in RATINGS_5_TIER}

# Also support English equivalents for backward compatibility
_RATING_SET_EN = {"buy", "overweight", "hold", "underweight", "sell"}
_EN_TO_CN = {
    "buy": "买入", "overweight": "增持", "hold": "持有",
    "underweight": "减持", "sell": "卖出",
}

# Matches "评级: X" / "rating - X" / "评级: **X**" — tolerates markdown
# bold wrappers and either a colon or hyphen separator.
_RATING_LABEL_RE = re.compile(r"(?:评级|rating).*?[:\-][\s*]*(\S+)", re.IGNORECASE)


def parse_rating(text: str, default: str = "持有") -> str:
    """Heuristically extract a 5-tier rating from prose text.

    Two-pass strategy:
    1. Look for an explicit "评级: X" label (tolerant of markdown bold).
    2. Fall back to the first 5-tier rating word found anywhere in the text.

    Returns a Chinese rating string, or ``default`` if no rating word appears.
    """
    for line in text.splitlines():
        m = _RATING_LABEL_RE.search(line)
        if m:
            val = m.group(1).strip("*:.,")
            if val.lower() in _RATING_SET:
                return val
            if val.lower() in _RATING_SET_EN:
                return _EN_TO_CN[val.lower()]

    for line in text.splitlines():
        for word in line.split():
            clean = word.strip("*:.,")
            if clean.lower() in _RATING_SET:
                return clean
            if clean.lower() in _RATING_SET_EN:
                return _EN_TO_CN[clean.lower()]

    return default
