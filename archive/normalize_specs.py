"""
Day 5 — Specification Normalization
-------------------------------------
Maps inconsistent raw spec keys (scraped from IndiaMART) into the
fixed schema fields: voltage_rating, current_rating,
operating_temperature, mounting_type.

Design principles:
1. Priority-ordered key matching — more specific/reliable keys checked first.
2. Unit sanity-checking — if a value's unit doesn't match what's expected
   for that field (e.g. "220V" sitting inside a Current field), we do NOT
   blindly store it. We flag it and return "Not found" instead.
   This protects the Week 2 confidence-scoring layer from being built on
   silently-wrong data.
"""

import re

# ---------------------------------------------------------------------
# Priority-ordered raw key candidates for each schema field.
# Order matters: first match found in the product's spec dict wins.
# ---------------------------------------------------------------------

VOLTAGE_KEYS = [
    "Voltage Rating (V)", "Voltage Rating", "Rated Voltage",
    "Supply Voltage", "Power/Voltage", "Voltage Type", "Voltage",
]

CURRENT_KEYS = [
    "Rated Current", "Rated current", "Current Rating (A)",
    "Current Rating (Amp)", "Current Rating (In Amps)",
    "Contact Current Rating", "Current Rating", "Switching Current",
    "Current",
]

TEMP_KEYS = [
    "Operating Temperature", "Ambient temperature",
    "Temperature Resistance", "Temperature", "Storage",
]

MOUNTING_KEYS = [
    "Mounting Type", "Mounting Style", "Mounting Options", "Mounting",
]


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _first_match(specs: dict, key_list: list):
    """Return (matched_key, raw_value) for the first key_list entry
    found in specs, else (None, None)."""
    for key in key_list:
        if key in specs and specs[key] not in (None, "", "Not found"):
            return key, specs[key]
    return None, None


def _has_unit(value: str, unit_pattern: str) -> bool:
    """Check if value string contains the given unit pattern (case-insensitive)."""
    return bool(re.search(unit_pattern, value, re.IGNORECASE))


def clean_voltage(raw_value: str):
    """Validate + lightly standardize a voltage string.
    Rejects values that look like a Current field mistakenly holding
    a Voltage, or vice versa."""
    if raw_value is None:
        return "Not found"

    val = raw_value.strip()

    # Sanity check: does it actually look like a voltage?
    # Accept V, VDC, VAC, V DC, V AC, Volts
    looks_like_voltage = _has_unit(val, r"\bv(dc|ac)?\b|volts?")
    # Reject if it ONLY has an amp marker and no voltage marker (wrong field)
    looks_like_current_only = _has_unit(val, r"\ba\b|amp") and not looks_like_voltage

    if looks_like_current_only:
        return "Not found"  # flagged: wrong unit for this field

    if not looks_like_voltage:
        # No recognizable unit at all — still keep raw value but it stays
        # low-confidence; Week 2 scoring will handle that. For now normalize spacing.
        pass

    val = re.sub(r"\s+", " ", val)
    val = val.replace("Vac", "V AC").replace("VAC", "V AC")
    val = val.replace("Vdc", "V DC").replace("VDC", "V DC")
    return val


def clean_current(raw_value: str):
    """Validate + lightly standardize a current string.
    Rejects values that look like a Voltage mistakenly holding a Current,
    and flags physically implausible values (e.g. 10000A on a small MCB)."""
    if raw_value is None:
        return "Not found"

    val = raw_value.strip()

    looks_like_current = _has_unit(val, r"\ba\b|amp|ma\b")
    looks_like_voltage_only = _has_unit(val, r"\bv(dc|ac)?\b|volts?") and not looks_like_current

    if looks_like_voltage_only:
        return "Not found"  # flagged: wrong unit for this field

    # Plausibility check — industrial components in our 10 categories
    # realistically range roughly 0.001A to 2000A. Anything wildly above
    # that (e.g. "10000A" on a single-pole MCB) is almost certainly a
    # data-entry error on the seller's listing page, not a real spec.
    numbers = re.findall(r"\d+\.?\d*", val)
    if numbers:
        max_num = max(float(n) for n in numbers)
        if max_num > 5000 and "ma" not in val.lower():
            return "Not found"  # flagged: implausible value

    val = re.sub(r"\s+", " ", val)
    return val


def clean_temperature(raw_value: str):
    """Standardize temperature strings (handles ranges like '-40 to 90 C')."""
    if raw_value is None:
        return "Not found"

    val = raw_value.strip()
    val = re.sub(r"\s+", " ", val)
    val = val.replace("Degree C", "°C").replace("Deg C", "°C").replace("Celsius", "°C")
    return val


def clean_mounting(raw_value: str):
    """Standardize mounting type strings to Title Case, trimmed."""
    if raw_value is None:
        return "Not found"

    val = raw_value.strip()
    val = re.sub(r"\s+", " ", val)
    return val


# ---------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------

def normalize_specifications(raw_specs: dict) -> dict:
    """
    Takes the raw 'specifications' dict scraped from a product page and
    returns a dict with the four fixed schema fields, each cleaned and
    validated. Missing or invalid values become 'Not found' — same
    intentional-missing-data pattern used elsewhere in the pipeline.
    """
    result = {
        "voltage_rating": "Not found",
        "current_rating": "Not found",
        "operating_temperature": "Not found",
        "mounting_type": "Not found",
    }

    _, v_raw = _first_match(raw_specs, VOLTAGE_KEYS)
    result["voltage_rating"] = clean_voltage(v_raw)

    _, c_raw = _first_match(raw_specs, CURRENT_KEYS)
    result["current_rating"] = clean_current(c_raw)

    _, t_raw = _first_match(raw_specs, TEMP_KEYS)
    result["operating_temperature"] = clean_temperature(t_raw)

    _, m_raw = _first_match(raw_specs, MOUNTING_KEYS)
    result["mounting_type"] = clean_mounting(m_raw)

    return result


# ---------------------------------------------------------------------
# Quick self-test with a few real examples from products.json
# ---------------------------------------------------------------------

if __name__ == "__main__":
    test_cases = [
        {
            "Voltage": "12V", "Number Of Poles": "4 Pole",
            "Brand": "Schneider Electric", "Type": "Industrial Relay",
        },
        {
            "Current Rating (In Amps)": "10000A",  # implausible -> should flag
            "Power/Voltage": "240V/50 Hz",
        },
        {
            "Rated Current": "> 115 A", "Rated Voltage": "230 V",
            "Coil Voltage": "230 V AC", "Mounting Type": "PC Board",
        },
        {
            "Operating Temperature": "-40 Degree C ~ +70 Degree C",
            "Mounting Style": "Pin Type",
        },
    ]

    for i, specs in enumerate(test_cases, 1):
        print(f"\nTest case {i}: {specs}")
        print("Normalized:", normalize_specifications(specs))