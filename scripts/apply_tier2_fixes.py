"""
apply_tier2_fixes.py
---------------------
Applies Day 1 sourcing results (MFR URL, SOURCE_TYPE, MARKETING_DESCRIPTION,
and brand corrections for 6 confirmed bugs) onto the real Tier 2 dataset.

USAGE (run from your project root, e.g. C:\\Users\\shubm\\Downloads\\unihack-project):
    python apply_tier2_fixes.py

WHAT IT DOES:
  1. Reads raw_data/html/tier2_llm_enriched.json
  2. Reads tier2_sourced_data.json (put it in the same folder as this script,
     or pass a path as sys.argv[2])
  3. For every row whose Mfg_Part_Num matches a key in the sourced data:
       - sets "MFR URL"
       - adds/sets "SOURCE_TYPE"
       - sets a "MARKETING_DESCRIPTION" field (paraphrased, source-grounded)
       - if corrected_brand_name / corrected_manufacturer_name are present,
         OVERWRITES BRAND_NAME / MANUFACTURER_NAME (this is the 6 confirmed bugs)
  4. Writes the result to raw_data/html/tier2_llm_enriched_FIXED.json
     (does NOT overwrite your original file -- review then rename/replace yourself)
  5. Prints a summary: how many rows updated, how many brand-corrected, which
     rows had no match (should be 0 if run against the same 74-row file).

This does NOT touch enforce_manufacturer_consistency.py -- that's a separate,
smaller edit (see accompanying instructions).
"""

import json
import sys
from pathlib import Path

def main():
    project_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    sourced_data_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("tier2_sourced_data.json")

    tier2_path = project_root / "raw_data" / "html" / "tier2_llm_enriched.json"
    output_path = project_root / "raw_data" / "html" / "tier2_llm_enriched_FIXED.json"

    if not tier2_path.exists():
        print(f"ERROR: could not find {tier2_path}")
        print("Run this script from your project root, or pass the root as the first argument:")
        print(r'  python apply_tier2_fixes.py "C:\Users\shubm\Downloads\unihack-project"')
        sys.exit(1)

    if not sourced_data_path.exists():
        print(f"ERROR: could not find {sourced_data_path}")
        print("Make sure tier2_sourced_data.json is in the same folder as this script,")
        print("or pass its path as the second argument.")
        sys.exit(1)

    with open(tier2_path, "r", encoding="utf-8") as f:
        tier2_rows = json.load(f)

    with open(sourced_data_path, "r", encoding="utf-8") as f:
        sourced = json.load(f)["rows"]

    updated = 0
    brand_corrected = []
    flagged = []
    unmatched = []

    for row in tier2_rows:
        mpn = row.get("Mfg_Part_Num", "")
        if mpn not in sourced:
            unmatched.append(mpn)
            continue

        data = sourced[mpn]

        row["MFR URL"] = data.get("mfr_url", "")
        row["SOURCE_TYPE"] = data.get("source_type", "")
        row["MARKETING_DESCRIPTION"] = data.get("marketing_description", "")

        if "corrected_brand_name" in data:
            old_brand = row.get("BRAND_NAME", "")
            old_mfr = row.get("MANUFACTURER_NAME", "")
            row["BRAND_NAME"] = data["corrected_brand_name"]
            row["MANUFACTURER_NAME"] = data["corrected_manufacturer_name"]
            brand_corrected.append({
                "mpn": mpn,
                "old_brand": old_brand,
                "old_manufacturer": old_mfr,
                "new_brand": data["corrected_brand_name"],
                "new_manufacturer": data["corrected_manufacturer_name"],
                "note": data.get("bug_note", "")
            })

        if "flag_note" in data:
            flagged.append({"mpn": mpn, "note": data["flag_note"]})

        updated += 1

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tier2_rows, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("TIER 2 FIX APPLICATION -- SUMMARY")
    print("=" * 60)
    print(f"Rows updated with URL/SOURCE_TYPE/description: {updated}")
    print(f"Output written to: {output_path}")
    print()
    print(f"BRAND CORRECTIONS APPLIED: {len(brand_corrected)}")
    for b in brand_corrected:
        print(f"  - {b['mpn']}: '{b['old_brand']}' -> '{b['new_brand']}'  ({b['note']})")
    print()
    print(f"FLAGGED FOR MANUAL REVIEW (non-blocking): {len(flagged)}")
    for fl in flagged:
        print(f"  - {fl['mpn']}: {fl['note']}")
    print()
    if unmatched:
        print(f"ROWS WITH NO SOURCED DATA (not in the 74 verified rows): {len(unmatched)}")
        for u in unmatched[:20]:
            print(f"  - {u}")
        if len(unmatched) > 20:
            print(f"  ... and {len(unmatched) - 20} more")
    else:
        print("All rows in tier2_llm_enriched.json were matched. Nothing missed.")
    print("=" * 60)
    print()
    print("NEXT STEP: review tier2_llm_enriched_FIXED.json, then replace the")
    print("original file (or update your pipeline to read the _FIXED version),")
    print("and re-run export_tier2_csv.py to regenerate the final CSV.")

if __name__ == "__main__":
    main()