"""
export_tier1_csv.py
----------------------
Exports the final Tier-1 (Dishwasher) records as a real, submittable
CSV file — with the exact 252 column headers and order from Unilog's
official Expected Output - Delivery Format file (headers untouched,
as required).

This is the first tangible, official-format deliverable artifact.

Input:  schema/schema_map.json          (for the exact column order)
        raw_data/html/tier1_final.json  (the enriched + source-merged records)
Output: raw_data/html/tier1_output.csv

Run:    python scripts/export_tier1_csv.py
"""

import json
import csv

SCHEMA_PATH = "schema/schema_map.json"
FINAL_PATH = "raw_data/html/tier1_final.json"
OUTPUT_PATH = "raw_data/html/tier1_output.csv"

# Internal-only fields we tag records with for our own transparency —
# these are NOT part of the official 252-column schema and must be
# excluded from the submittable CSV.
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

    # Quick completeness check: how many of the 252 fields are non-empty
    # on average across these rows — a simple, honest fill-rate metric.
    total_cells = len(records) * len(column_order)
    filled_cells = sum(
        1 for record in records for col in column_order if str(record.get(col, "")).strip()
    )
    fill_rate = filled_cells / total_cells * 100 if total_cells else 0
    print(f"Overall field fill rate: {filled_cells}/{total_cells} ({fill_rate:.1f}%)")


if __name__ == "__main__":
    main()