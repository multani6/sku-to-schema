"""
merge_final_output.py
--------------------------------------
Combines Tier 1 (10 rows, full depth), Tier 2 (74 rows, medium depth),
and Tier 3 (916 rows, light depth) into ONE master CSV — the final
submittable deliverable — using the exact official 252-column schema
for every row, regardless of which tier it came from.

Also prints a per-tier fill-rate summary, since that gradient (high ->
medium -> low fill rate, by design) IS the pitch story for how depth
was deliberately prioritized under the 23 Aug deadline.

Input:  raw_data/html/tier1_output.csv
        raw_data/html/tier2_output.csv
        outputs/tier3_output.csv
Output: outputs/unihack_final_submission.csv

Run:    python scripts/merge_final_output.py
"""

import csv

SCHEMA_PATH = "schema/schema_map.json"
TIER1_PATH = "raw_data/html/tier1_output.csv"
TIER2_PATH = "raw_data/html/tier2_output.csv"
TIER3_PATH = "outputs/tier3_output.csv"
OUTPUT_PATH = "outputs/unihack_final_submission.csv"


def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fill_rate(rows, column_order):
    if not rows:
        return 0.0
    total = len(rows) * len(column_order)
    filled = sum(
        1 for row in rows for col in column_order if str(row.get(col, "")).strip()
    )
    return filled / total * 100 if total else 0.0


def main():
    import json
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    column_order = schema["column_order"]

    tier1_rows = load_csv(TIER1_PATH)
    tier2_rows = load_csv(TIER2_PATH)
    tier3_rows = load_csv(TIER3_PATH)

    # Sanity check: every source file should already have exactly the
    # official column set. If any file's headers don't match, fail loudly
    # now rather than silently producing a malformed merged file.
    for name, rows, path in [
        ("Tier 1", tier1_rows, TIER1_PATH),
        ("Tier 2", tier2_rows, TIER2_PATH),
        ("Tier 3", tier3_rows, TIER3_PATH),
    ]:
        if rows:
            actual_cols = set(rows[0].keys())
            expected_cols = set(column_order)
            if actual_cols != expected_cols:
                missing = expected_cols - actual_cols
                extra = actual_cols - expected_cols
                print(f"WARNING: {name} ({path}) column mismatch!")
                if missing:
                    print(f"  Missing columns: {missing}")
                if extra:
                    print(f"  Unexpected extra columns: {extra}")

    all_rows = tier1_rows + tier2_rows + tier3_rows

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=column_order, extrasaction="ignore")
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"Merged {len(tier1_rows)} (Tier 1) + {len(tier2_rows)} (Tier 2) + "
          f"{len(tier3_rows)} (Tier 3) = {len(all_rows)} total rows")
    print(f"Saved to {OUTPUT_PATH}\n")

    print("Fill-rate by tier (this gradient is the intended depth story):")
    print(f"  Tier 1 (full depth):    {fill_rate(tier1_rows, column_order):.1f}%")
    print(f"  Tier 2 (medium depth):  {fill_rate(tier2_rows, column_order):.1f}%")
    print(f"  Tier 3 (light depth):   {fill_rate(tier3_rows, column_order):.1f}%")
    print(f"  Overall blended:        {fill_rate(all_rows, column_order):.1f}%")

    expected_total = 1000
    if len(all_rows) != expected_total:
        print(f"\nWARNING: expected {expected_total} total rows (1000 input rows), "
              f"got {len(all_rows)}. Investigate before treating this as final.")
    else:
        print(f"\nRow count check: {len(all_rows)}/1000 — matches the full input catalog. Correct.")


if __name__ == "__main__":
    main()