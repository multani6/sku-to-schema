"""
segment_categories.py
----------------------
Segments the Unihack Sample Dataset (Input) into 3 tiers for the
tiered-depth enrichment strategy:

Tier 1 (Anchor - Full Depth):        Exact "Dishwasher" matches
Tier 2 (Family Expansion - Medium):  Other Major Appliances from the
                                      same manufacturer group (dryer,
                                      washer, fridge, range/oven, microwave)
Tier 3 (Scale Layer - Light):        Everything else (lighting, tools,
                                      abrasives, building materials, etc.)

Input:  raw_data/html/Unihack__Sample_Dataset_-_Input.csv
Output: raw_data/html/tier1_dishwashers.json
        raw_data/html/tier2_major_appliances.json
        raw_data/html/tier3_general_catalog.json

Run:    python scripts/segment_categories.py
"""

import csv
import json
import os

INPUT_PATH = "raw_data/html/Unihack__Sample_Dataset_-_Input.csv"
OUTPUT_DIR = "raw_data/html"

# Manufacturer code(s) that represent the "Major Appliances" family in
# this sample dataset. Extend this list if you spot more appliance
# manufacturers when you inspect the full 1000-row set yourself.
APPLIANCE_MANUFACTURER_KEYWORDS = ["APPDE"]

# Keywords that identify a Tier-2 "major appliance" item once we're
# already inside an appliance-manufacturer row.
APPLIANCE_KEYWORDS = [
    "dishwasher", "dryer", "washer", "fridge", "refrig",
    "range", "oven", "microwave", "mocrowave", "laundry",
    "beverage center", "coffee maker", "espresso", "cooktop",
    "toaster", "freezer",
]


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def is_appliance_manufacturer(part_manuf: str) -> bool:
    return any(code in part_manuf for code in APPLIANCE_MANUFACTURER_KEYWORDS)


def classify(row: dict) -> str:
    """Returns 'tier1', 'tier2', or 'tier3' for a given input row."""
    desc = row.get("Part_Desc", "").lower()
    manuf = row.get("Part_Manuf", "")

    if "dishwasher" in desc:
        return "tier1"

    if is_appliance_manufacturer(manuf) and any(kw in desc for kw in APPLIANCE_KEYWORDS):
        return "tier2"

    return "tier3"


def main():
    rows = load_rows(INPUT_PATH)

    tier1, tier2, tier3 = [], [], []

    for row in rows:
        tier = classify(row)
        if tier == "tier1":
            tier1.append(row)
        elif tier == "tier2":
            tier2.append(row)
        else:
            tier3.append(row)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(os.path.join(OUTPUT_DIR, "tier1_dishwashers.json"), "w", encoding="utf-8") as f:
        json.dump(tier1, f, indent=2)

    with open(os.path.join(OUTPUT_DIR, "tier2_major_appliances.json"), "w", encoding="utf-8") as f:
        json.dump(tier2, f, indent=2)

    with open(os.path.join(OUTPUT_DIR, "tier3_general_catalog.json"), "w", encoding="utf-8") as f:
        json.dump(tier3, f, indent=2)

    print(f"Total input rows: {len(rows)}")
    print(f"Tier 1 (Dishwashers - Full Depth):        {len(tier1)} rows")
    print(f"Tier 2 (Major Appliances - Medium Depth): {len(tier2)} rows")
    print(f"Tier 3 (General Catalog - Light Depth):   {len(tier3)} rows")
    print()
    print("Saved to:")
    print(f"  {OUTPUT_DIR}/tier1_dishwashers.json")
    print(f"  {OUTPUT_DIR}/tier2_major_appliances.json")
    print(f"  {OUTPUT_DIR}/tier3_general_catalog.json")


if __name__ == "__main__":
    main()
