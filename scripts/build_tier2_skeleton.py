"""
build_tier2_skeleton.py
--------------------------
Tier 2 = the 74 other Major Appliance rows (dryers, washers, fridges,
ranges/ovens, microwaves, beverage centers, coffee makers, espresso
machines, cooktops, toasters, freezers).

Unlike Tier 1 (where every row was a dishwasher, so taxonomy was a
single hardcoded constant), Tier 2 needs a per-row category classifier
since it spans 11 different appliance sub-types. This is the key
generalization test: does the same architecture hold up across a wider
category mix?

Input:  schema/schema_map.json
        raw_data/html/tier2_major_appliances.json
Output: raw_data/html/tier2_skeleton.json
        raw_data/html/tier2_category_map.json  (for transparency/debugging)

Run:    python scripts/build_tier2_skeleton.py
"""

import json
import os
import re

SCHEMA_PATH = "schema/schema_map.json"
TIER2_PATH = "raw_data/html/tier2_major_appliances.json"
SKELETON_OUTPUT_PATH = "raw_data/html/tier2_skeleton.json"
CATEGORY_MAP_OUTPUT_PATH = "raw_data/html/tier2_category_map.json"

NOT_DERIVABLE_FIELDS = {
    "PART_NUMBER": "Internal Unilog system-assigned ID — cannot be derived from product content",
    "SKU - MY_PART_NUMBER": "Internal Unilog system-assigned SKU — cannot be derived from product content",
}

RULE_DERIVED_MAP = {
    "MANUFACTURER_PART_NUMBER": "Mfg_Part_Num",
}

PASSTHROUGH_FIELDS = [
    "Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf",
]

# Per-category taxonomy — each category maps to (Dept, Class, Fine, Classpath).
# Dept/Class are shared across all Major Appliances; Fine/Classpath vary.
CATEGORY_TAXONOMY = {
    "dryer": ("Appliances", "Large Appliances", "Clothes Dryers",
              "Appliances & Consumer Electronics>Laundry Appliances>Clothes Dryers"),
    "washer": ("Appliances", "Large Appliances", "Clothes Washers",
               "Appliances & Consumer Electronics>Laundry Appliances>Clothes Washers"),
    "laundry center": ("Appliances", "Large Appliances", "Laundry Centers",
                        "Appliances & Consumer Electronics>Laundry Appliances>Laundry Centers"),
    "fridge": ("Appliances", "Large Appliances", "Refrigerators",
               "Appliances & Consumer Electronics>Kitchen Appliances>Refrigerators"),
    "refrig": ("Appliances", "Large Appliances", "Refrigerators",
               "Appliances & Consumer Electronics>Kitchen Appliances>Refrigerators"),
    "range": ("Appliances", "Large Appliances", "Ranges",
              "Appliances & Consumer Electronics>Kitchen Appliances>Ranges"),
    "oven": ("Appliances", "Large Appliances", "Ovens",
             "Appliances & Consumer Electronics>Kitchen Appliances>Ovens"),
    "cooktop": ("Appliances", "Large Appliances", "Cooktops",
                "Appliances & Consumer Electronics>Kitchen Appliances>Cooktops"),
    "microwave": ("Appliances", "Small Appliances", "Microwave Ovens",
                  "Appliances & Consumer Electronics>Kitchen Appliances>Microwave Ovens"),
    "mocrowave": ("Appliances", "Small Appliances", "Microwave Ovens",
                  "Appliances & Consumer Electronics>Kitchen Appliances>Microwave Ovens"),
    "beverage center": ("Appliances", "Small Appliances", "Beverage Centers",
                         "Appliances & Consumer Electronics>Kitchen Appliances>Beverage Centers"),
    "coffee maker": ("Appliances", "Small Appliances", "Coffee Makers",
                      "Appliances & Consumer Electronics>Kitchen Appliances>Coffee Makers"),
    "espresso": ("Appliances", "Small Appliances", "Espresso Machines",
                 "Appliances & Consumer Electronics>Kitchen Appliances>Espresso Machines"),
    "toaster": ("Appliances", "Small Appliances", "Toasters",
                "Appliances & Consumer Electronics>Kitchen Appliances>Toasters"),
    "freezer": ("Appliances", "Large Appliances", "Freezers",
                "Appliances & Consumer Electronics>Kitchen Appliances>Freezers"),
}

