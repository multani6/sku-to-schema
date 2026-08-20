"""
sample_tier3_batch2.py
-------------------------
Pulls another 30 random Tier 3 rows for manual sourcing, EXCLUDING the
30 already sourced in batch 1 (20 Aug session).

Run (from project root):
    py scripts\\sample_tier3_batch2.py
"""

import json
import random

PATH = "outputs/tier3_enriched.json"
SAMPLE_SIZE = 30
SEED = 2  # different seed from batch 1 (seed=1) to get a fresh set

ALREADY_SOURCED = {
    "G1951-UPC", "49-94-1905", "MWUG42010124", "566679", "43852BK",
    "ADR5117512CG", "586917", "8904015", "XT524", "42200BK",
    "578810", "794.321", "1513726", "DCN930P1", "574012",
    "GT-CB-100C", "SPB-44BPL", "DCS714B", "543302146", "577876",
    "TC121VS", "IBPH250P15T", "DCM200B", "AGB15512SG", "42200BKCS",
    "43911BK", "5B-332-120", "543005936", "578801", "QO612L100RBCP",
}

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

candidates = [r for r in data if r.get("Mfg_Part_Num", "") not in ALREADY_SOURCED]

random.seed(SEED)
sample = random.sample(candidates, SAMPLE_SIZE)

for r in sample:
    mpn = r.get("Mfg_Part_Num", "")
    brand = r.get("BRAND_NAME", "")
    desc = r.get("Part_Desc", "")
    print(f"{mpn} | {brand} | {desc}")