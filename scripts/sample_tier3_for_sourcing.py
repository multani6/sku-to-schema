"""
sample_tier3_for_sourcing.py
-------------------------------
Pulls 30 random Tier 3 rows (Mfg_Part_Num, BRAND_NAME, Part_Desc only)
for manual manufacturer-URL sourcing, matching the same process used
for Tier 2's 74-row sourcing pass on 19 Aug.

Run (from project root):
    py scripts\\sample_tier3_for_sourcing.py
"""

import json
import random

PATH = "outputs/tier3_enriched.json"
SAMPLE_SIZE = 30
SEED = 1  # fixed seed so the sample is reproducible if we need to re-run

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

random.seed(SEED)
sample = random.sample(data, SAMPLE_SIZE)

for r in sample:
    mpn = r.get("Mfg_Part_Num", "")
    brand = r.get("BRAND_NAME", "")
    desc = r.get("Part_Desc", "")
    print(f"{mpn} | {brand} | {desc}")