# Order matters: check more specific terms before generic ones
CATEGORY_KEYWORD_ORDER = [
    "laundry center", "beverage center", "coffee maker", "espresso",
    "toaster", "cooktop", "mocrowave", "microwave", "freezer",
    "dryer", "washer", "fridge", "refrig", "range", "oven",
]


def classify_category(part_desc):
    desc = part_desc.lower()
    for keyword in CATEGORY_KEYWORD_ORDER:
        if keyword in desc:
            return keyword
    return None


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def classify_field(col, schema_groups, category):
    if col in PASSTHROUGH_FIELDS:
        return "DIRECT_PASSTHROUGH"
    if col in NOT_DERIVABLE_FIELDS:
        return "NOT_DERIVABLE"
    if col in RULE_DERIVED_MAP:
        return "RULE_DERIVED"
    if col in ["Dept", "Class", "Fine", "Classpath"] and category is not None:
        return "RULE_DERIVED"

    LLM_GROUPS = ["manufacturer_brand", "descriptions", "features_and_misc", "attributes"]
    SOURCE_GROUPS = [
        "sourcing", "images_docs_compliance", "product_ids", "dimensions",
        "identifiers", "commercial",
    ]
    for group_name in LLM_GROUPS:
        if col in schema_groups.get(group_name, []):
            return "PENDING_LLM"
    for group_name in SOURCE_GROUPS:
        if col in schema_groups.get(group_name, []):
            return "PENDING_SOURCE"
    if col in ["Dept", "Class", "Fine", "Classpath"]:
        return "PENDING_LLM"  # category unknown — let LLM take a best guess, flagged low-confidence
    return "UNCLASSIFIED"


def build_record(input_row, column_order, schema_groups, category):
    record = {}

    for col in column_order:
        field_status = classify_field(col, schema_groups, category)

        if field_status == "DIRECT_PASSTHROUGH":
            record[col] = input_row.get(col, "")
        elif field_status == "RULE_DERIVED":
            if col in ["Dept", "Class", "Fine", "Classpath"]:
                taxonomy = CATEGORY_TAXONOMY.get(category)
                idx = ["Dept", "Class", "Fine", "Classpath"].index(col)
                record[col] = taxonomy[idx] if taxonomy else ""
            else:
                source_col = RULE_DERIVED_MAP[col]
                record[col] = input_row.get(source_col, "")
        elif field_status == "NOT_DERIVABLE":
            record[col] = f"N/A — {NOT_DERIVABLE_FIELDS[col]}"
        else:
            record[col] = ""

    return record


def main():
    schema = load_json(SCHEMA_PATH)
    column_order = schema["column_order"]
    schema_groups = schema["groups"]

    tier2_rows = load_json(TIER2_PATH)

    skeletons = []
    category_map = {}
    unclassified_count = 0

    for row in tier2_rows:
        mpn = row.get("Mfg_Part_Num", "")
        category = classify_category(row.get("Part_Desc", ""))
        category_map[mpn] = category if category else "UNCLASSIFIED"
        if category is None:
            unclassified_count += 1

        record = build_record(row, column_order, schema_groups, category)
        skeletons.append(record)

    os.makedirs(os.path.dirname(SKELETON_OUTPUT_PATH), exist_ok=True)
    with open(SKELETON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(skeletons, f, indent=2)
    with open(CATEGORY_MAP_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(category_map, f, indent=2)

    print(f"Built skeleton for {len(skeletons)} Tier-2 rows -> {SKELETON_OUTPUT_PATH}\n")

    import collections
    counts = collections.Counter(category_map.values())
    print("Category breakdown:")
    for cat, count in counts.most_common():
        print(f"  {cat}: {count}")

    if unclassified_count:
        print(f"\n⚠ {unclassified_count} rows could not be auto-classified — "
              f"see tier2_category_map.json for which ones")


if __name__ == "__main__":
    main()