"""
build_tier1_skeleton.py
------------------------
Builds the first-pass skeleton for the 10 Tier-1 (Dishwasher) rows,
mapping the 252-column schema and classifying every field by how it
will eventually get filled:

  - DIRECT_PASSTHROUGH   : copied straight from the raw input row
  - RULE_DERIVED         : computed by a simple rule (e.g. same as MPN)
  - NOT_DERIVABLE        : an internal Unilog-assigned ID we cannot
                            invent (e.g. PART_NUMBER, SKU) — flagged
                            honestly instead of fabricated
  - PENDING_LLM          : needs GenAI research/generation (descriptions,
                            attributes, classification, features)
  - PENDING_SOURCE       : needs manufacturer-site lookup (images, docs,
                            warranty, spec sheets)

This gives us a concrete, defensible breakdown of "what % of the
schema is rule-based vs. what % genuinely needs AI" — a metric worth
showing judges directly.

Input:  schema/schema_map.json
        raw_data/html/tier1_dishwashers.json
Output: raw_data/html/tier1_skeleton.json

Run:    python scripts/build_tier1_skeleton.py
"""

import json
import os

SCHEMA_PATH = "schema/schema_map.json"
TIER1_PATH = "raw_data/html/tier1_dishwashers.json"
OUTPUT_PATH = "raw_data/html/tier1_skeleton.json"

NOT_DERIVABLE_FIELDS = {
    "PART_NUMBER": "Internal Unilog system-assigned ID — cannot be derived from product content",
    "SKU - MY_PART_NUMBER": "Internal Unilog system-assigned SKU — cannot be derived from product content",
}

# Tier-1-specific rule: every Tier 1 row IS a dishwasher by construction,
# so taxonomy is deterministic — no LLM call needed, zero misclassification risk.
TIER1_TAXONOMY_RULE = {
    "Dept": "Appliances",
    "Class": "Large Appliances",
    "Fine": "Dishwashers",
    "Classpath": "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
}

# Fields that are a direct rule (not a raw copy, not requiring LLM)
RULE_DERIVED_MAP = {
    "MANUFACTURER_PART_NUMBER": "Mfg_Part_Num",  # same value as Mfg_Part_Num
}

PASSTHROUGH_FIELDS = [
    "Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf",
]

# Everything in these schema groups needs GenAI research/generation
LLM_GROUPS = [
    "manufacturer_brand", "descriptions", "features_and_misc", "attributes",
]

# Everything in these schema groups needs manufacturer-source lookup
# (identifiers here only catches ALTERNATE_PART_NUMBER, since PART_NUMBER,
# SKU, Mfg_Part_Num, and MANUFACTURER_PART_NUMBER are already handled above)
SOURCE_GROUPS = [
    "sourcing", "images_docs_compliance", "product_ids", "dimensions",
    "identifiers", "commercial",
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def classify_field(col, schema_groups):
    if col in PASSTHROUGH_FIELDS:
        return "DIRECT_PASSTHROUGH"
    if col in NOT_DERIVABLE_FIELDS:
        return "NOT_DERIVABLE"
    if col in RULE_DERIVED_MAP or col in TIER1_TAXONOMY_RULE:
        return "RULE_DERIVED"
    for group_name in LLM_GROUPS:
        if col in schema_groups.get(group_name, []):
            return "PENDING_LLM"
    for group_name in SOURCE_GROUPS:
        if col in schema_groups.get(group_name, []):
            return "PENDING_SOURCE"
    return "UNCLASSIFIED"  # should not happen if schema_map is complete


def build_record(input_row, column_order, schema_groups):
    record = {}
    status = {}

    for col in column_order:
        field_status = classify_field(col, schema_groups)
        status[col] = field_status

        if field_status == "DIRECT_PASSTHROUGH":
            record[col] = input_row.get(col, "")
        elif field_status == "RULE_DERIVED":
            if col in TIER1_TAXONOMY_RULE:
                record[col] = TIER1_TAXONOMY_RULE[col]
            else:
                source_col = RULE_DERIVED_MAP[col]
                record[col] = input_row.get(source_col, "")
        elif field_status == "NOT_DERIVABLE":
            record[col] = f"N/A — {NOT_DERIVABLE_FIELDS[col]}"
        else:
            # PENDING_LLM / PENDING_SOURCE — left blank for the next step
            record[col] = ""

    return record, status


def main():
    schema = load_json(SCHEMA_PATH)
    column_order = schema["column_order"]
    schema_groups = schema["groups"]

    tier1_rows = load_json(TIER1_PATH)

    skeletons = []
    status_summary = {}

    for row in tier1_rows:
        record, status = build_record(row, column_order, schema_groups)
        skeletons.append(record)
        for col, s in status.items():
            status_summary.setdefault(s, set()).add(col)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(skeletons, f, indent=2)

    print(f"Built skeleton for {len(skeletons)} Tier-1 rows -> {OUTPUT_PATH}\n")
    print("Field status breakdown (out of 252 columns):")
    for status_name, cols in sorted(status_summary.items(), key=lambda x: -len(x[1])):
        pct = len(cols) / len(column_order) * 100
        print(f"  {status_name:20s}: {len(cols):3d} columns ({pct:5.1f}%)")


if __name__ == "__main__":
    main()