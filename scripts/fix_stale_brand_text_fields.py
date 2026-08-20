"""
fix_stale_brand_text_fields.py
--------------------------------
apply_tier2_fixes.py corrected MFR URL / SOURCE_TYPE / MARKETING_DESCRIPTION /
BRAND_NAME / MANUFACTURER_NAME for 7 rows with confirmed brand-mismatch bugs.
It did NOT touch MOBILE_DESC, INVOICE_DESC, SHORT_DESC, LONG_DESC1, RETAIL_DESC
-- these were LLM-generated during enrich_tier2_llm.py against the OLD (wrong)
brand and still contain stale brand mentions.

This script does a targeted, scoped string replacement of the old brand
mention with the corrected brand, ONLY in those 5 text fields, ONLY for the
7 specific rows below. It does not touch any other row or field.

Run AFTER tier2_llm_enriched.json already has correct BRAND_NAME /
MANUFACTURER_NAME (i.e. after the FIXED file was swapped in and
enforce_manufacturer_consistency.py has been re-run).
"""

import json
import re
import sys

DEFAULT_PATH = "raw_data/html/tier2_llm_enriched.json"
TEXT_FIELDS = ["MOBILE_DESC", "INVOICE_DESC", "SHORT_DESC", "LONG_DESC1", "RETAIL_DESC"]

# mfg_part_num -> list of (old_brand_pattern_regex, new_brand_string)
# Ordered longest-match-first per row where relevant.
FIXES = {
    "TC5003BN": [
        (r"\bLG\b", "Speed Queen"),
    ],
    "XOU2470BCGS": [
        (r"\bGE Caf\u00e9\b", "XO Appliance"),
        (r"\bGE Cafe\b", "XO Appliance"),
        (r"\bGE\b", "XO Appliance"),
    ],
    "XOU24BCGSR": [
        (r"\bGE Caf\u00e9\b", "XO Appliance"),
        (r"\bGE Cafe\b", "XO Appliance"),
        (r"\bGE\b", "XO Appliance"),
    ],
    "XOU24WDZGBR": [
        (r"\bGE Caf\u00e9\b", "XO Appliance"),
        (r"\bGE Cafe\b", "XO Appliance"),
        (r"\bGE\b", "XO Appliance"),
    ],
    "SMC2266KS": [
        (r"\bSamsung\b", "Sharp"),
    ],
    "SLER30524SS": [
        (r"\bSamsung\b", "Beko"),
    ],
    "PMOS1980AF": [
        (r"\bGE\b", "Frigidaire Professional"),
    ],
}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH

    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    changed_rows = []

    for r in records:
        mpn = r.get("Mfg_Part_Num", "")
        if mpn not in FIXES:
            continue

        row_changes = []
        for field in TEXT_FIELDS:
            original = r.get(field, "")
            if not original:
                continue
            updated = original
            for pattern, replacement in FIXES[mpn]:
                updated = re.sub(pattern, replacement, updated)
            if updated != original:
                row_changes.append((field, original, updated))
                r[field] = updated

        if row_changes:
            changed_rows.append((mpn, row_changes))

    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Scanned {len(records)} rows, targeted {len(FIXES)} known-bug MPNs.")
    if changed_rows:
        print(f"Updated stale brand text in {len(changed_rows)} rows:")
        for mpn, changes in changed_rows:
            print(f"\n  {mpn}:")
            for field, old, new in changes:
                print(f"    {field}:")
                print(f"      OLD: {old}")
                print(f"      NEW: {new}")
    else:
        print("No stale brand mentions found in target fields (already clean, or MPNs not present in this file).")


if __name__ == "__main__":
    main()