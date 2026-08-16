"""
sample_for_manual_verification.py
--------------------------------------
Samples rows from Tier 1 + Tier 2 for manual ground-truth verification.
Produces a simple CSV that's easy to fill in by hand (or in Excel/Sheets)
while checking each row's MPN online (manufacturer's own site, or a
retailer listing) to confirm whether the enrichment is actually correct.

This builds a real, defensible accuracy number -- not just the 2 official
worked examples -- for the pitch and for Q&A.

Run:
  python scripts/sample_for_manual_verification.py
"""

import json
import random
import csv
import os

TIER1_PATH = "raw_data/html/tier1_llm_enriched.json"
TIER2_PATH = "raw_data/html/tier2_llm_enriched.json"
OUTPUT_PATH = "outputs/manual_verification_worksheet.csv"

SAMPLE_SIZE_TIER1 = 10   # all of Tier 1 (only 10 rows total anyway)
SAMPLE_SIZE_TIER2 = 25   # random sample of Tier 2

RANDOM_SEED = 42  # fixed seed so the sample is reproducible if reviewers ask


def load_json(path):
    if not os.path.exists(path):
        print(f"⚠️  Not found: {path}")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    random.seed(RANDOM_SEED)

    tier1 = load_json(TIER1_PATH)
    tier2 = load_json(TIER2_PATH)

    tier1_sample = tier1[:SAMPLE_SIZE_TIER1]  # take all 10
    tier2_sample = random.sample(tier2, min(SAMPLE_SIZE_TIER2, len(tier2)))

    all_samples = [("Tier 1", r) for r in tier1_sample] + [("Tier 2", r) for r in tier2_sample]

    rows_out = []
    for tier_name, r in all_samples:
        rows_out.append({
            "Tier": tier_name,
            "Mfg_Part_Num": r.get("Mfg_Part_Num", ""),
            "Part_Desc (raw input)": r.get("Part_Desc", ""),
            "LLM Manufacturer": r.get("MANUFACTURER_NAME", ""),
            "LLM Brand": r.get("BRAND_NAME", ""),
            "LLM Short Desc": r.get("SHORT_DESC", ""),
            "LLM Confidence": r.get("_llm_confidence", ""),
            # --- Columns for YOU to fill in by hand, one row at a time ---
            "Manufacturer_Correct? (Y/N)": "",
            "Brand_Correct? (Y/N)": "",
            "Description_Accurate? (Y/N)": "",
            "Verification_Source (URL or note)": "",
            "Notes": "",
        })

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        fieldnames = list(rows_out[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Sampled {len(tier1_sample)} rows from Tier 1 (all of it)")
    print(f"Sampled {len(tier2_sample)} rows from Tier 2 (random, seed={RANDOM_SEED})")
    print(f"Total rows to verify: {len(rows_out)}")
    print(f"\nSaved worksheet: {OUTPUT_PATH}")
    print("\nNext: open this CSV in Excel/Google Sheets and fill in the")
    print("Y/N and Notes columns for each row, one at a time.")


if __name__ == "__main__":
    main()