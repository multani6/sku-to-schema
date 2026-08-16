"""
build_schema_map.py
--------------------
Reads the official 252-column Expected Output header row and builds a
reusable, logically-grouped schema map (schema/schema_map.json).

This map is the single source of truth used by every tier's enrichment
script (Tier 1 dishwashers, Tier 2 major appliances, Tier 3 general
catalog) — same structure, different depth per tier.

Input:  raw_data/html/Unihack__Expected_Output_-_Delivery_Format.csv
Output: schema/schema_map.json

Run:    python scripts/build_schema_map.py
"""

import csv
import json
import os

INPUT_PATH = "raw_data/html/Unihack__Expected_Output_-_Delivery_Format.csv"
OUTPUT_PATH = "schema/schema_map.json"

# ---- Explicit column groups (order-preserving, non-attribute fields) ----

SOURCING = ["MFR URL", "Ref URL 1", "Ref URL 2", "Ref URL 3", "Ref URL 4", "Ref URL 5"]

IDENTIFIERS = [
    "PART_NUMBER", "SKU - MY_PART_NUMBER", "Mfg_Part_Num",
    "MANUFACTURER_PART_NUMBER", "ALTERNATE_PART_NUMBER",
]

TAXONOMY = ["Dept", "Class", "Fine", "Classpath"]

RAW_INPUT_PASSTHROUGH = [
    "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf",
]

MANUFACTURER_BRAND = ["MANUFACTURER_NAME", "BRAND_NAME", "TRADE_NAME"]

DESCRIPTIONS = [
    "MOBILE_DESC", "INVOICE_DESC", "SHORT_DESC", "LONG_DESC1",
    "RETAIL_DESC", "MARKETING_DESCRIPTION",
]

FEATURES_AND_MISC = [f"ITEM_FEATURES_{i}" for i in range(1, 21)] + [
    "With", "Standard/Approvals", "Prop 65", "Application", "Includes", "Product Name",
]

PRODUCT_IDS = ["UPC", "EAN", "GTIN", "UNSPSC"]

COMMERCIAL = [
    "Warranty", "List Price", "Selling Qty", "Selling UOM",
    "Standard Packaging Information",
]

DIMENSIONS = [
    "LENGTH", "LENGTH_UOM", "HEIGHT", "HEIGHT_UOM", "WIDTH", "WIDTH_UOM",
    "WEIGHT", "WEIGHT_UOM", "VOLUME", "VOLUME_UOM",
]

IMAGES_DOCS_COMPLIANCE = [
    "Product Image", "Alternate Image 1", "Alternate Image 2",
    "Alternate Image 3", "Alternate Image 4", "SDS", "SDS_1",
    "Warranty Information", "Catalog", "Specification Sheet",
    "Instruction/Installation Manual", "Service Manual",
    "Owners/User Manual", "Line Drawing", "MTR", "RoHS",
    "Full Engineering Drawing", "Energy Star Guide", "Technical Bulletin",
    "Submittal", "Compatibility Chart", "Size Chart",
    "Product Label/Insert", "Video Link", "Video Link 1",
    "Country Of Origin", "Discontinued", "Actual Image (Yes/No)",
]

# Attributes are generated programmatically: 50 x (LABEL, VALUE, UOM)
def build_attribute_columns():
    cols = []
    for i in range(1, 51):
        cols.append(f"ATTRIBUTE_LABEL {i}")
        cols.append(f"ATTRIBUTE_VALUE {i}")
        cols.append(f"ATTRIBUTE_UOM {i}")
    return cols


def load_header(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return next(reader)


def main():
    header = load_header(INPUT_PATH)
    header_set = set(header)

    groups = {
        "sourcing": SOURCING,
        "identifiers": IDENTIFIERS,
        "taxonomy": TAXONOMY,
        "raw_input_passthrough": RAW_INPUT_PASSTHROUGH,
        "manufacturer_brand": MANUFACTURER_BRAND,
        "descriptions": DESCRIPTIONS,
        "features_and_misc": FEATURES_AND_MISC,
        "attributes": build_attribute_columns(),
        "product_ids": PRODUCT_IDS,
        "commercial": COMMERCIAL,
        "dimensions": DIMENSIONS,
        "images_docs_compliance": IMAGES_DOCS_COMPLIANCE,
    }

    # --- Validation: every header column must appear in exactly one group,
    # and every group column must actually exist in the real header. ---
    all_grouped = [col for cols in groups.values() for col in cols]

    missing_from_header = [c for c in all_grouped if c not in header_set]
    missing_from_groups = [c for c in header if c not in all_grouped]
    duplicates = [c for c in set(all_grouped) if all_grouped.count(c) > 1]

    print(f"Total columns in official header: {len(header)}")
    print(f"Total columns captured in groups:  {len(all_grouped)}")

    if missing_from_header:
        print("\n⚠ Columns in groups but NOT in official header (check spelling):")
        for c in missing_from_header:
            print(" ", c)

    if missing_from_groups:
        print("\n⚠ Columns in official header but NOT grouped yet:")
        for c in missing_from_groups:
            print(" ", c)

    if duplicates:
        print("\n⚠ Columns grouped more than once:")
        for c in duplicates:
            print(" ", c)

    if not (missing_from_header or missing_from_groups or duplicates):
        print("\n✅ All 252 columns accounted for, no duplicates, no mismatches.")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_columns": len(header),
                "column_order": header,
                "groups": groups,
            },
            f,
            indent=2,
        )

    print(f"\nSaved schema map to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()