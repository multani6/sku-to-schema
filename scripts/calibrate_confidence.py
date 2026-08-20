"""
calibrate_confidence.py
--------------------------------------
Cross-checks LLM's self-reported confidence (_llm_confidence) against an
INDEPENDENT, rule-based MPN-prefix -> manufacturer signal. This answers
the hardest Q&A question: "is your confidence tag calibrated, or is the
LLM just confidently asserting itself?"

v2 fix (real bug caught during first run): the rule table was built from
appliance-domain patterns only (Tier 1/2). Short prefixes like "DC"
collide across domains -- "DC" means Speed Queen (laundry appliance) in
Tier 2, but means DeWalt/Stanley Black & Decker (power tools -- DCB,
DCD, DCF, DCG, DCS, DCK, DCN family) in Tier 3. Applying the appliance
rule table to Tier 3 rows produced 41 false "MISMATCH" flags that were
actually the RULE being wrong, not the LLM. Fixed by scoping the rule
table to only the domain it was built for (Tier 1/2). This is a real,
documented bug in our own verification tooling -- kept in, not hidden.

v3 fix (20 Aug 2026 — found via first full pipeline run): four prefix
mappings here were STALE — they predated the Day 1 (19 Aug) manufacturer-
attribution fixes verified and applied in enforce_manufacturer_
consistency.py's AUTHORITATIVE_BRAND_MANUFACTURER table, but this rule
table was never updated to match. That produced false "MISMATCH" flags
for rows where the LLM/enforcement output was actually CORRECT and this
script's own rule was wrong:
    XOU  was mapped to "GE"      -> corrected to "XO Appliance"
    TC5  was mapped to "LG"      -> corrected to "Alliance Laundry" (Speed Queen)
    SMC  was mapped to "Samsung" -> corrected to "Sharp"
    SLER was mapped to "Samsung" -> corrected to "Beko"
Same lesson as the v2 fix: this script's rule table is a separate,
hand-maintained source of truth from AUTHORITATIVE_BRAND_MANUFACTURER,
so the two can silently drift apart. Worth keeping in sync going
forward whenever a new prefix fix is verified.

v4 fix (20 Aug 2026 — found in the v3-corrected calibration run): PDT
and PDD prefixes were grouped with PDSH under "Electrolux", but PDT/PDD
are GE Profile prefixes, not Frigidaire. Confirmed directly by Stage 2.5
scraping logs: PDT715SYVFS and PDD415PYYFS both resolved to real
geappliances.com product URLs (GE-Profile-...-PDT715SYVFS and
GE-Profile-Double-Drawer-Dishwasher-PDD415PYYFS), which is independent
evidence the manufacturer is GE, not Electrolux. Moved ^PDT|^PDD out of
the Electrolux rule and into the GE rule. PDSH stays under Electrolux
(that one is correct — PDSH4816AF is the Frigidaire benchmark row).

v5 fix (20 Aug 2026 — found in the v4-corrected calibration run):
ERF/EUF prefixes were grouped under "Electrolux", but all 3 mismatched
rows (ERFD19CGCS, EUF17CDBW, EUF21CDBW) were independently verified via
web search to be sold directly on elementelectronics.com's own official
product pages — the strongest available evidence short of scraping the
page ourselves. Moved ^ERF|^EUF out of the Electrolux rule into a new
dedicated "Element Electronics" rule. The LLM's MANUFACTURER_NAME output
was correct in all 3 cases; only this script's rule table was wrong.

Design:
  - A hand-built prefix table (from patterns visible across tier1/tier2
    enriched data) maps MPN prefixes -> expected manufacturer, SCOPED to
    Tier 1/2 only (appliance domain).
  - For each row, we independently derive an "expected" manufacturer from
    the prefix alone (no LLM call) and compare it to what the LLM output
    in MANUFACTURER_NAME.
  - AGREEMENT_STATUS is the real calibration signal:
      MATCH              -> rule-based signal agrees with LLM's own claim
      MISMATCH           -> rule-based signal disagrees -> real risk flag
      NO_RULE_COVERAGE   -> no scoped rule applies -> can't independently
                             verify, LLM's self-report stands alone here
  - This does NOT re-run the LLM. It only re-analyzes already-generated
    JSON output files. Zero additional API cost.

Run:
  python scripts/calibrate_confidence.py
"""

import json
import re
import os
from collections import Counter

TIER1_PATH = "raw_data/html/tier1_llm_enriched.json"
TIER2_PATH = "raw_data/html/tier2_llm_enriched.json"
TIER3_PATH = "outputs/tier3_enriched.json"
OUTPUT_PATH = "outputs/confidence_calibration_report.json"

# ---------------------------------------------------------------------
# Rule-based signal, SCOPED TO APPLIANCE DOMAIN (Tier 1/2 only -- see
# v2 fix note above). Built from prefix patterns observed across the
# Tier 1/2 dataset (dishwashers, dryers, washers, ranges, microwaves,
# refrigerators, freezers).
#
# HONEST CAVEAT: this rule table's prefix patterns substantially
# overlap with the MPN-prefix hints already given to the LLM inside
# enrich_tier1_llm.py's / enrich_tier2_llm.py's system prompts. That
# means a high agreement % here mostly reflects INTERNAL CONSISTENCY
# between the prompt's hints and the LLM's own output -- not a fully
# independent, external ground-truth validation. Treat the calibration
# metric below as an internal-consistency check, and present it that
# way in the pitch/README, not as independent proof of accuracy.
# ---------------------------------------------------------------------
MPN_PREFIX_RULES = [
    (r"^KDFM|^KDTS|^KDPS|^KSES|^KMMF", "Whirlpool"),
    (r"^WDTS|^WDF|^WMMS|^WSGS", "Whirlpool"),
    (r"^PDSH|^PRFS|^GCFG", "Electrolux"),
    (r"^ERF|^EUF", "Element Electronics"),
    (r"^PEP|^PCFE|^PTD|^PTW|^PB9|^PS9|^PAD|^PGE|^GNE|^GDE|^GCST|^JXGRILL|^C7|^C9|^C90|^CVE|^CVM|^CHP|^CES|^PDT|^PDD",
     "GE"),
    (r"^XOU", "XO Appliance"),
    (r"^LDPH|^LDT|^LDF|^LT18|^LSEL|^WKE|^MSER", "LG"),
    (r"^DF|^DR|^DV|^DC|^TV|^TR|^FF|^TC5", "Alliance Laundry"),
    (r"^MVW", "Maytag"),
    (r"^SMC|^SMD", "Sharp"),
    (r"^WOSP|^SLER", "Beko"),
]

