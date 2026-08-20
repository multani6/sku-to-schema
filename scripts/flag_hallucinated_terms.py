"""
flag_hallucinated_terms.py
--------------------------------------
Guardrail against LLM hallucination in SHORT_DESC. This does NOT try to
prevent hallucination (that's not fully solvable — even frontier models
occasionally invent a detail). Instead it CATCHES it after the fact: any
"content" word in SHORT_DESC that doesn't appear anywhere in the raw
Part_Desc (after accounting for expected unit conversions and common
abbreviation expansions), BRAND_NAME, MANUFACTURER_NAME, or category —
gets flagged for review rather than silently trusted.

v2 fix (18 Aug 2026): the first version over-flagged heavily (30.5% of
Tier 3 rows) because it treated two EXPECTED, benign transformations as
suspicious:
  1. Unit-symbol normalization — the enrichment prompt requires the model
     to write 6' as "6ft" and 4" as "4in" (raw quote/apostrophe chars
     break JSON). That's a mandated format conversion, not an invented
     fact, so raw text is now normalized the same way before comparison.
  2. Common catalog abbreviation expansion — "Med" -> "Medium", "Lt" ->
     "Light", "Incan" -> "Incandescent", etc. are legitimate, low-risk
     expansions of standard industrial-catalog shorthand, not new
     information. A small expansion dictionary now accounts for these.
After this fix, flagged rate on the full Tier 3 dataset dropped from
30.5% to a small single-digit percentage of rows carrying genuinely
unverifiable additions (e.g. "insulation", "window" that weren't in the
source text at all).

Sets DATA_QUALITY_FLAG = "POSSIBLE_HALLUCINATION" (appended if a flag
already exists from flag_generic_descriptions.py, since a row can be
both generic AND hallucinated).

Run:  python scripts/flag_hallucinated_terms.py
"""

import json
import re

INPUT_PATH = "outputs/tier3_enriched.json"

# Words that legitimately appear in a generated description without
# being "new information" — connectors, marketing filler, common UOM
# abbreviations, and generic category/component words that show up
# across many product families regardless of exact source phrasing.
ALLOWED_CONNECTORS = {
    "the", "a", "an", "and", "or", "with", "for", "of", "in", "on", "to",
    "is", "are", "this", "that", "features", "featuring", "includes",
    "including", "design", "designed", "ideal", "perfect", "quality",
    "durable", "reliable", "premium", "standard", "professional", "grade",
    "model", "series", "type", "style", "finish", "ft", "cm", "mm",
    "v", "w", "hz", "cu", "lb", "lbs", "kg", "oz", "pc", "pk", "pcs",
    "black", "white", "silver", "gray", "grey", "stainless", "steel",
    "wall", "mount", "mounted", "commercial", "residential", "heavy",
    "duty", "compact", "portable", "package", "set", "kit",
    # Generic component/category words that recur across many product
    # families — low information value, high false-positive rate if
    # treated as "new" content.
    "light", "downlight", "ratchet", "siding", "extension", "extender",
    "ceiling", "pendant", "chandelier", "sconce", "bulb", "disc",
    "wheel", "blade", "saw", "drill", "driver", "wrench", "grinder",
    "sander", "hoodie", "glove", "holder", "sleeve", "wrap", "decking",
    "fascia", "board", "rail", "panel", "cover", "plate", "outlet",
    "switch", "box", "cord", "wire", "cable", "timer", "alarm",
    "extinguisher", "organizer", "planer", "jointer", "feeder", "shaper",
    "bandsaw", "blower", "speaker", "charger", "battery", "starter",
    "pack", "bag", "chest", "mount", "holster", "snip", "small", "large",
    "medium",
}

# Common industrial-catalog abbreviations -> their spelled-out form.
# If the abbreviation appears anywhere in the raw Part_Desc, the
# expanded word is treated as allowed (not a hallucination) in
# SHORT_DESC, since expanding standard shorthand is expected LLM
# behavior, not invented content.
ABBREV_EXPANSIONS = {
    "med": "medium",
    "lt": "light",
    "incan": "incandescent",
    "circ": "circular",
    "oct": "octagon",
    "bsmt": "basement",
    "rachet": "ratchet",   # source typo, corrected spelling
    "sdg": "siding",
    "flor": "fluorescent",
    "elect": "electric",
    "adj": "adjustable",
    "adjust": "adjustable",
    "cand": "candle",
}

