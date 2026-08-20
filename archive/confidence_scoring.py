import json
from normalize_specs import (
    VOLTAGE_KEYS, CURRENT_KEYS, TEMP_KEYS, MOUNTING_KEYS,
    clean_voltage, clean_current, clean_temperature, clean_mounting,
)

# ---------------------------------------------------------------------
# Confidence weight for each raw key — based on how specific/reliable
# that key name is. A key literally called "Voltage Rating" is far more
# trustworthy than a generic "Voltage" field, which could be a coil
# voltage or something else entirely.
# ---------------------------------------------------------------------

VOLTAGE_CONFIDENCE = {
    "Voltage Rating (V)": 95, "Voltage Rating": 90, "Rated Voltage": 85,
    "Supply Voltage": 75, "Power/Voltage": 60, "Voltage Type": 50,
    "Voltage": 65,
}

CURRENT_CONFIDENCE = {
    "Rated Current": 90, "Rated current": 90, "Current Rating (A)": 90,
    "Current Rating (Amp)": 90, "Current Rating (In Amps)": 60,
    "Contact Current Rating": 55, "Current Rating": 85,
    "Switching Current": 70, "Current": 55,
}

TEMP_CONFIDENCE = {
    "Operating Temperature": 95, "Ambient temperature": 85,
    "Temperature Resistance": 70, "Temperature": 60, "Storage": 50,
}

MOUNTING_CONFIDENCE = {
    "Mounting Type": 95, "Mounting Style": 85,
    "Mounting Options": 70, "Mounting": 60,
}

# Business-relevance weighting: voltage/current are safety-critical
# procurement specs (wrong value = equipment damage). Mounting matters
# for installation fit. Temperature is a secondary concern for most
# categories in our catalog (only extreme-environment use cases need it).
FIELD_WEIGHTS = {
    "voltage_rating": 0.30,
    "current_rating": 0.30,
    "mounting_type": 0.25,
    "operating_temperature": 0.15,
}


def score_field(raw_specs, key_list, confidence_map, clean_fn):
    """
    Finds the first matching key for this field, cleans its value,
    and returns (cleaned_value, confidence_score, matched_key).
    If the cleaner rejects the value (returns 'Not found' despite raw
    data existing), confidence drops to 0 — this is our 'flagged for
    human review' signal.
    """
    for key in key_list:
        if key in raw_specs and raw_specs[key] not in (None, "", "Not found"):
            raw_value = raw_specs[key]
            cleaned = clean_fn(raw_value)
            if cleaned == "Not found":
                # Sanity check rejected it — zero confidence, needs human eyes
                return "Not found", 0, key
            base_confidence = confidence_map.get(key, 50)
            return cleaned, base_confidence, key

    # No matching key found at all in raw specs
    return "Not found", 0, None


def score_product(raw_specs: dict) -> dict:
    """
    Returns normalized values + confidence scores for all 4 fields,
    plus an overall product-level confidence score (weighted by
    business relevance — see FIELD_WEIGHTS above).
    """
    voltage_val, voltage_conf, voltage_key = score_field(
        raw_specs, VOLTAGE_KEYS, VOLTAGE_CONFIDENCE, clean_voltage)
    current_val, current_conf, current_key = score_field(
        raw_specs, CURRENT_KEYS, CURRENT_CONFIDENCE, clean_current)
    temp_val, temp_conf, temp_key = score_field(
        raw_specs, TEMP_KEYS, TEMP_CONFIDENCE, clean_temperature)
    mount_val, mount_conf, mount_key = score_field(
        raw_specs, MOUNTING_KEYS, MOUNTING_CONFIDENCE, clean_mounting)

    overall_confidence = round(
        voltage_conf * FIELD_WEIGHTS["voltage_rating"] +
        current_conf * FIELD_WEIGHTS["current_rating"] +
        mount_conf * FIELD_WEIGHTS["mounting_type"] +
        temp_conf * FIELD_WEIGHTS["operating_temperature"], 1
    )

    return {
        "voltage_rating": {"value": voltage_val, "confidence": voltage_conf, "matched_key": voltage_key},
        "current_rating": {"value": current_val, "confidence": current_conf, "matched_key": current_key},
        "operating_temperature": {"value": temp_val, "confidence": temp_conf, "matched_key": temp_key},
        "mounting_type": {"value": mount_val, "confidence": mount_conf, "matched_key": mount_key},
        "overall_confidence": overall_confidence,
    }


# ---------------------------------------------------------------------
# Run on the full dataset
# ---------------------------------------------------------------------

if __name__ == "__main__":
    with open("../raw_data/html/products.json", "r", encoding="utf-8") as f:
        products = json.load(f)

    REVIEW_THRESHOLD = 40  # products scoring below this need human review

    needs_review = []

    for product in products:
        raw_specs = product.get("specifications", {})
        scores = score_product(raw_specs)
        product["confidence_scores"] = scores

        if scores["overall_confidence"] < REVIEW_THRESHOLD:
            needs_review.append({
                "product_name": product["product_name"],
                "category": product["category"],
                "overall_confidence": scores["overall_confidence"],
                "source_url": product["source_url"],
            })

    with open("../raw_data/html/products_scored.json", "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

    with open("../raw_data/html/needs_review.json", "w", encoding="utf-8") as f:
        json.dump(needs_review, f, indent=2, ensure_ascii=False)

    avg_confidence = round(
        sum(p["confidence_scores"]["overall_confidence"] for p in products) / len(products), 1
    )

    print(f"Total products: {len(products)}")
    print(f"Average overall confidence: {avg_confidence}")
    print(f"Products flagged for human review (confidence < {REVIEW_THRESHOLD}): {len(needs_review)}")
    print(f"\nSaved: raw_data/html/products_scored.json")
    print(f"Saved: raw_data/html/needs_review.json")