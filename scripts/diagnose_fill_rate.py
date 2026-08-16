"""
diagnose_fill_rate.py
------------------------
Breaks down the Tier-1 field fill-rate by schema group, so we know
exactly which parts of the 252-column schema still need work and can
prioritize the remaining build days accordingly — rather than treating
"20% filled" as one undifferentiated number.

Input:  schema/schema_map.json
        raw_data/html/tier1_final.json
Run:    python scripts/diagnose_fill_rate.py
"""

import json

SCHEMA_PATH = "schema/schema_map.json"
FINAL_PATH = "raw_data/html/tier1_final.json"


def main():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    groups = schema["groups"]

    with open(FINAL_PATH, encoding="utf-8") as f:
        records = json.load(f)

    print(f"Fill rate by schema group (across {len(records)} rows):\n")

    for group_name, columns in groups.items():
        total_cells = len(records) * len(columns)
        filled_cells = sum(
            1 for record in records for col in columns if str(record.get(col, "")).strip()
        )
        pct = filled_cells / total_cells * 100 if total_cells else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {group_name:26s} {bar} {pct:5.1f}%  ({filled_cells}/{total_cells})")

    print("\nPer-row attribute count (out of 50 possible slots):")
    for record in records:
        mpn = record.get("Mfg_Part_Num", "")
        filled_attrs = sum(
            1 for i in range(1, 51) if str(record.get(f"ATTRIBUTE_LABEL {i}", "")).strip()
        )
        print(f"  {mpn}: {filled_attrs}/50 attributes populated")


if __name__ == "__main__":
    main()