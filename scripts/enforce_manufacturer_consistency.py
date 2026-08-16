"""
enforce_manufacturer_consistency.py
--------------------------------------
Reused as-is from Tier 1/2. Groups records by (normalized) brand, picks a
single canonical manufacturer per brand, and applies it consistently.
"""

import json
import re
import sys
import collections

DEFAULT_PATH = "raw_data/html/tier2_llm_enriched.json"

AUTHORITATIVE_BRAND_MANUFACTURER = {
    "speedqueen": "Alliance Laundry Systems",
    "frigidaire": "Electrolux",
    "kitchenaid": "Whirlpool Corporation",
    "whirlpool": "Whirlpool Corporation",
    "geprofile": "GE Appliances (Haier)",
    "gecafe": "GE Appliances (Haier)",
    "ge": "GE Appliances (Haier)",
    "lg": "LG Electronics",
}


def normalize_brand(brand):
    b = re.sub(r"[^a-z0-9]", "", str(brand).lower())
    return b


def pick_canonical_manufacturer(records_in_group, normalized_brand):
    if normalized_brand in AUTHORITATIVE_BRAND_MANUFACTURER:
        return AUTHORITATIVE_BRAND_MANUFACTURER[normalized_brand], "AUTHORITATIVE"

    high_conf_values = [
        r.get("MANUFACTURER_NAME", "").strip()
        for r in records_in_group
        if r.get("_llm_confidence") == "high" and r.get("MANUFACTURER_NAME", "").strip()
    ]
    all_values = [
        r.get("MANUFACTURER_NAME", "").strip()
        for r in records_in_group
        if r.get("MANUFACTURER_NAME", "").strip()
    ]

    pool = high_conf_values if high_conf_values else all_values
    if not pool:
        return None, None

    counts = collections.Counter(pool)
    return counts.most_common(1)[0][0], "MAJORITY_VOTE"


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH

    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    groups = collections.defaultdict(list)
    for r in records:
        brand = r.get("BRAND_NAME", "")
        if brand.strip():
            groups[normalize_brand(brand)].append(r)

    corrections = []

    for norm_brand, group in groups.items():
        if len(group) < 2 and norm_brand not in AUTHORITATIVE_BRAND_MANUFACTURER:
            continue

        canonical, method = pick_canonical_manufacturer(group, norm_brand)
        if canonical is None:
            continue

        for r in group:
            current = r.get("MANUFACTURER_NAME", "").strip()
            if current != canonical:
                corrections.append({
                    "mfg_part_num": r.get("Mfg_Part_Num", ""),
                    "brand": r.get("BRAND_NAME", ""),
                    "old_manufacturer": current,
                    "new_manufacturer": canonical,
                    "method": method,
                })
                r["MANUFACTURER_NAME"] = canonical

    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"Checked {len(records)} rows across {len(groups)} brand groups.")
    if corrections:
        print(f"Corrected {len(corrections)} manufacturer-name inconsistencies.")
    else:
        print("No inconsistencies found.")


if __name__ == "__main__":
    main()