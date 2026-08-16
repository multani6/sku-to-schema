"""
Tier 3 — keyword-based fallback classifier.

Used ONLY for rows whose Part_Manuf is not in MANUFACTURER_CATEGORY_MAP
(the long tail of ~50 small manufacturers + the "-" / no-manufacturer rows).

Design note: keywords are checked in priority order (most specific first)
against Part_Desc (lowercased). First match wins. This is deliberately a
simple, auditable rule set — not a black box — so every classification can
be traced back to the exact keyword that fired.
"""

import re

# (category, [keywords]) — order matters, first match wins.
# More specific / less ambiguous terms are listed first.
# Keywords marked with \b in the regex sense are whole-word matches — this
# matters for short/ambiguous tokens like "lt" (light abbreviation), which
# would otherwise false-positive inside words like "salt" or "result".
KEYWORD_RULES = [
    ("Lighting", [
        "led", "skylt", "skylight", "flor ", "light", "lamp",
        r"\blt\b", "chandelier", "flashlt", "motion lt",
    ]),
    ("Abrasives", ["disc", "sanding", "abrasive", "cut-off", "cut off", "grit"]),
    ("Building Materials", [
        "rail kit", "post trim", "post sleeve", "post cap", "post rdi",
        "blank post", "baluster", "patio dr", "gliding", "slider", "hopper",
        "drywall", "threshold", "rainscreen", "sheathing", "osb",
        "attic access", "mortar", "window", "door", "gate", "support post",
        "zip r", "decking", "doug fir", "stk smooth", "1s2e",
    ]),
    ("Electrical", [
        "elect tape", "battery", "batt ", "jumpstart", "wire", "cable",
        "dimmer", "timer", "box cover", "decor plate", "load cntr",
        "load center", "outlet", "gfci", "gfi",
    ]),
    ("Power Tools", ["drill", "driver", "saw", "sander", "grinder", "trimmer", "vacuum"]),
    ("Hand Tools & Accessories", ["tire pressure", "gauge", "kneeling pad", "bit holder", "tape"]),
]


def classify_by_keyword(part_desc: str) -> tuple[str, str]:
    """
    Returns (category, matched_keyword) or ("Other / Needs Manual Classification", "")
    if nothing matched.

    Keywords containing regex metacharacters (currently only \\b word-boundary
    markers) are matched with re.search; plain keywords use a fast substring
    check.
    """
    desc_lower = part_desc.lower()
    for category, keywords in KEYWORD_RULES:
        for kw in keywords:
            if "\\b" in kw:
                if re.search(kw, desc_lower):
                    return category, kw
            elif kw in desc_lower:
                return category, kw
    return "Other / Needs Manual Classification", ""