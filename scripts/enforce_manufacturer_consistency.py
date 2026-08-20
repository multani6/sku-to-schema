"""
enforce_manufacturer_consistency.py
--------------------------------------
Reused as-is from Tier 1/2. Groups records by (normalized) brand, picks a
single canonical manufacturer per brand, and applies it consistently.

Fix (18 Aug 2026, found via full Tier 3 dataset test): rows with
BRAND_NAME == "Unknown" were being grouped together and majority-voted
as if "Unknown" were a real shared brand, which silently overwrote
correct manufacturer names (e.g. "Rees Cast Stone Company",
"Westwood Lumber Sales") with "Unknown". Placeholder brand values are
now excluded from grouping entirely, so those rows are left untouched.

Fix (19 Aug 2026, Day 1 Tier 2 sourcing): some rows have a BRAND_NAME
that is itself wrong, not just an inconsistent MANUFACTURER_NAME.
e.g. TC5003BN is labeled BRAND_NAME="LG" but the TC5 prefix is Speed
Queen. These are corrected via MPN-prefix override BEFORE grouping,
so the row lands in the correct brand group and gets the correct
manufacturer automatically.

Fix (20 Aug 2026, Day 2, Tier 3 150-row partial sourcing): two new
bug-classes found, distinct from the ones above:
  (a) product-line name sitting in BRAND_NAME instead of the parent
      manufacturer (e.g. "Finyline" instead of "RDI")
  (b) BRAND_NAME="Unknown" rows where Part_Desc text actually reveals
      the real manufacturer (e.g. "OC Duration" -> Owens Corning)
  (c) third-party "compatible-with" mislabeling, where BRAND_NAME is
      legitimately a third-party brand (e.g. "DeWalt") but the true
      MANUFACTURER is a different company (e.g. StealthMounts)
(a) and (b) are handled by resolve_brand_alias(), run BEFORE grouping.
(c) is handled by MANUAL_MANUFACTURER_OVERRIDES, applied AFTER grouping
so majority-vote doesn't overwrite it back.
"""

import json
import re
import sys
import collections

DEFAULT_PATH = "raw_data/html/tier2_llm_enriched.json"

AUTHORITATIVE_BRAND_MANUFACTURER = {
    "speedqueen": "Alliance Laundry Systems",
    "frigidaire": "Electrolux",
    "kitchenaid": "Whirlpool Corporation",
    "whirlpool": "Whirlpool Corporation",
    "geprofile": "GE Appliances (Haier)",
    "gecafe": "GE Appliances (Haier)",
    "ge": "GE Appliances (Haier)",
    "lg": "LG Electronics",
    "element": "Element Electronics",
    # --- Day 1 (19 Aug) Tier 2 sourcing bug fixes ---
    # Verified against tier2_sourced_data.json corrected_brand_name /
    # corrected_manufacturer_name fields (exact strings, do not alter).
    # XOU2470BCGS, XOU24BCGSR, XOU24WDZGBR: wrongly attributed to "GE Cafe"
    # -> actual brand/manufacturer is "XO Appliance" (independent co., XOU
    # prefix). normalize_brand("XO Appliance") = "xoappliance".
    "xoappliance": "XO Appliance",
    # SMC2266KS: wrongly labeled "Samsung" -> actual brand/manufacturer is
    # "Sharp" (SMC prefix = Sharp, not Samsung).
    "sharp": "Sharp",
    # PMOS1980AF: brand is "Frigidaire Professional" (distinct normalized
    # key from plain "Frigidaire" above) -> manufacturer is Electrolux.
    "frigidaireprofessional": "Electrolux",
    # SLER30524SS: wrongly labeled "Samsung" -> actual brand/manufacturer
    # is "Beko" (SLER prefix = Beko, not Samsung).
    "beko": "Beko",
}

# NEW (Day 2, 20 Aug): distinct bug-class from AUTHORITATIVE_BRAND_MANUFACTURER
# above. That dict keys off normalized BRAND_NAME and fixes MANUFACTURER_NAME.
# This dict keys off a raw product-line name or Unknown-masked alias found in
# BRAND_NAME/Part_Desc, and fixes BOTH fields. Found during Tier 3 150-row
# partial sourcing (20 Aug) — product-line names used as brand, and
# BRAND_NAME="Unknown" rows where Part_Desc reveals the real manufacturer.
BRAND_ALIAS_TO_MANUFACTURER = {
    "Finyline": "RDI",
    "Patriot": "Color Guard",
    "AJM": "AJ MFG",
    "Easi-Lite": "CertainTeed",
    "Zip System": "Huber",
    "OC Duration": "Owens Corning",
    "OC WeatherLock": "Owens Corning",
    "Fine Fissured": "Armstrong Ceilings",
    "XT": "Bow Products",
    "Tech Gear": "Mobile Warming by Fieldsheer",
}

