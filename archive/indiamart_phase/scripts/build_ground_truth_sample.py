"""
build_ground_truth_sample.py
Day 7 - Ground Truth Benchmarking

Builds a stratified sample of products for manual verification against
real IndiaMART listings, to produce verified accuracy percentages per field.

Matches the actual structure of products_scored.json:
{
    "product_name": ...,
    "category": ...,
    "source_url": ...,
    "specifications": {...},
    "confidence_scores": {
        "voltage_rating": {"value": ..., "confidence": ..., "matched_key": ...},
        "current_rating": {...},
        "operating_temperature": {...},
        "mounting_type": {...},
        "overall_confidence": <float>
    }
}
"""

import json
import random
import hashlib
from pathlib import Path

# ---- CONFIG ----
INPUT_FILE = "raw_data/html/products_scored.json"
OUTPUT_FILE = "raw_data/html/ground_truth_sample.json"
SAMPLE_PER_CATEGORY = 5    # 5 x 10 known categories = 50 total
CONFIDENCE_THRESHOLD = 40  # same threshold used in confidence_scoring.py
RANDOM_SEED = 42           # fixed seed = reproducible sample (important for judges/Q&A)
FIELDS = ["voltage_rating", "current_rating", "operating_temperature", "mounting_type"]

random.seed(RANDOM_SEED)


def load_products(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_product_id(product):
    """
    No product_id field exists in the source data, so we derive a stable,
    reproducible ID from the source_url (short hash). Stable across runs
    since it's content-based, not order-based.
    """
    url = product.get("source_url", "")
    return "PID-" + hashlib.md5(url.encode("utf-8")).hexdigest()[:8]


def group_by_category(products):
    """
    Group products by category. Products with category == 'Not found'
    (known edge case - e.g. the Schneider contactor URL that detect_category()
    missed) are pulled out separately rather than silently mixed in, since
    including a mis-categorized product would break the 'category-balanced
    sample' claim.
    """
    grouped = {}
    uncategorized = []
    for p in products:
        cat = p.get("category", "unknown")
        if cat == "Not found" or not cat:
            uncategorized.append(p)
        else:
            grouped.setdefault(cat, []).append(p)
    return grouped, uncategorized


def get_overall_confidence(product):
    return product.get("confidence_scores", {}).get("overall_confidence", 0)


def stratified_sample(grouped, per_category):
    """
    For each category, pick a mix of high-confidence and low-confidence
    products so we can test whether confidence scores correlate with
    real-world accuracy.
    """
    sample = []

    for category, products in grouped.items():
        high_conf = [p for p in products if get_overall_confidence(p) >= CONFIDENCE_THRESHOLD]
        low_conf = [p for p in products if get_overall_confidence(p) < CONFIDENCE_THRESHOLD]

        n_high = min(len(high_conf), per_category // 2)
        n_low = min(len(low_conf), per_category - n_high)

        picked = []
        if n_high > 0:
            picked += random.sample(high_conf, n_high)
        if n_low > 0:
            picked += random.sample(low_conf, n_low)

        # Fill shortfall (e.g. a category has very few high-conf products)
        if len(picked) < per_category:
            picked_urls = {p.get("source_url") for p in picked}
            remaining_pool = [p for p in products if p.get("source_url") not in picked_urls]
            fill_needed = min(per_category - len(picked), len(remaining_pool))
            if fill_needed > 0:
                picked += random.sample(remaining_pool, fill_needed)

        sample.extend(picked)

    return sample


def build_verification_template(sample):
    """
    Attach empty fields for manual verification.
    You'll fill 'verified_*' fields by hand after checking the real
    IndiaMART listing at source_url.
    """
    template = []
    for p in sample:
        cs = p.get("confidence_scores", {})
        predicted = {}
        confidence_per_field = {}
        for field in FIELDS:
            field_data = cs.get(field, {})
            predicted[field] = field_data.get("value", "Not found")
            confidence_per_field[field] = field_data.get("confidence", 0)

        template.append({
            "product_id": make_product_id(p),
            "product_name": p.get("product_name"),
            "category": p.get("category"),
            "source_url": p.get("source_url"),
            "overall_confidence_score": cs.get("overall_confidence", 0),
            "confidence_per_field": confidence_per_field,

            # what the pipeline predicted
            "predicted": predicted,

            # to be filled manually by checking the real listing
            "verified": {field: None for field in FIELDS},

            # per-field: true (match), false (mismatch), "N/A" (both not found)
            "match_result": {field: None for field in FIELDS},

            "verification_notes": ""
        })
    return template


def main():
    products = load_products(INPUT_FILE)
    print(f"Loaded {len(products)} products from {INPUT_FILE}")

    grouped, uncategorized = group_by_category(products)
    print(f"Found {len(grouped)} valid categories: {list(grouped.keys())}")
    if uncategorized:
        print(f"NOTE: {len(uncategorized)} product(s) have category = 'Not found' "
              f"and were EXCLUDED from stratified sampling (known detect_category() edge case).")
        for u in uncategorized:
            print(f"   -> {u.get('product_name')} | {u.get('source_url')}")

    sample = stratified_sample(grouped, SAMPLE_PER_CATEGORY)
    print(f"\nSampled {len(sample)} products total (target was {SAMPLE_PER_CATEGORY * len(grouped)})")

    template = build_verification_template(sample)

    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    print(f"Ground truth sample saved to {OUTPUT_FILE}")

    # quick category-wise breakdown for sanity check
    cat_counts = {}
    for item in sample:
        cat_counts[item.get("category", "unknown")] = cat_counts.get(item.get("category", "unknown"), 0) + 1
    print("\nSample breakdown by category:")
    for cat, count in sorted(cat_counts.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()