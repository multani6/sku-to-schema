import json

INPUT_FILE = "../raw_data/html/tier2_llm_enriched.json"
OUTPUT_FILE = "../raw_data/html/tier2_llm_enriched.json"  # same file overwrite

FIXES = {
    "ERFD19CGCS": {"MANUFACTURER_NAME": "Element Electronics", "BRAND_NAME": "Element"},
    "EUF17CDBW": {"MANUFACTURER_NAME": "Element Electronics", "BRAND_NAME": "Element"},
    "EUF21CDBW": {"MANUFACTURER_NAME": "Element Electronics", "BRAND_NAME": "Element"},
}

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    fixed_count = 0
    for row in data:
        mpn = row.get("Mfg_Part_Num", "")
        if mpn in FIXES:
            old_mfr = row.get("MANUFACTURER_NAME", "")
            old_brand = row.get("BRAND_NAME", "")
            row["MANUFACTURER_NAME"] = FIXES[mpn]["MANUFACTURER_NAME"]
            row["BRAND_NAME"] = FIXES[mpn]["BRAND_NAME"]
            row["_llm_confidence_notes"] = (
                f"MANUALLY CORRECTED: was '{old_brand}'/{old_mfr}, "
                f"fixed to Element after EUF/ER prefix-collision bug found via web verification"
            )
            fixed_count += 1
            print(f"Fixed {mpn}: {old_brand} -> Element")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nTotal fixed: {fixed_count}")
    print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()