# NEW (Day 2, 20 Aug): third-party "compatible-with" mislabeling.
# BM-DW20-YLW-6: BRAND_NAME legitimately stays "DeWalt" (it IS a DeWalt-
# compatible accessory), but the true MANUFACTURER is StealthMounts, not
# DeWalt. Must be applied AFTER grouping/majority-vote, not before —
# otherwise the DeWalt brand-group's majority vote will overwrite it back
# to DeWalt's real manufacturer.
MANUAL_MANUFACTURER_OVERRIDES = {
    "BM-DW20-YLW-6": "StealthMounts",
}

# Brand values that are placeholders, not real shared brands. Rows
# carrying one of these must never be grouped together for majority-vote
# purposes — they are unrelated products that merely share an "unknown"
# label, not products from the same manufacturer.
PLACEHOLDER_BRANDS = {"unknown", "n/a", "none", ""}

# MPN-prefix-based BRAND_NAME overrides. Some rows have a BRAND_NAME that
# is itself wrong (not just an inconsistent manufacturer), e.g. TC5003BN
# is labeled BRAND_NAME="LG" but the TC5 prefix is Speed Queen. These
# must be corrected BEFORE grouping/majority-vote, or the row silently
# gets grouped under the wrong brand and assigned the wrong manufacturer.
MPN_PREFIX_BRAND_OVERRIDES = {
    "TC5": "Speed Queen",
    # TODO (Shubman — verify before uncommenting): only add these if the
    # BRAND_NAME field itself is wrong in the Tier 3 raw data for these
    # MPNs, same situation as TC5003BN. If BRAND_NAME is already correct
    # there and only MANUFACTURER_NAME was wrong, do NOT add these —
    # AUTHORITATIVE_BRAND_MANUFACTURER above already handles it via
    # grouping, and adding an unnecessary override here risks silently
    # reclassifying a row that didn't need it.
    # "XOU": "XO Appliance",
    # "SMC": "Sharp",
    # "PMOS": "Frigidaire Professional",
    # "SLER": "Beko",
    "PCFE": "Frigidaire Professional",
}


def normalize_brand(brand):
    b = re.sub(r"[^a-z0-9]", "", str(brand).lower())
    return b


def apply_mpn_prefix_overrides(records):
    fixed = []
    for r in records:
        mpn = r.get("Mfg_Part_Num", "").strip()
        for prefix, correct_brand in MPN_PREFIX_BRAND_OVERRIDES.items():
            if mpn.startswith(prefix) and r.get("BRAND_NAME", "").strip() != correct_brand:
                fixed.append({
                    "mfg_part_num": mpn,
                    "old_brand": r.get("BRAND_NAME", ""),
                    "new_brand": correct_brand,
                })
                r["BRAND_NAME"] = correct_brand
                break
    return fixed


def resolve_brand_alias(records):
    """
    Run BEFORE grouping. Handles two Tier 3 bug-classes found in the
    20 Aug 150-row partial sourcing pass:
      (a) product-line name sitting in BRAND_NAME instead of the parent
          manufacturer (e.g. "Finyline" -> "RDI")
      (b) BRAND_NAME="Unknown" rows where Part_Desc text reveals the
          real manufacturer (e.g. desc contains "OC Duration" -> Owens
          Corning)
    Only fires on an explicit alias match from BRAND_ALIAS_TO_MANUFACTURER,
    so it cannot over-fix genuinely unbranded commodity rows (e.g. Doug
    Fir STK correctly stays "Unknown" — confirmed negative control).
    """
    fixes = []
    for r in records:
        brand = r.get("BRAND_NAME", "").strip()
        desc = r.get("Part_Desc", "") or ""

        # (a) direct product-line-as-brand alias match
        if brand in BRAND_ALIAS_TO_MANUFACTURER:
            mfr = BRAND_ALIAS_TO_MANUFACTURER[brand]
            if r.get("MANUFACTURER_NAME", "").strip() != mfr or brand != mfr:
                fixes.append({
                    "mfg_part_num": r.get("Mfg_Part_Num", ""),
                    "old_brand": brand,
                    "new_brand": mfr,
                    "reason": "product_line_as_brand",
                })
                r["BRAND_NAME"] = mfr
                r["MANUFACTURER_NAME"] = mfr
            continue

        # (b) Unknown-masking: check Part_Desc for a known alias substring
        if brand.lower() == "unknown":
            for alias, mfr in BRAND_ALIAS_TO_MANUFACTURER.items():
                if alias.lower() in desc.lower():
                    fixes.append({
                        "mfg_part_num": r.get("Mfg_Part_Num", ""),
                        "old_brand": brand,
                        "new_brand": mfr,
                        "reason": f"unknown_masking (matched '{alias}' in Part_Desc)",
                    })
                    r["BRAND_NAME"] = mfr
                    r["MANUFACTURER_NAME"] = mfr
                    break

    return fixes