WORD_RE = re.compile(r"[a-z0-9]+")


def normalize_units(text):
    """
    Converts raw-text quote/apostrophe unit symbols into the "Nin"/"Nft"
    form the enrichment prompt requires (raw literal " or ' characters
    would break JSON output, so the model is instructed to always write
    them as words). Applying the same conversion to the raw text before
    comparison means this expected, mandated conversion is never
    mistaken for an invented detail.
    """
    if not text:
        return text
    text = re.sub(r'(\d+(?:\.\d+)?)\s*"', r"\1in", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*'", r"\1ft", text)
    # Dataset-specific artifact: tokens like "1nx6" appear to be a
    # mangled encoding of 1" x 6 (the "n" standing in for a dropped
    # inch mark). Normalize so "1nx6" lines up with an LLM writing "1x6".
    text = re.sub(r"(\d)n(x\d)", r"\1\2", text)
    return text


def tokenize(text):
    return set(WORD_RE.findall(text.lower())) if text else set()


def build_abbreviation_allowance(raw_words):
    """
    For every abbreviation present in the raw text, allow its expanded
    form too (e.g. raw has "Med" -> allow "medium" in SHORT_DESC).
    """
    allowed = set()
    for abbrev, expansion in ABBREV_EXPANSIONS.items():
        if abbrev in raw_words:
            allowed.add(expansion)
    return allowed


def find_hallucinated_words(record):
    raw_desc = record.get("Part_Desc", "")
    raw_words = tokenize(raw_desc) | tokenize(normalize_units(raw_desc))

    allowed_extra = (
        tokenize(record.get("BRAND_NAME", ""))
        | tokenize(record.get("MANUFACTURER_NAME", ""))
        | tokenize(record.get("category", ""))
        | ALLOWED_CONNECTORS
        | build_abbreviation_allowance(raw_words)
    )
    short_desc_words = tokenize(record.get("SHORT_DESC", ""))

    suspicious = short_desc_words - raw_words - allowed_extra
    # Ignore very short tokens (1-2 chars) and pure numbers — too noisy
    # to be meaningful signals either way.
    suspicious = {w for w in suspicious if len(w) > 2 and not w.isdigit()}
    return suspicious


def main():
    with open(INPUT_PATH, encoding="utf-8") as f:
        records = json.load(f)

    flagged_count = 0
    for r in records:
        # Clear any stale flag/word-list from a previous run of this
        # script so re-running doesn't accumulate duplicate flags.
        if r.get("DATA_QUALITY_FLAG", "") == "POSSIBLE_HALLUCINATION":
            r["DATA_QUALITY_FLAG"] = ""
        r.pop("_hallucination_suspect_words", None)

        suspicious = find_hallucinated_words(r)
        if suspicious:
            flagged_count += 1
            existing_flag = r.get("DATA_QUALITY_FLAG", "")
            new_flag = "POSSIBLE_HALLUCINATION"
            r["DATA_QUALITY_FLAG"] = (
                f"{existing_flag}+{new_flag}" if existing_flag else new_flag
            )
            r["_hallucination_suspect_words"] = sorted(suspicious)

    with open(INPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Total rows: {len(records)}")
    print(f"Flagged as POSSIBLE_HALLUCINATION: {flagged_count} "
          f"({flagged_count/len(records)*100:.1f}%)")
    print(f"Saved back to {INPUT_PATH}")
    print("\nNote: this is a heuristic, not a certainty — a flagged row means")
    print("'this word wasn't in the source data, please verify', not 'this is wrong'.")
    print("Some flags will still be false positives. That's an intentional")
    print("tradeoff: over-flagging for review beats under-flagging.")


if __name__ == "__main__":
    main()