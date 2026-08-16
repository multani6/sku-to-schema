"""
flag_generic_descriptions.py
--------------------------------------
Adds DATA_QUALITY_FLAG = "GENERIC_DESC_MPN_REQUIRED" to any row whose
SHORT_DESC is shared with 1+ other rows (different Mfg_Part_Num).

This is NOT a bug fix — it's an honest transparency flag. Investigation
confirmed these rows are generic because the raw source description
itself lacks any human-readable distinguishing detail (size/color/
finish) — only an opaque manufacturer part-number suffix differs (e.g.
"NI", "WH", "BK"), which we deliberately do NOT decode into a guessed
color/finish name, since Unilog's own guidelines are explicit that
fabricated values score zero. The Mfg_Part_Num field (always present,
always unique per row) remains the true differentiator for these SKUs
and must always be shown alongside SHORT_DESC in any UI/export.

Run:  python scripts/flag_generic_descriptions.py
"""

import json
import collections

INPUT_PATH = "outputs/tier3_enriched.json"


def main():
    with open(INPUT_PATH, encoding="utf-8") as f:
        records = json.load(f)

    desc_to_mpns = collections.defaultdict(set)
    for r in records:
        desc = r.get("SHORT_DESC", "").strip()
        if desc:
            desc_to_mpns[desc].add(r["Mfg_Part_Num"])

    generic_descs = {d for d, mpns in desc_to_mpns.items() if len(mpns) > 1}

    flagged_count = 0
    for r in records:
        if r.get("SHORT_DESC", "").strip() in generic_descs:
            r["DATA_QUALITY_FLAG"] = "GENERIC_DESC_MPN_REQUIRED"
            flagged_count += 1
        else:
            r["DATA_QUALITY_FLAG"] = ""

    with open(INPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Total rows: {len(records)}")
    print(f"Flagged as GENERIC_DESC_MPN_REQUIRED: {flagged_count} "
          f"({flagged_count/len(records)*100:.1f}%)")
    print(f"Saved back to {INPUT_PATH}")


if __name__ == "__main__":
    main()