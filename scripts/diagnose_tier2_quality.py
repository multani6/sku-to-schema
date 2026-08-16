"""
diagnose_tier2_quality.py
----------------------------
Quick sanity check on the 74 Tier-2 enriched rows: confidence
breakdown, manufacturer-identification spot-check (did the LLM avoid
echoing the Part_Manuf distributor code?), and a few sample records
printed for a human eyeball check — without dumping all 74 full
records.

Run: python scripts/diagnose_tier2_quality.py
"""

import json
import collections

ENRICHED_PATH = "raw_data/html/tier2_llm_enriched.json"
CATEGORY_MAP_PATH = "raw_data/html/tier2_category_map.json"

DISTRIBUTOR_NAMES = {"appliance dealers cooperative", "appde"}


def main():
    with open(ENRICHED_PATH, encoding="utf-8") as f:
        records = json.load(f)
    with open(CATEGORY_MAP_PATH, encoding="utf-8") as f:
        category_map = json.load(f)

    print(f"Total rows: {len(records)}\n")

    # --- Confidence breakdown ---
    confidence_counts = collections.Counter(
        r.get("_llm_confidence", "unknown") for r in records
    )
    print("Confidence breakdown:")
    for level, count in confidence_counts.most_common():
        print(f"  {level}: {count}")

    # --- Manufacturer/distributor confusion check ---
    confused = []
    for r in records:
        mfr = r.get("MANUFACTURER_NAME", "").lower()
        brand = r.get("BRAND_NAME", "").lower()
        if any(d in mfr for d in DISTRIBUTOR_NAMES) or any(d in brand for d in DISTRIBUTOR_NAMES):
            confused.append(r.get("Mfg_Part_Num", ""))

    print(f"\nDistributor/manufacturer confusion check: {len(confused)}/{len(records)} rows affected")
    if confused:
        print(f"  Affected MPNs: {', '.join(confused)}")
    else:
        print("  ✓ Clean — no row echoed the distributor code as the manufacturer")

    # --- Empty manufacturer/brand check (LLM correctly abstained) ---
    empty_mfr = sum(1 for r in records if not r.get("MANUFACTURER_NAME", "").strip())
    print(f"\nRows where LLM left manufacturer blank (uncertain, didn't guess): {empty_mfr}/{len(records)}")

    # --- Category coverage sanity check ---
    categories_seen = collections.Counter(category_map.values())
    print(f"\nCategories covered: {len(categories_seen)}")

    # --- A few sample records for eyeballing ---
    print("\n--- Sample records (first 3) ---")
    for r in records[:3]:
        print(f"\n{r.get('Mfg_Part_Num')} | {r.get('Product Name')}")
        print(f"  Manufacturer: {r.get('MANUFACTURER_NAME')} | Brand: {r.get('BRAND_NAME')}")
        print(f"  Invoice: {r.get('INVOICE_DESC')}")
        print(f"  Mobile:  {r.get('MOBILE_DESC')}")
        attrs = [
            (r.get(f"ATTRIBUTE_LABEL {i}"), r.get(f"ATTRIBUTE_VALUE {i}"), r.get(f"ATTRIBUTE_UOM {i}"))
            for i in range(1, 6) if r.get(f"ATTRIBUTE_LABEL {i}")
        ]
        print(f"  Sample attributes: {attrs}")


if __name__ == "__main__":
    main()