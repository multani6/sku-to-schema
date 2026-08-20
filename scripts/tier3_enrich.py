"""
tier3_enrich.py
--------------------------------------
Tier 3 light-depth enrichment pipeline for the ~916 non-appliance rows.

Design (deliberately lighter than Tier 1/2 — see project notes):
  - Category: assigned via manufacturer-rule -> keyword-fallback -> LLM
    (only the last ~5% of rows actually need an LLM call for category)
  - Brand / Manufacturer: cleaned of placeholders, resolved via LLM,
    then passed through enforce_manufacturer_consistency.py logic
  - Description: ONE short-format description per row (not the 5-format
    treatment Tier 1/2 got) — every row needs an LLM call for this part,
    since generating text isn't something a rule table can do.
  - Confidence tag: EXACT_SKU_VERIFIED / FAMILY_INFERRED /
    LOW_CONFIDENCE_NEEDS_REVIEW (same 3-tag scheme as Tier 1/2, for a
    consistent story across all three tiers)

IMPORTANT COST NOTE for the pitch: the "94.7% classified free" number
applies to CATEGORY ASSIGNMENT only. Description generation still needs
an LLM call for all 916 rows, because writing text isn't a rule-table
task. Don't conflate the two numbers — a judge who catches that would
read it as inflating the result.

Checkpointing: progress is saved after every single row to
outputs/tier3_checkpoint.json. If the script crashes or hits a rate
limit, re-running it picks up exactly where it left off instead of
reprocessing already-done rows or losing partial progress.

Run:  python scripts/tier3_enrich.py
"""

import collections
import csv
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from tier3_manufacturer_category_map import MANUFACTURER_CATEGORY_MAP, CATEGORIES
from tier3_keyword_classifier import classify_by_keyword

try:
    from groq import Groq
except ImportError:
    print("Missing dependency. Run: pip install groq --break-system-packages")
    sys.exit(1)

INPUT_PATH = "raw_data/tier3_input.csv"
CHECKPOINT_PATH = "outputs/tier3_checkpoint.json"
OUTPUT_JSON_PATH = "outputs/tier3_enriched.json"

MODEL = "openai/gpt-oss-120b"
# NOTE: switched from "llama-3.3-70b-versatile" on 15 Aug 2026 — Groq is
# decommissioning that model on 16 Aug 2026 (confirmed via their official
# deprecation notice). openai/gpt-oss-120b is Groq's recommended
# replacement for llama-3.3-70b-versatile workloads.

PLACEHOLDER_VALUES = {
    "-- unbranded --", "-- no unilog brand --", "-- no dib brand --", "-",
}

# Retry behaviour for rate-limit / transient errors (same pattern as Tier 2)
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 15


def clean_placeholder(value: str) -> str:
    """Returns '' if the value is a known placeholder, else the original value."""
    if not value:
        return ""
    if value.strip().lower() in PLACEHOLDER_VALUES:
        return ""
    return value.strip()


def get_rule_based_category(part_desc: str, part_manuf: str) -> tuple[str, str]:
    """
    Returns (category, method) using manufacturer-rule first, then
    keyword-fallback. Returns (None, "NEEDS_LLM") if neither rule fires.
    """
    if part_manuf in MANUFACTURER_CATEGORY_MAP:
        return MANUFACTURER_CATEGORY_MAP[part_manuf], "MANUFACTURER_RULE"

    category, matched_kw = classify_by_keyword(part_desc)
    if category != "Other / Needs Manual Classification":
        return category, "KEYWORD_FALLBACK"

    return None, "NEEDS_LLM"