def apply_manual_overrides(records):
    """
    Run AFTER grouping/majority-vote. Handles third-party "compatible-with"
    mislabeling (e.g. BM-DW20-YLW-6: BRAND_NAME correctly stays "DeWalt",
    but true MANUFACTURER is StealthMounts). Must run last, or majority-vote
    on the DeWalt brand-group would overwrite it back.
    """
    fixes = []
    for r in records:
        mpn = r.get("Mfg_Part_Num", "").strip()
        if mpn in MANUAL_MANUFACTURER_OVERRIDES:
            correct_mfr = MANUAL_MANUFACTURER_OVERRIDES[mpn]
            current = r.get("MANUFACTURER_NAME", "").strip()
            if current != correct_mfr:
                fixes.append({
                    "mfg_part_num": mpn,
                    "old_manufacturer": current,
                    "new_manufacturer": correct_mfr,
                    "reason": "manual_override_third_party",
                })
                r["MANUFACTURER_NAME"] = correct_mfr
    return fixes


def pick_canonical_manufacturer(records_in_group, normalized_brand):
    if normalized_brand in AUTHORITATIVE_BRAND_MANUFACTURER:
        return AUTHORITATIVE_BRAND_MANUFACTURER[normalized_brand], "AUTHORITATIVE"

    high_conf_values = [
        r.get("MANUFACTURER_NAME", "").strip()
        for r in records_in_group
        if r.get("_llm_confidence") == "high" and r.get("MANUFACTURER_NAME", "").strip()
    ]
    all_values = [
        r.get("MANUFACTURER_NAME", "").strip()
        for r in records_in_group
        if r.get("MANUFACTURER_NAME", "").strip()
    ]

    pool = high_conf_values if high_conf_values else all_values
    if not pool:
        return None, None

    counts = collections.Counter(pool)
    return counts.most_common(1)[0][0], "MAJORITY_VOTE"


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH

    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    brand_fixes = apply_mpn_prefix_overrides(records)
    alias_fixes = resolve_brand_alias(records)

    groups = collections.defaultdict(list)
    for r in records:
        brand = r.get("BRAND_NAME", "").strip()
        if brand and brand.lower() not in PLACEHOLDER_BRANDS:
            groups[normalize_brand(brand)].append(r)

    corrections = []

    for norm_brand, group in groups.items():
        if len(group) < 2 and norm_brand not in AUTHORITATIVE_BRAND_MANUFACTURER:
            continue

        canonical, method = pick_canonical_manufacturer(group, norm_brand)
        if canonical is None:
            continue
        if canonical.strip().lower() in PLACEHOLDER_BRANDS:
            continue  # never "correct" a real name into a placeholder

        for r in group:
            current = r.get("MANUFACTURER_NAME", "").strip()
            if current != canonical:
                corrections.append({
                    "mfg_part_num": r.get("Mfg_Part_Num", ""),
                    "brand": r.get("BRAND_NAME", ""),
                    "old_manufacturer": current,
                    "new_manufacturer": canonical,
                    "method": method,
                })
                r["MANUFACTURER_NAME"] = canonical

    manual_fixes = apply_manual_overrides(records)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"Checked {len(records)} rows across {len(groups)} brand groups.")
    if brand_fixes:
        print(f"Corrected {len(brand_fixes)} BRAND_NAME (MPN-prefix) errors.")
        for bf in brand_fixes:
            print(f"  - {bf['mfg_part_num']}: BRAND_NAME '{bf['old_brand']}' -> '{bf['new_brand']}'")
    if alias_fixes:
        print(f"Corrected {len(alias_fixes)} brand-alias errors (product-line-as-brand / Unknown-masking).")
        for af in alias_fixes:
            print(f"  - {af['mfg_part_num']}: BRAND_NAME '{af['old_brand']}' -> '{af['new_brand']}' [{af['reason']}]")
    if corrections:
        print(f"Corrected {len(corrections)} manufacturer-name inconsistencies.")
        for c in corrections:
            print(f"  - {c['mfg_part_num']} ({c['brand']}): '{c['old_manufacturer']}' -> '{c['new_manufacturer']}' [{c['method']}]")
    else:
        print("No majority-vote/authoritative inconsistencies found.")
    if manual_fixes:
        print(f"Applied {len(manual_fixes)} manual third-party overrides.")
        for mf in manual_fixes:
            print(f"  - {mf['mfg_part_num']}: MANUFACTURER_NAME '{mf['old_manufacturer']}' -> '{mf['new_manufacturer']}' [{mf['reason']}]")


if __name__ == "__main__":
    main()
