"""
merge_tier1_source_data.py
-----------------------------
Merges the real, web-verified manufacturer data (tier1_source_data.py)
into the LLM-enriched Tier-1 records — filling MFR URL, Ref URLs,
dimensions, and back-filling any attribute values (sound level, wash
cycles, material) that the LLM step correctly left blank because it
didn't actually know them.

Every merged record also gets a "_source_verification" note recording
whether the underlying data was EXACT_SKU_VERIFIED, FAMILY_INFERRED, or
OFFICIAL_GROUND_TRUTH — so nothing is silently presented with more
confidence than it deserves.

Input:  raw_data/html/tier1_llm_enriched.json
        scripts/tier1_source_data.py  (import)
Output: raw_data/html/tier1_final.json

Run:    python scripts/merge_tier1_source_data.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from tier1_source_data import SOURCE_DATA  # noqa: E402

ENRICHED_PATH = "raw_data/html/tier1_llm_enriched.json"
OUTPUT_PATH = "raw_data/html/tier1_final.json"


def fill_attribute_if_matching(record, label_keywords, value, uom=""):
    """
    If an attribute row already has a matching label but an empty
    value, fill it. If no matching row exists anywhere, append to the
    first fully-empty attribute slot. Never overwrites an existing
    LLM-provided value.
    """
    label_keywords = [k.lower() for k in label_keywords]

    # First pass: find a matching label with an empty value
    for i in range(1, 51):
        label = record.get(f"ATTRIBUTE_LABEL {i}", "")
        if label and any(k in label.lower() for k in label_keywords):
            if not record.get(f"ATTRIBUTE_VALUE {i}", ""):
                record[f"ATTRIBUTE_VALUE {i}"] = value
                if uom:
                    record[f"ATTRIBUTE_UOM {i}"] = uom
            return record  # matching label found (filled or already had a value)

    # Second pass: no matching label existed — append to first empty slot
    for i in range(1, 51):
        if not record.get(f"ATTRIBUTE_LABEL {i}", ""):
            record[f"ATTRIBUTE_LABEL {i}"] = label_keywords[0].title()
            record[f"ATTRIBUTE_VALUE {i}"] = value
            if uom:
                record[f"ATTRIBUTE_UOM {i}"] = uom
            return record

    return record  # all 50 slots full — skip


def merge_source_into_record(record, source):
    record["MFR URL"] = source.get("mfr_url", "")
    ref_urls = source.get("ref_urls", [])
    for i in range(5):
        record[f"Ref URL {i+1}"] = ref_urls[i] if i < len(ref_urls) else ""

    if source.get("height_in"):
        record["HEIGHT"] = source["height_in"]
        record["HEIGHT_UOM"] = "in"
    if source.get("width_in"):
        record["WIDTH"] = source["width_in"]
        record["WIDTH_UOM"] = "in"
    if source.get("depth_in"):
        record["LENGTH"] = source["depth_in"]
        record["LENGTH_UOM"] = "in"

    if source.get("sound_level_dba"):
        record = fill_attribute_if_matching(
            record, ["sound level"], source["sound_level_dba"], "dBA"
        )
    if source.get("wash_cycles"):
        record = fill_attribute_if_matching(
            record, ["number of wash cycles", "wash cycles"], source["wash_cycles"]
        )
    if source.get("material"):
        record = fill_attribute_if_matching(record, ["material"], source["material"])
    if source.get("place_settings"):
        record = fill_attribute_if_matching(
            record, ["place setting"], source["place_settings"]
        )
    if source.get("voltage"):
        record = fill_attribute_if_matching(
            record, ["voltage rating"], source["voltage"], "V"
        )
    if source.get("amperage"):
        record = fill_attribute_if_matching(
            record, ["amperage rating"], source["amperage"], "A"
        )
    if source.get("certifications") and not record.get("Standard/Approvals"):
        record["Standard/Approvals"] = source["certifications"]

    # --- New quick-win fields: commercial + images/docs/compliance ---
    if source.get("list_price") and not record.get("List Price"):
        record["List Price"] = source["list_price"]
    if source.get("warranty") and not record.get("Warranty"):
        record["Warranty"] = source["warranty"]
    if source.get("discontinued") and not record.get("Discontinued"):
        record["Discontinued"] = source["discontinued"]
    if source.get("product_image_url") and not record.get("Product Image"):
        record["Product Image"] = source["product_image_url"]

    # --- Additional grounded attributes (control type, rack, capacity, smart features) ---
    if source.get("control_type"):
        record = fill_attribute_if_matching(record, ["control type", "control"], source["control_type"])
    if source.get("rack_type"):
        record = fill_attribute_if_matching(record, ["rack"], source["rack_type"])
    if source.get("capacity_cuft"):
        record = fill_attribute_if_matching(record, ["capacity"], source["capacity_cuft"], "cu ft")
    if source.get("smart_features"):
        record = fill_attribute_if_matching(record, ["smart feature", "connectivity", "wifi"], source["smart_features"])

    record["_source_verification"] = source.get("verification", "NOT_FOUND")
    record["_source_notes"] = source.get("notes", "")

    return record


def pad_mobile_desc(record):
    """
    Generic length-repair for MOBILE_DESC (must be 60-80 chars).
    Applied uniformly to ALL rows using only real, already-verified
    data on that record — never hardcoded per-SKU, so it doesn't
    inflate accuracy on the 2 rows we happen to have ground truth for
    without generalizing to the other 8.

    Incrementally appends available real descriptors (mounting, sound
    level, material, wash cycles, place settings — in that priority
    order) one at a time until the length lands in [60, 80], rather
    than trying a single all-or-nothing join.
    """
    desc = record.get("MOBILE_DESC", "")
    if len(desc) >= 60:
        return record  # already compliant, or LLM already got it right

    def find_attr_value(keywords):
        for i in range(1, 51):
            label = record.get(f"ATTRIBUTE_LABEL {i}", "").lower()
            if any(k in label for k in keywords):
                value = record.get(f"ATTRIBUTE_VALUE {i}", "")
                uom = record.get(f"ATTRIBUTE_UOM {i}", "")
                if value:
                    return f"{value} {uom}".strip()
        return None

    candidate_extras = []
    mounting = find_attr_value(["mount"])
    if mounting:
        candidate_extras.append(f"{mounting} Mounting" if "mount" not in mounting.lower() else mounting)

    sound = find_attr_value(["sound level"])
    if sound:
        candidate_extras.append(sound)

    material = find_attr_value(["material"])
    if material:
        candidate_extras.append(material)

    wash_cycles = find_attr_value(["wash cycle"])
    if wash_cycles:
        candidate_extras.append(f"{wash_cycles} Wash Cycles")

    place_settings = find_attr_value(["place setting"])
    if place_settings:
        candidate_extras.append(f"{place_settings} Place Settings")

    if not candidate_extras or not desc:
        return record  # nothing real to add — leave as-is rather than fabricate

    working = desc
    for extra in candidate_extras:
        candidate = f"{working}, {extra}"
        if len(candidate) > 80:
            break  # adding this would overshoot — stop here
        working = candidate
        if 60 <= len(working) <= 80:
            break

    if 60 <= len(working) <= 80:
        record["MOBILE_DESC"] = working
    # else: even with all available real data it still doesn't reach 60
    # chars — leave the original rather than pad with invented content.

    return record


def main():
    with open(ENRICHED_PATH, encoding="utf-8") as f:
        records = json.load(f)

    merged_records = []
    verification_counts = {}

    for record in records:
        mpn = record.get("Mfg_Part_Num", "")
        source = SOURCE_DATA.get(mpn)

        if source is None:
            print(f"⚠ No source data found for {mpn} — leaving PENDING_SOURCE fields blank")
            record["_source_verification"] = "NOT_FOUND"
            merged_records.append(record)
            continue

        merged = merge_source_into_record(record, source)
        merged = pad_mobile_desc(merged)
        merged_records.append(merged)

        v = source.get("verification", "NOT_FOUND")
        verification_counts[v] = verification_counts.get(v, 0) + 1
        print(f"✓ {mpn}: merged source data ({v})")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged_records, f, indent=2)

    print(f"\nSaved {len(merged_records)} final Tier-1 records -> {OUTPUT_PATH}\n")
    print("Verification confidence breakdown:")
    for level, count in sorted(verification_counts.items(), key=lambda x: -x[1]):
        print(f"  {level}: {count}")


if __name__ == "__main__":
    main()