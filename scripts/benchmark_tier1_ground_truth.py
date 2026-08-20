"""
benchmark_tier1_ground_truth.py
---------------------------------
Compares your LLM-enriched Tier-1 output against the 2 official
worked-example rows Unilog provided (PDSH4816AF and WDTS7024RZ) and
produces real, defensible accuracy numbers — not claimed metrics.

Scoring methods (deliberately different per field type, because a
single blanket "accuracy %" is not credible):
  - EXACT match        : identifiers, manufacturer/brand names
  - FORMAT compliance   : character limits + casing rules for descriptions
  - LABEL RECALL        : what % of the official attribute labels did we
                           also produce (regardless of exact wording)?
  - VALUE match          : for attributes where we produced the same
                           label, does our value match the official value?

Input:  raw_data/html/tier1_llm_enriched.json
Output: printed report + raw_data/html/tier1_benchmark_report.json

Run (from the project root, e.g. via scripts/run_pipeline.py):
  python scripts/benchmark_tier1_ground_truth.py

Note (20 Aug 2026): this file was briefly patched to use "../"-prefixed
paths on the assumption the pipeline should run from inside scripts/.
A full scan of every script's path constants showed that's backwards —
every other script in the pipeline uses root-relative paths. Reverted
to the original, correct root-relative paths below.
"""

import json
import re

ENRICHED_PATH = "raw_data/html/tier1_final.json"
REPORT_PATH = "raw_data/html/tier1_benchmark_report.json"

# ---- Official ground truth, transcribed directly from Unilog's
# Expected Output - Delivery Format worked examples ----

GROUND_TRUTH = {
    "PDSH4816AF": {
        "MANUFACTURER_NAME": "Rheem Manufacturing",
        "BRAND_NAME": "FRIGIDAIRE®",
        "INVOICE_DESC": "DISHWASHER LEG 5 SST 120V 15A 50-1/4IN",
        "MOBILE_DESC": "Rheem Manufacturing FRIGIDAIRE, Dishwasher, Professional Series, PDSH4816AF",
        "attributes": {
            "series": "Professional Series",
            "number of wash cycles": "5",
            "voltage rating": "120",
            "amperage rating": "15",
            "mounting type": "Leg",
            "depth with door open": "50-1/4",
            "sound level": "47",
            "material": "Stainless Steel",
        },
    },
    "WDTS7024RZ": {
        "MANUFACTURER_NAME": "Whirlpool Corporation",
        "BRAND_NAME": "Whirlpool®",
        "INVOICE_DESC": "DISHWASHER BLTLN SST SST 120V 10A 41DBA",
        "MOBILE_DESC": "Whirlpool, Dishwasher, Eco Series, WDTS7024RZ, Built-in Mounting",
        "attributes": {
            "series": "Eco Series",
            "voltage rating": "120",
            "amperage rating": "10",
            "mounting type": "Built-in",
            "depth with door open": "50-3/16",
            "minimum height": "33-7/16",
            "sound level": "41",
            "material": "Stainless Steel",
        },
    },
}


