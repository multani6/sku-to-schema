"""
verify_ground_truth.py
Day 7 - Ground Truth Benchmarking (Manual Verification CLI)

Interactive tool to manually verify predicted specs against real
IndiaMART listings. Run repeatedly - it resumes from where you left off.
"""

import json
from pathlib import Path

SAMPLE_FILE = "raw_data/html/ground_truth_sample.json"
FIELDS = ["voltage_rating", "current_rating", "operating_temperature", "mounting_type"]


def load_sample():
    with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_sample(data):
    with open(SAMPLE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_done(product):
    """A product is considered done once every field has a match_result set."""
    return all(product["match_result"][field] is not None for field in FIELDS)


def normalize(value):
    """Loose normalization so '230V' and '230 V' etc. don't get typed as mismatches."""
    if value is None:
        return ""
    return str(value).strip().lower().replace(" ", "")


def prompt_field(field, predicted_value):
    print(f"\n  Field: {field}")
    print(f"  Predicted: {predicted_value}")
    print("  Enter the REAL value from the listing.")
    print("  [Enter] = predicted is correct as-is | 'nf' = field not found on real page | 'skip' = skip this field for now")
    raw = input("  Verified value: ").strip()

    if raw.lower() == "skip":
        return None, None  # leave unresolved

    if raw == "":
        verified_value = predicted_value
    elif raw.lower() == "nf":
        verified_value = "Not found"
    else:
        verified_value = raw

    pred_norm = normalize(predicted_value)
    ver_norm = normalize(verified_value)

    if pred_norm == "notfound" and ver_norm == "notfound":
        match = "N/A"
    elif pred_norm == ver_norm:
        match = True
    else:
        match = False

    return verified_value, match


def verify_product(product, index, total):
    print("\n" + "=" * 70)
    print(f"[{index}/{total}] {product['product_name']}  (category: {product['category']})")
    print(f"URL: {product['source_url']}")
    print("Open this URL in your browser, then verify each field below.")

    for field in FIELDS:
        if product["match_result"][field] is not None:
            continue  # already done in a previous run
        predicted_value = product["predicted"][field]
        verified_value, match = prompt_field(field, predicted_value)
        if match is None:
            continue  # skipped, stays unresolved
        product["verified"][field] = verified_value
        product["match_result"][field] = match

    note = input("\n  Any verification notes for this product? (Enter to skip): ").strip()
    if note:
        product["verification_notes"] = note


def print_summary(data):
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    field_stats = {f: {"match": 0, "mismatch": 0, "na": 0, "total_checked": 0} for f in FIELDS}

    for product in data:
        for field in FIELDS:
            result = product["match_result"][field]
            if result is None:
                continue
            field_stats[field]["total_checked"] += 1
            if result == "N/A":
                field_stats[field]["na"] += 1
            elif result is True:
                field_stats[field]["match"] += 1
            else:
                field_stats[field]["mismatch"] += 1

    for field, stats in field_stats.items():
        checked = stats["total_checked"]
        if checked == 0:
            print(f"{field}: not verified yet")
            continue
        # Accuracy computed only over cases where a real value existed to compare
        comparable = stats["match"] + stats["mismatch"]
        accuracy = (stats["match"] / comparable * 100) if comparable > 0 else None
        acc_str = f"{accuracy:.1f}%" if accuracy is not None else "N/A (no comparable cases)"
        print(f"{field}: checked={checked}, match={stats['match']}, "
              f"mismatch={stats['mismatch']}, both-not-found={stats['na']}, accuracy={acc_str}")

    done_count = sum(1 for p in data if is_done(p))
    print(f"\nProducts fully verified: {done_count}/{len(data)}")


def main():
    data = load_sample()
    total = len(data)

    pending = [p for p in data if not is_done(p)]
    print(f"Loaded {total} products. {len(pending)} still need verification.")

    if not pending:
        print("All products already verified!")
        print_summary(data)
        return

    print("\nTip: type 'quit' at any 'Verified value' prompt to stop and save progress.\n")

    for i, product in enumerate(pending, 1):
        try:
            verify_product(product, i, len(pending))
        except (EOFError, KeyboardInterrupt):
            print("\n\nStopped early. Saving progress...")
            break
        save_sample(data)  # save after every product, not just at the end

    save_sample(data)
    print("\nProgress saved.")
    print_summary(data)


if __name__ == "__main__":
    main()