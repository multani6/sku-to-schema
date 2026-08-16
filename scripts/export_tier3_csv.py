"""
export_tier3_csv.py
----------------------
Exports the 916 Tier-3 (light-depth) records to the official 252-column
CSV schema — same pattern as export_tier1_csv.py / export_tier2_csv.py.

IMPORTANT — this is a LIGHT-DEPTH tier by design (documented decision,
not a limitation): only a small subset of the 252 columns are populated
per row (identifiers, brand/manufacturer, one description, a rough
category). Every other column is left blank rather than guessed, which
is the honest choice per Unilog's own guidance ("a fluent description
made of invented values scores zero").

Field-mapping decisions made here (documented so nothing is a silent
guess):
  - category (our internal field) -> Classpath. We only ever produced a
    single flat category name (e.g. "Lighting"), not a full official
    breadcrumb like "Appliances & Consumer Electronics > Kitchen
    Appliances > ...", because we have no official taxonomy file. We
    write the flat name as-is rather than fabricate a fake hierarchy.
  - Mfg_Part_Num is also copied into MANUFACTURER_PART_NUMBER, since
    for this catalog the manufacturer's part number IS the value we
    have in Mfg_Part_Num (no separate internal SKU was provided).
  - SHORT_DESC is the ONLY description field populated. Tier 1/2 wrote
    5 description formats per row (mobile/invoice/short/long/retail);
    Tier 3 deliberately does not, to stay within the light-depth scope.
  - DATA_QUALITY_FLAG and category_method/_llm_confidence are INTERNAL
    fields (not part of the official 252 columns) and are excluded from
    this CSV, same as Tier 1/2's exporter excludes its internal fields.
    They remain visible in outputs/tier3_enriched.json for the
    dashboard / audit trail.

Input:  schema/schema_map.json
        outputs/tier3_enriched.json
Output: outputs/tier3_output.csv

Run:    python scripts/export_tier3_csv.py
"""

import json
import csv

SCHEMA_PATH = "schema/schema_map.json"
FINAL_PATH = "outputs/tier3_enriched.json"
OUTPUT_PATH = "outputs/tier3_output.csv"

# Internal-only fields, not part of the official 252-column schema.
INTERNAL_FIELDS = {
    "category", "category_method", "_llm_confidence",
    "_llm_call_failed", "DATA_QUALITY_FLAG",
}


def map_to_schema_columns(record: dict) -> dict:
    """
    Converts one Tier 3 internal record into a dict keyed by the
    OFFICIAL 252-column names, applying only the documented mappings
    above. Any column not explicitly set here is left blank by
    DictWriter automatically (restval='' is the default).
    """
    mpn = record.get("Mfg_Part_Num", "")
    return {
        "Mfg_Part_Num": mpn,
        "MANUFACTURER_PART_NUMBER": mpn,
        "Part_Desc": record.get("Part_Desc", ""),
        "E1_Brand": record.get("E1_Brand", ""),
        "Unilog_Brand": record.get("Unilog_Brand", ""),
        "DIB_Brand": record.get("DIB_Brand", ""),
        "Part_Manuf": record.get("Part_Manuf", ""),
        "BRAND_NAME": record.get("BRAND_NAME", ""),
        "MANUFACTURER_NAME": record.get("MANUFACTURER_NAME", ""),
        "Classpath": record.get("category", ""),
        "SHORT_DESC": record.get("SHORT_DESC", ""),
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
            mapped = map_to_schema_columns(record)
            writer.writerow(mapped)

    print(f"Exported {len(records)} rows x {len(column_order)} columns -> {OUTPUT_PATH}")

    total_cells = len(records) * len(column_order)
    filled_cells = sum(
        1 for record in records
        for col in column_order
        if str(map_to_schema_columns(record).get(col, "")).strip()
    )
    fill_rate = filled_cells / total_cells * 100 if total_cells else 0
    print(f"Overall field fill rate: {filled_cells}/{total_cells} ({fill_rate:.1f}%)")
    print("(Low fill rate is EXPECTED and correct for Tier 3 — light-depth")
    print(" by design, see docstring. Compare against Tier 1/2's much higher")
    print(" fill rate to show the deliberate depth gradient in the pitch.)")


if __name__ == "__main__":
    main()