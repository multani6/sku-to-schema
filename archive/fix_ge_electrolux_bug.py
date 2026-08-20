import json

INPUT_FILE = "../raw_data/html/tier1_llm_enriched.json"
OUTPUT_FILE = "../raw_data/html/tier1_llm_enriched.json"  # same file overwrite

FIXES = {
    "PDT715SYVFS": {"MANUFACTURER_NAME": "GE Appliances (Haier)"},
    "PDD415PYYFS": {"MANUFACTURER_NAME": "GE Appliances (Haier)"},
}

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    fixed_count = 0
    for row in data:
        mpn = row.get("Mfg_Part_Num", "")
        if mpn in FIXES:
            old_mfr = row.get("MANUFACTURER_NAME", "")
            row["MANUFACTURER_NAME"] = FIXES[mpn]["MANUFACTURER_NAME"]
            row["_llm_confidence_notes"] = (
                f"MANUALLY CORRECTED: was '{old_mfr}', fixed to 'GE Appliances (Haier)' "
                f"after PD-prefix collision bug found via web verification "
                f"(GE brand was incorrectly assigned Electrolux as manufacturer; "
                f"GE Appliances has been owned by Haier since 2016, not Electrolux)"
            )
            fixed_count += 1
            print(f"Fixed {mpn}: {old_mfr} -> GE Appliances (Haier)")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nTotal fixed: {fixed_count}")
    print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()