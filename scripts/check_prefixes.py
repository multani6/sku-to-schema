"""
check_prefixes.py
------------------
Quick one-off check: does tier3_enriched.json contain any rows whose
Mfg_Part_Num starts with XOU / SMC / PMOS / SLER / PCFE, and if so,
what is their current BRAND_NAME?

Run from the unihack-project folder:
    py check_prefixes.py
"""

import json

PATH = "outputs/tier3_enriched.json"
PREFIXES = ["XOU", "SMC", "PMOS", "SLER", "PCFE"]

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

for prefix in PREFIXES:
    matches = [r for r in data if r.get("Mfg_Part_Num", "").startswith(prefix)]
    print(f"{prefix}: {len(matches)} rows found")
    for r in matches:
        mpn = r.get("Mfg_Part_Num")
        brand = r.get("BRAND_NAME")
        mfr = r.get("MANUFACTURER_NAME")
        print(f"    {mpn} -> BRAND_NAME={brand} | MANUFACTURER_NAME={mfr}")