# Domains where the rule table above is valid. Extend this list only
# after building/verifying rules for that domain -- do NOT just remove
# the scoping check, that's what caused the v1 false positives.
RULE_TABLE_VALID_TIERS = {"Tier 1", "Tier 2"}


def rule_based_manufacturer(mpn: str, tier: str):
    """
    Returns the expected manufacturer substring if a scoped rule matches,
    else None. Only applies MPN_PREFIX_RULES within the domain (tier) it
    was built for -- see module docstring for why this scoping matters.
    """
    if tier not in RULE_TABLE_VALID_TIERS:
        return None
    for pattern, expected in MPN_PREFIX_RULES:
        if re.match(pattern, mpn or ""):
            return expected
    return None


def check_agreement(rule_expected: str, llm_manufacturer: str) -> str:
    if rule_expected is None:
        return "NO_RULE_COVERAGE"
    if not llm_manufacturer:
        return "MISMATCH"
    if rule_expected.lower() in llm_manufacturer.lower():
        return "MATCH"
    return "MISMATCH"


def load_json(path):
    if not os.path.exists(path):
        print(f"⚠️  Not found, skipping: {path}")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def analyze(records, tier_name):
    results = []
    for r in records:
        mpn = r.get("Mfg_Part_Num", "")
        llm_manuf = r.get("MANUFACTURER_NAME", "")
        llm_conf = r.get("_llm_confidence", "")

        rule_expected = rule_based_manufacturer(mpn, tier_name)
        agreement = check_agreement(rule_expected, llm_manuf)

        results.append({
            "tier": tier_name,
            "mfg_part_num": mpn,
            "llm_manufacturer": llm_manuf,
            "llm_confidence": llm_conf,
            "rule_expected_manufacturer": rule_expected,
            "agreement_status": agreement,
        })
    return results


def main():
    tier1 = analyze(load_json(TIER1_PATH), "Tier 1")
    tier2 = analyze(load_json(TIER2_PATH), "Tier 2")
    tier3 = analyze(load_json(TIER3_PATH), "Tier 3")
    all_results = tier1 + tier2 + tier3

    high_conf_values = {"high", "EXACT_SKU_VERIFIED"}
    checkable = [r for r in all_results if r["agreement_status"] != "NO_RULE_COVERAGE"]
    high_conf_checkable = [r for r in checkable if r["llm_confidence"] in high_conf_values]

    high_conf_match = sum(1 for r in high_conf_checkable if r["agreement_status"] == "MATCH")
    high_conf_total = len(high_conf_checkable)
    calibration_rate = round(high_conf_match / high_conf_total * 100, 1) if high_conf_total else None

    mismatches = [r for r in all_results if r["agreement_status"] == "MISMATCH"]

    status_counts = Counter(r["agreement_status"] for r in all_results)
    coverage_rate = round((len(checkable) / len(all_results)) * 100, 1) if all_results else 0

    report = {
        "meta": {
            "total_rows_analyzed": len(all_results),
            "rule_coverage_pct": coverage_rate,
            "note": "Rule coverage is intentionally scoped to Tier 1/2 (appliance domain) after v2 fix -- see script docstring for the v1 cross-domain bug this fixed. IMPORTANT: this rule table overlaps substantially with the MPN-prefix hints given to the LLM in the enrichment prompts, so the calibration metric below reflects INTERNAL CONSISTENCY, not independent ground-truth validation -- see module docstring.",
        },
        "calibration_metric": {
            "description": "Of rows LLM tagged HIGH confidence AND we could independently rule-check, % where the independent rule agrees. NOTE: 'independent' here means a separately-coded rule table, not a separately-sourced signal -- see caveat in meta.note above.",
            "high_confidence_checkable_rows": high_conf_total,
            "high_confidence_rule_agreement_pct": calibration_rate,
        },
        "agreement_status_breakdown": dict(status_counts),
        "mismatches_needing_review": mismatches,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Analyzed {len(all_results)} rows across all tiers")
    print(f"Rule coverage (Tier 1/2 only, scoped after v2 fix): {coverage_rate}% of rows")
    print(f"\n--- CALIBRATION METRIC (the number that matters for Q&A) ---")
    print(f"NOTE: this is an internal-consistency check, not independent ground-truth validation (see docstring).")
    print(f"High-confidence rows we could independently verify: {high_conf_total}")
    print(f"Of those, independent rule agreed: {high_conf_match} ({calibration_rate}%)")
    print(f"\nAgreement breakdown: {dict(status_counts)}")
    print(f"\nMismatches found (real discrepancies to investigate): {len(mismatches)}")
    if mismatches:
        print("First 5 mismatches:")
        for m in mismatches[:5]:
            print(f"  {m['mfg_part_num']}: LLM said '{m['llm_manufacturer']}' "
                  f"(confidence={m['llm_confidence']}), rule expected '{m['rule_expected_manufacturer']}'")
    print(f"\nSaved full report: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()