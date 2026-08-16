"""
export_tier2_csv.py
----------------------
Exports the 74 Tier-2 (Major Appliance) records as a CSV matching the
official 252-column schema — same approach as Tier 1's exporter.

Input:  schema/schema_map.json
        raw_data/html/tier2_llm_enriched.json
Output: raw_data/html/tier2_output.csv

Run:    python scripts/export_tier2_csv.py
"""

import json
import csv

SCHEMA_PATH = "schema/schema_map.json"
FINAL_PATH = "raw_data/html/tier2_llm_enriched.json"
OUTPUT_PATH = "raw_data/html/tier2_output.csv"

INTERNAL_FIELDS = {
    "_llm_confidence", "_llm_confidence_notes",
    "_source_verification", "_source_notes",
}


def main():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    column_order = schema["column_order"]

    with open(FINAL_PATH, encoding="utf-8") as f:
        records = json.load(f)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=column_order, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            clean_record = {k: v for k, v in record.items() if k not in INTERNAL_FIELDS}
            writer.writerow(clean_record)

    print(f"Exported {len(records)} rows x {len(column_order)} columns -> {OUTPUT_PATH}")

    total_cells = len(records) * len(column_order)
    filled_cells = sum(
        1 for record in records for col in column_order if str(record.get(col, "")).strip()
    )
    fill_rate = filled_cells / total_cells * 100 if total_cells else 0
    print(f"Overall field fill rate: {filled_cells}/{total_cells} ({fill_rate:.1f}%)")


if __name__ == "__main__":
    main()