def normalize(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


# Corporate suffixes that shouldn't cause a legitimate match to fail —
# "Whirlpool" and "Whirlpool Corporation" refer to the same company.
CORPORATE_SUFFIXES = [
    "corporation", "corp", "inc", "incorporated", "llc", "ltd",
    "limited", "company", "co", "manufacturing", "mfg",
]


def normalize_company_name(s):
    n = normalize(s)
    for suffix in CORPORATE_SUFFIXES:
        n = n.replace(suffix, "")
    return n


def exact_match(a, b):
    return normalize(a) == normalize(b)


def company_match(a, b):
    """Fuzzier match for manufacturer/brand names: ignores corporate
    suffixes and checks if one name is contained in the other, since
    'Whirlpool' vs 'Whirlpool Corporation' is a correct match, not an error."""
    na, nb = normalize_company_name(a), normalize_company_name(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def check_invoice_desc(value):
    issues = []
    if len(value) > 40:
        issues.append(f"exceeds 40 chars ({len(value)})")
    if value != value.upper():
        issues.append("not all caps")
    return issues


def check_mobile_desc(value):
    issues = []
    length = len(value)
    if not (60 <= length <= 80):
        issues.append(f"length {length} outside 60-80 char range")
    return issues


def build_attr_lookup(record):
    """Builds {normalized_label: value} from the 50 ATTRIBUTE_LABEL/VALUE columns."""
    lookup = {}
    for i in range(1, 51):
        label = record.get(f"ATTRIBUTE_LABEL {i}", "")
        value = record.get(f"ATTRIBUTE_VALUE {i}", "")
        if label:
            lookup[normalize(label)] = value
    return lookup


def score_row(mpn, generated, truth):
    result = {"mfg_part_num": mpn, "checks": {}}

    # --- Exact-match fields ---
    # BRAND_NAME and MANUFACTURER_NAME use company_match (suffix/parent-
    # company tolerant) rather than strict exact_match, because
    # "Whirlpool" vs "Whirlpool Corporation" is a correct match, not an
    # error — punishing it would misrepresent real accuracy.
    for field in ["MANUFACTURER_NAME", "BRAND_NAME"]:
        gen_val = generated.get(field, "")
        truth_val = truth[field]
        result["checks"][field] = {
            "generated": gen_val,
            "expected": truth_val,
            "match": company_match(gen_val, truth_val),
        }

    # --- Format compliance ---
    invoice_val = generated.get("INVOICE_DESC", "")
    result["checks"]["INVOICE_DESC_format"] = {
        "generated": invoice_val,
        "issues": check_invoice_desc(invoice_val),
        "pass": len(check_invoice_desc(invoice_val)) == 0,
    }

    mobile_val = generated.get("MOBILE_DESC", "")
    result["checks"]["MOBILE_DESC_format"] = {
        "generated": mobile_val,
        "issues": check_mobile_desc(mobile_val),
        "pass": len(check_mobile_desc(mobile_val)) == 0,
    }

    # --- Attribute label recall + value match ---
    gen_attrs = build_attr_lookup(generated)
    expected_attrs = {normalize(k): v for k, v in truth["attributes"].items()}

    matched_labels = 0
    matched_values = 0
    label_details = []
    for norm_label, expected_val in expected_attrs.items():
        found = norm_label in gen_attrs
        value_match = found and exact_match(gen_attrs.get(norm_label, ""), expected_val)
        if found:
            matched_labels += 1
        if value_match:
            matched_values += 1
        label_details.append({
            "expected_label": norm_label,
            "expected_value": expected_val,
            "label_found": found,
            "generated_value": gen_attrs.get(norm_label, "") if found else None,
            "value_match": value_match,
        })

    total_expected = len(expected_attrs)
    result["checks"]["attributes"] = {
        "label_recall_pct": round(matched_labels / total_expected * 100, 1),
        "value_accuracy_pct": round(matched_values / total_expected * 100, 1),
        "details": label_details,
    }

    return result


def main():
    with open(ENRICHED_PATH, encoding="utf-8") as f:
        enriched_records = json.load(f)

    records_by_mpn = {r.get("Mfg_Part_Num"): r for r in enriched_records}

    all_results = []
    for mpn, truth in GROUND_TRUTH.items():
        if mpn not in records_by_mpn:
            print(f"⚠ {mpn} not found in enriched output — skipping")
            continue
        result = score_row(mpn, records_by_mpn[mpn], truth)
        all_results.append(result)

    # --- Print human-readable report ---
    for result in all_results:
        mpn = result["mfg_part_num"]
        checks = result["checks"]
        print(f"\n{'='*60}")
        print(f"BENCHMARK: {mpn}")
        print(f"{'='*60}")

        for field in ["MANUFACTURER_NAME", "BRAND_NAME"]:
            c = checks[field]
            status = "✓" if c["match"] else "✗"
            print(f"  {status} {field}: got {c['generated']!r} | expected {c['expected']!r}")

        c = checks["INVOICE_DESC_format"]
        status = "✓" if c["pass"] else "✗"
        print(f"  {status} INVOICE_DESC format: {c['generated']!r} {c['issues']}")

        c = checks["MOBILE_DESC_format"]
        status = "✓" if c["pass"] else "✗"
        print(f"  {status} MOBILE_DESC format: {c['generated']!r} {c['issues']}")

        c = checks["attributes"]
        print(f"  Attribute label recall:  {c['label_recall_pct']}%")
        print(f"  Attribute value accuracy: {c['value_accuracy_pct']}%")

    # --- Aggregate summary ---
    if all_results:
        avg_label_recall = sum(r["checks"]["attributes"]["label_recall_pct"] for r in all_results) / len(all_results)
        avg_value_acc = sum(r["checks"]["attributes"]["value_accuracy_pct"] for r in all_results) / len(all_results)
        mfr_matches = sum(1 for r in all_results if r["checks"]["MANUFACTURER_NAME"]["match"])
        brand_matches = sum(1 for r in all_results if r["checks"]["BRAND_NAME"]["match"])
        invoice_pass = sum(1 for r in all_results if r["checks"]["INVOICE_DESC_format"]["pass"])
        mobile_pass = sum(1 for r in all_results if r["checks"]["MOBILE_DESC_format"]["pass"])
        n = len(all_results)

        print(f"\n{'='*60}")
        print("SUMMARY (across benchmarked rows)")
        print(f"{'='*60}")
        print(f"  Manufacturer name exact match: {mfr_matches}/{n}")
        print(f"  Brand name exact match:        {brand_matches}/{n}")
        print(f"  INVOICE_DESC format pass:      {invoice_pass}/{n}")
        print(f"  MOBILE_DESC format pass:       {mobile_pass}/{n}")
        print(f"  Avg attribute label recall:    {avg_label_recall:.1f}%")
        print(f"  Avg attribute value accuracy:  {avg_value_acc:.1f}%")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nFull report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()