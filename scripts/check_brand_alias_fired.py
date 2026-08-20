"""
check_brand_alias_fired.py
-----------------------------
Verifies whether resolve_brand_alias() and the manual override actually
fired on the Tier 3 enriched output — checks the real BRAND_NAME and
MANUFACTURER_NAME fields for each target row, not just raw text search.

Run (from project root):
    py scripts\\check_brand_alias_fired.py
"""

import json

PATH = "outputs/tier3_enriched.json"

# Expected outcomes after resolve_brand_alias() / MANUAL_MANUFACTURER_OVERRIDES
EXPECTED = {
    "Finyline": "RDI",
    "Patriot": "Color Guard",
    "AJM": "AJ MFG",
    "Easi-Lite": "CertainTeed",
    "Zip System": "Huber",
    "OC Duration": "Owens Corning",
    "OC WeatherLock": "Owens Corning",
    "Fine Fissured": "Armstrong Ceilings",
}

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

print(f"Total Tier 3 rows: {len(data)}\n")

# --- Check alias-based rows (match on Part_Desc containing the alias) ---
for alias, expected_mfr in EXPECTED.items():
    matches = [r for r in data if alias.lower() in (r.get("Part_Desc", "") or "").lower()]
    print(f"--- '{alias}' (expected -> {expected_mfr}) : {len(matches)} rows found ---")
    for r in matches:
        mpn = r.get("Mfg_Part_Num")
        brand = r.get("BRAND_NAME")
        mfr = r.get("MANUFACTURER_NAME")
        status = "✓ FIXED" if mfr == expected_mfr else "✗ NOT FIXED"
        print(f"  {status} | {mpn} | BRAND_NAME={brand!r} | MANUFACTURER_NAME={mfr!r}")
    print()

# --- Check the manual override row ---
print("--- BM-DW20-YLW-6 (expected manufacturer -> StealthMounts) ---")
target = [r for r in data if r.get("Mfg_Part_Num") == "BM-DW20-YLW-6"]
for r in target:
    brand = r.get("BRAND_NAME")
    mfr = r.get("MANUFACTURER_NAME")
    status = "✓ FIXED" if mfr == "StealthMounts" else "✗ NOT FIXED"
    print(f"  {status} | BRAND_NAME={brand!r} | MANUFACTURER_NAME={mfr!r}")
if not target:
    print("  ⚠ Row not found by exact Mfg_Part_Num match")