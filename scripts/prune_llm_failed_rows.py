"""
prune_llm_failed_rows.py
--------------------------------------
Scans outputs/tier3_enriched.json (or the checkpoint) for rows that got
saved with the "all retries exhausted" fallback placeholder — these have
_llm_call_failed: true, an empty SHORT_DESC, and confidence
LOW_CONFIDENCE_NEEDS_REVIEW. Some of these may have been saved during a
window BEFORE the fail-fast quota-exhaustion fix existed, meaning they
were actually just rate-limited, not genuinely low-confidence — and got
permanently marked "done" with garbage data as a result.

This script finds them and removes them from the checkpoint so the next
run of tier3_enrich.py reprocesses them properly instead of leaving
blank/garbage records in the final output.

Run this ONCE, then run: python scripts/tier3_enrich.py
"""

import csv
import json

INPUT_PATH = "raw_data/tier3_input.csv"
CHECKPOINT_PATH = "outputs/tier3_checkpoint.json"


def main():
    with open(CHECKPOINT_PATH, encoding="utf-8") as f:
        checkpoint = json.load(f)

    # NOTE: older checkpoint entries (saved before this script added the
    # "_llm_call_failed" flag to the persisted record) won't have that
    # key at all — so we can't rely on it alone for rows saved earlier.
    # The reliable signal for "this was a fallback record, not a real
    # LLM answer" is the combination the fallback always produces:
    # confidence == LOW_CONFIDENCE_NEEDS_REVIEW AND an empty SHORT_DESC.
    bad_keys = [
        k for k, v in checkpoint.items()
        if v.get("_llm_call_failed") is True
        or (v.get("_llm_confidence") == "LOW_CONFIDENCE_NEEDS_REVIEW" and not v.get("SHORT_DESC", "").strip())
    ]

    print(f"Checkpoint has {len(checkpoint)} total rows.")
    print(f"Found {len(bad_keys)} rows with placeholder/failed-call data:")
    for k in bad_keys:
        rec = checkpoint[k]
        print(f"  {k}  ->  Part_Desc: {rec.get('Part_Desc', '')[:60]}")

    if not bad_keys:
        print("\nNothing to prune — no placeholder rows found. You're clean.")
        return

    for k in bad_keys:
        del checkpoint[k]

    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2)

    print(f"\nPruned {len(bad_keys)} rows. Checkpoint now has {len(checkpoint)} rows.")
    print("Now run: python scripts/tier3_enrich.py")
    print("These rows will be reprocessed properly.")


if __name__ == "__main__":
    main()