def build_prompt(row: dict, known_category: str | None) -> str:
    brand_candidates = [
        clean_placeholder(row.get("E1_Brand", "")),
        clean_placeholder(row.get("Unilog_Brand", "")),
        clean_placeholder(row.get("DIB_Brand", "")),
    ]
    brand_candidates = [b for b in brand_candidates if b]
    brand_hint = brand_candidates[0] if brand_candidates else "(no brand given in source data)"

    if known_category:
        category_instruction = (
            f'The category has already been determined as "{known_category}" '
            f'(do not change it, just echo it back in your JSON response).'
        )
        category_list_note = ""
    else:
        category_instruction = (
            "Determine the single best category for this product from the list below."
        )
        category_list_note = f"\nAllowed categories: {', '.join(CATEGORIES)}"

    return f"""You are enriching one row of an industrial product catalog for a B2B distributor.

Product description (raw, abbreviated): {row.get('Part_Desc', '')}
Manufacturer part number: {row.get('Mfg_Part_Num', '')}
Brand field from source data: {brand_hint}
Manufacturer/supplier field from source data: {row.get('Part_Manuf', '') or '(not given)'}

{category_instruction}{category_list_note}

Tasks:
1. category: the product category (see above).
2. brand_name: the actual product brand, properly capitalized (e.g. "DeWalt", "Trex", "Kichler"). If the source brand field was empty/placeholder, infer the brand from the description or manufacturer field if reasonably obvious; otherwise use "Unknown".
3. manufacturer_name: the manufacturer/parent company name, properly formatted (e.g. "Stanley Black & Decker", "Trex Company Inc"). If not confidently determinable, use "Unknown".
4. short_desc: ONE short, clean, buyer-facing product description (60-100 characters), written the way a distributor catalog would phrase it.
   - Do not invent specifications (sizes, colors, voltages, materials) that are NOT present in the raw description.
   - CRITICAL: if the raw description DOES contain a size, dimension, color, finish, length, or variant code (e.g. "1nx6-16'", "Hatteras", "Grooved", "P120", "Black"), you MUST keep that distinguishing detail in short_desc. Two different part numbers must not end up with the same short_desc — if you find yourself writing a generic family name with no variant details, go back and re-check the raw description for a size/color/grit/finish you dropped.
   - Prioritize keeping (in this order, space permitting within ~100 chars): the specific variant detail (size/color/grit/finish) > the product family/series name > generic marketing words.
   - CRITICAL JSON-SAFETY RULE: NEVER use the literal double-quote character (") anywhere in any field value, including for inches. Write inches as "in" (e.g. "1/2 in x 18 in", not 1/2"x18"). Do not use straight or curly quote marks for feet either — write "ft" instead of the ' symbol. This is mandatory: a literal " inside a JSON string value breaks the response and the whole row fails.
5. confidence: one of "EXACT_SKU_VERIFIED" (you recognize this exact part number/product), "FAMILY_INFERRED" (you recognize the product family/brand but not this exact SKU), or "LOW_CONFIDENCE_NEEDS_REVIEW" (raw description is too ambiguous/abbreviated to be confident).

Respond with ONLY a JSON object, no other text, no markdown fences:
{{"category": "...", "brand_name": "...", "manufacturer_name": "...", "short_desc": "...", "confidence": "..."}}
"""


class DailyQuotaExhausted(Exception):
    """Raised when the Groq daily token quota is hit. Distinct from a
    genuine per-row data problem — retrying or giving up-with-a-placeholder
    are both wrong responses to this; the correct response is to stop the
    whole run immediately, without marking the current row as done, so a
    fresh API key can pick up exactly where we stopped."""
    pass


