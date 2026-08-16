"""
diagnose_tier3_duplicate_descriptions.py
--------------------------------------
Checks how many rows in the Tier 3 enriched output share an identical
SHORT_DESC with at least one other row that has a DIFFERENT Mfg_Part_Num.
This matters because a duplicate description across two distinct SKUs
means a buyer can't tell the products apart in search results — a real
data-quality problem, not a cosmetic one.

Run:  python scripts/diagnose_tier3_duplicate_descriptions.py
"""

import json
import collections

with open("outputs/tier3_enriched.json", encoding="utf-8") as f:
    records = json.load(f)

desc_to_mpns = collections.defaultdict(set)
for r in records:
    desc = r.get("SHORT_DESC", "").strip()
    if desc:
        desc_to_mpns[desc].add(r["Mfg_Part_Num"])

problem_descs = {d: mpns for d, mpns in desc_to_mpns.items() if len(mpns) > 1}
affected_rows = sum(len(mpns) for mpns in problem_descs.values())

print(f"Total rows: {len(records)}")
print(f"Distinct SHORT_DESC values: {len(desc_to_mpns)}")
print(f"SHORT_DESC values shared by 2+ different MPNs: {len(problem_descs)}")
print(f"Total rows affected by a shared/duplicate description: {affected_rows} "
      f"({affected_rows/len(records)*100:.1f}% of Tier 3)")

print("\nTop 10 worst offenders (most MPNs sharing one description):")
worst = sorted(problem_descs.items(), key=lambda x: -len(x[1]))[:10]
for desc, mpns in worst:
    print(f"  [{len(mpns)} SKUs] \"{desc}\"")
    for m in list(mpns)[:5]:
        print(f"      - {m}")