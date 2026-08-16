"""
prune_checkpoint_for_reprocessing.py
--------------------------------------
Removes ONLY the checkpoint entries for rows affected by the
duplicate-SHORT_DESC bug (see diagnose_tier3_duplicate_descriptions.py),
so that re-running tier3_enrich.py reprocesses just those ~360 rows with
the improved prompt — instead of burning quota re-running all 916.

Run this ONCE, then run: python scripts/tier3_enrich.py
"""

import csv
import json
import collections

INPUT_PATH = "raw_data/tier3_input.csv"
OUTPUT_JSON_PATH = "outputs/tier3_enriched.json"
CHECKPOINT_PATH = "outputs/tier3_checkpoint.json"


def main():
    with open(OUTPUT_JSON_PATH, encoding="utf-8") as f:
        records = json.load(f)

    # Find every SHORT_DESC shared by 2+ different MPNs (same logic as
    # the diagnostic script) — these are the rows that need a redo.
    desc_to_mpns = collections.defaultdict(set)
    for r in records:
        desc = r.get("SHORT_DESC", "").strip()
        if desc:
            desc_to_mpns[desc].add(r["Mfg_Part_Num"])

    affected_mpns = set()
    for desc, mpns in desc_to_mpns.items():
        if len(mpns) > 1:
            affected_mpns.update(mpns)

    print(f"Rows to reprocess (duplicate-description affected): {len(affected_mpns)}")

    # Rebuild row_key for every row in the original input, in the same
    # "mpn::row_index" format tier3_enrich.py uses.
    with open(INPUT_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    keys_to_remove = set()
    for i, row in enumerate(rows, start=1):
        mpn = row["Mfg_Part_Num"]
        if mpn in affected_mpns:
            row_key = f"{mpn}::{i}" if mpn else f"NOPART::{i}"
            keys_to_remove.add(row_key)

    with open(CHECKPOINT_PATH, encoding="utf-8") as f:
        checkpoint = json.load(f)

    before = len(checkpoint)
    for k in keys_to_remove:
        checkpoint.pop(k, None)
    after = len(checkpoint)

    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2)

    print(f"Checkpoint: {before} -> {after} entries ({before - after} pruned for reprocessing).")
    print("Now run: python scripts/tier3_enrich.py")
    print("It will resume and reprocess ONLY the pruned rows with the improved prompt.")


if __name__ == "__main__":
    main()