def call_llm(client: "Groq", prompt: str) -> dict:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1500,
            )
            text = response.choices[0].message.content.strip()
            # Strip accidental markdown fences if the model adds them anyway
            text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Defensive repair: the model occasionally slips a raw "
                # or ' inside a value despite being told not to, which
                # breaks JSON parsing. Try a targeted repair before
                # giving up and burning a full retry (saves quota) —
                # only replace quote characters that sit BETWEEN two
                # alphanumeric/whitespace characters, since those are
                # never structural JSON quotes (real JSON quotes are
                # always adjacent to {, }, [, ], :, or ,).
                repaired = re.sub(r'(?<=[a-zA-Z0-9])"(?=[a-zA-Z0-9\s])', "in", text)
                repaired = re.sub(r"(?<=[a-zA-Z0-9])'(?=[a-zA-Z0-9\s])", "ft", repaired)
                return json.loads(repaired)
        except Exception as e:
            err_str = str(e)
            is_daily_quota_error = (
                "tokens per day" in err_str.lower() or "TPD" in err_str
            )
            if is_daily_quota_error:
                # No point retrying or waiting — the error message itself
                # says "try again in Nm" (minutes), and this key's daily
                # allowance is simply spent. Fail fast instead of burning
                # 3 retries x 15s per remaining row for the rest of the run.
                raise DailyQuotaExhausted(err_str)
            print(f"    [retry {attempt}/{MAX_RETRIES}] LLM call failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    # All retries exhausted for a NON-quota reason (e.g. a genuinely
    # malformed response even after the repair attempt) — return a safe
    # fallback so the pipeline doesn't crash on one bad row. This row
    # gets flagged for review.
    return {
        "category": "Other / Needs Manual Classification",
        "brand_name": "Unknown",
        "manufacturer_name": "Unknown",
        "short_desc": "",
        "confidence": "LOW_CONFIDENCE_NEEDS_REVIEW",
        "_llm_call_failed": True,
    }


def load_checkpoint() -> dict:
    """
    Loads the checkpoint, migrating it from the old key format (plain
    Mfg_Part_Num) to the new format ("mpn::row_index") if needed.

    Migration deliberately does NOT carry over entries for any MPN that
    appears more than once in the input (currently just AVM6EV) — with
    the old format there's no way to tell which of the duplicate rows
    the saved record actually belonged to, so both are reprocessed
    fresh rather than risk mis-attributing one product's data to the
    other. This costs at most a couple of extra LLM calls and buys
    correctness.
    """
    if not os.path.exists(CHECKPOINT_PATH):
        return {}

    with open(CHECKPOINT_PATH, encoding="utf-8") as f:
        old = json.load(f)

    if not old or all("::" in k for k in old.keys()):
        return old  # empty, or already in the new format

    print("Old-format checkpoint detected — migrating to row-indexed keys "
          "(preserves already-completed work, no wasted API calls)...")

    with open(INPUT_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    mpn_counts = collections.Counter(r["Mfg_Part_Num"] for r in rows)
    duplicate_mpns = {m for m, c in mpn_counts.items() if c > 1}

    migrated = {}
    consumed = set()
    for i, row in enumerate(rows, start=1):
        mpn = row["Mfg_Part_Num"]
        if mpn in duplicate_mpns:
            continue  # force reprocessing for ambiguous duplicate-MPN rows
        if mpn in old and mpn not in consumed:
            row_key = f"{mpn}::{i}" if mpn else f"NOPART::{i}"
            migrated[row_key] = old[mpn]
            consumed.add(mpn)

    print(f"Migrated {len(migrated)}/{len(old)} rows. "
          f"{len(old) - len(migrated)} rows (duplicate-MPN or unmatched) will be reprocessed.")
    save_checkpoint(migrated)
    return migrated


def save_checkpoint(checkpoint: dict):
    os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2)


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: Set the GROQ_API_KEY environment variable before running.")
        sys.exit(1)
    client = Groq(api_key=api_key)

    with open(INPUT_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    checkpoint = load_checkpoint()
    print(f"Loaded checkpoint: {len(checkpoint)} rows already processed.")

    rule_classified_count = 0
    llm_classified_count = 0

    for i, row in enumerate(rows, start=1):
        mpn = row["Mfg_Part_Num"]
        # Use "mpn::row_index" as the checkpoint key, not just mpn.
        # Why: the source data has at least one genuine duplicate MPN
        # (AVM6EV appears twice, for two different products — a real
        # data-quality issue flagged elsewhere). Keying purely by MPN
        # meant the second row silently overwrote the first one in the
        # checkpoint, so a run over 916 rows only ever produced 915
        # output records — this fixes that while staying readable.
        row_key = f"{mpn}::{i}" if mpn else f"NOPART::{i}"

        if row_key in checkpoint:
            continue  # already done, resume-safe

        rule_category, rule_method = get_rule_based_category(
            row["Part_Desc"], row["Part_Manuf"]
        )
        if rule_category:
            rule_classified_count += 1
        else:
            llm_classified_count += 1

        prompt = build_prompt(row, known_category=rule_category)
        try:
            llm_result = call_llm(client, prompt)
        except DailyQuotaExhausted:
            print(f"\nDaily token quota exhausted at row {i}/{len(rows)} (Mfg_Part_Num={mpn}).")
            print("Stopping now WITHOUT marking this row as done, so no placeholder/garbage")
            print("data gets written. Get a fresh GROQ_API_KEY and re-run this same command —")
            print("it will resume from exactly this row.")
            sys.exit(0)

        final_category = rule_category if rule_category else llm_result.get("category", "Other / Needs Manual Classification")
        category_method = rule_method if rule_category else "LLM_CLASSIFIED"

        record = {
            **row,
            "category": final_category,
            "category_method": category_method,
            "BRAND_NAME": llm_result.get("brand_name", "Unknown"),
            "MANUFACTURER_NAME": llm_result.get("manufacturer_name", "Unknown"),
            "SHORT_DESC": llm_result.get("short_desc", ""),
            "_llm_confidence": llm_result.get("confidence", "LOW_CONFIDENCE_NEEDS_REVIEW"),
            "_llm_call_failed": llm_result.get("_llm_call_failed", False),
        }

        checkpoint[row_key] = record
        save_checkpoint(checkpoint)  # save after EVERY row — crash-safe

        if i % 25 == 0 or i == len(rows):
            print(f"[{i}/{len(rows)}] processed. (rule-classified so far: {rule_classified_count}, LLM-classified: {llm_classified_count})")

    # Final export
    final_records = list(checkpoint.values())
    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(final_records, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(final_records)} rows enriched.")
    print(f"Saved to {OUTPUT_JSON_PATH}")
    print(f"\nCategory source breakdown:")
    from collections import Counter
    method_counts = Counter(r["category_method"] for r in final_records)
    for m, c in method_counts.most_common():
        print(f"  {c:4d}  {m}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user (Ctrl+C). No data lost — every completed row was "
              "already saved to the checkpoint. Just re-run this same command to "
              "resume exactly where you left off.")
        sys.exit(0)