"""
enrich_tier1_llm.py
---------------------
Uses Groq (Llama 3.3 70B) to fill the PENDING_LLM fields for the 10
Tier-1 (Dishwasher) rows: manufacturer/brand identification, all 6
description formats, item features, and up to 50 attribute triplets.

This does NOT touch PENDING_SOURCE fields (images, docs, pricing,
warranty, dimensions) — those need real manufacturer-source lookup,
not LLM generation, and are handled in a separate step.

v2 fix (13 Aug 2026): benchmark run against official ground truth showed
the model was echoing the Part_Manuf distributor code ("Appliance Dealers
Cooperative / APPDE") as the actual manufacturer/brand. Added explicit
disambiguation guidance so it reasons from the MPN prefix instead.

v3 fix (15 Aug 2026): switched MODEL from "llama-3.3-70b-versatile" to
"openai/gpt-oss-120b" — Groq is decommissioning llama-3.3-70b-versatile
on 16 Aug 2026 (confirmed via their official deprecation notice).
openai/gpt-oss-120b is Groq's recommended replacement. Tier 1 output
was already produced before this switch, so this only matters if the
script needs to be rerun.

Setup:
  pip install groq

Run:
  python scripts/enrich_tier1_llm.py
"""

import os
import json
import time
import re
from groq import Groq

SKELETON_PATH = "raw_data/html/tier1_skeleton.json"
TIER1_RAW_PATH = "raw_data/html/tier1_dishwashers.json"
OUTPUT_PATH = "raw_data/html/tier1_llm_enriched.json"

API_KEY = os.environ.get("GROQ_API_KEY", "PASTE_YOUR_KEY_HERE")
MODEL = "openai/gpt-oss-120b"

client = Groq(api_key=API_KEY)

SYSTEM_PROMPT = """You are a product-data enrichment specialist for Unilog, \
an industrial/appliance product content company. Given a terse, abbreviated \
raw catalogue description, you research your general knowledge of the named \
manufacturer/model and produce complete, standardised, commerce-ready \
content for a dishwasher product record.

CRITICAL — DO NOT CONFUSE THE DISTRIBUTOR WITH THE MANUFACTURER:
The "Part_Manuf" field you are given (e.g. "Appliance Dealers Cooperative \
(APPDE)") is a PURCHASING GROUP / DISTRIBUTOR code used internally by the \
catalogue. It is almost NEVER the actual appliance manufacturer or brand. \
You must independently determine the true manufacturer and brand by \
reasoning from the manufacturer part number (MPN) prefix and general \
industry knowledge of appliance model-numbering conventions. For example:
  - MPN prefixes like "PDSH", "PDT", "PDD" commonly indicate Frigidaire \
Professional/Gallery lines (parent company Rheem/Electrolux family)
  - MPN prefixes like "WDT", "WDTS", "WDF" commonly indicate Whirlpool
  - MPN prefixes like "LDPH", "LDT", "LDF" commonly indicate LG
  - MPN prefixes like "KDFM", "KDTS", "KDPS", "KDTM" commonly indicate KitchenAid
If you are genuinely uncertain of the true manufacturer/brand after this \
reasoning, set manufacturer_name and brand_name to "" and note it in \
confidence_notes — do NOT default to the distributor/Part_Manuf value.

STRICT FORMAT RULES (violating these is a serious quality failure):
- INVOICE_DESC: max 40 characters, ALL CAPS, extremely abbreviated \
(e.g. "DISHWASHER LEG 5 SST 120V 15A 50-1/4IN")
- MOBILE_DESC: 60-80 characters, format: "<Manufacturer>, <Brand>, <Item Type>, <Series>, <MPN>"
- SHORT_DESC: one line, format: "<Brand> <Series> <MPN> <Item Type> With <key feature>, <key attribute>, <key attribute>"
- LONG_DESC1: a single flowing sentence, comma-separated feature list, \
covering series, wash cycles, voltage/amperage, mounting, dimensions, \
sound level, material, and any additional info
- RETAIL_DESC: short marketing-style phrase, no MPN
- MARKETING_DESCRIPTION: 1-2 sentences of persuasive marketing copy, or \
leave as empty string "" if you don't have enough grounded detail to write \
a non-generic one — do NOT invent marketing claims you cannot support

RULES FOR ATTRIBUTES:
- Only include attributes you can reasonably infer from the model description \
or well-established knowledge of that manufacturer's product line for that model.
- Leave "value" as "" if you know the label applies to this product category \
but do not know the actual value (do NOT guess a number).
- Use standard UOM abbreviations (V, A, in, dBA, kW-hr, hr) — never full words.
- Do not fabricate certifications, colors, or model-specific numbers you are \
not reasonably confident about.

Respond with ONLY valid JSON, no markdown code fences, no commentary, \
matching exactly this schema:

{
  "manufacturer_name": "",
  "brand_name": "",
  "trade_name": "",
  "mobile_desc": "",
  "invoice_desc": "",
  "short_desc": "",
  "long_desc1": "",
  "retail_desc": "",
  "marketing_description": "",
  "item_features": ["", "..."],
  "with": "",
  "standard_approvals": "",
  "prop_65": "",
  "application": "",
  "includes": "",
  "product_name": "Dishwasher",
  "attributes": [
    {"label": "", "value": "", "uom": ""}
  ],
  "confidence": "high|medium|low",
  "confidence_notes": ""
}
"""

USER_PROMPT_TEMPLATE = """Raw catalogue row:
Mfg_Part_Num: {mfg_part_num}
Part_Desc: {part_desc}
Part_Manuf (distributor code, NOT the manufacturer — see instructions): {part_manuf}

Produce the enrichment JSON now."""


def strip_code_fences(text):
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text)
    text = re.sub(r"```$", "", text)
    return text.strip()


def call_llm(row):
    user_prompt = USER_PROMPT_TEMPLATE.format(
        mfg_part_num=row.get("Mfg_Part_Num", ""),
        part_desc=row.get("Part_Desc", ""),
        part_manuf=row.get("Part_Manuf", ""),
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        max_tokens=3000,
    )

    raw = response.choices[0].message.content
    cleaned = strip_code_fences(raw)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse failed for {row.get('Mfg_Part_Num')}: {e}")
        print(f"  Raw response (first 300 chars): {raw[:300]}")
        return None


def merge_into_skeleton(skeleton_record, llm_output):
    record = dict(skeleton_record)

    record["MANUFACTURER_NAME"] = llm_output.get("manufacturer_name", "")
    record["BRAND_NAME"] = llm_output.get("brand_name", "")
    record["TRADE_NAME"] = llm_output.get("trade_name", "")

    record["MOBILE_DESC"] = llm_output.get("mobile_desc", "")
    record["INVOICE_DESC"] = llm_output.get("invoice_desc", "")
    record["SHORT_DESC"] = llm_output.get("short_desc", "")
    record["LONG_DESC1"] = llm_output.get("long_desc1", "")
    record["RETAIL_DESC"] = llm_output.get("retail_desc", "")
    record["MARKETING_DESCRIPTION"] = llm_output.get("marketing_description", "")

    features = llm_output.get("item_features", [])
    for i in range(20):
        col = f"ITEM_FEATURES_{i+1}"
        record[col] = features[i] if i < len(features) else ""

    record["With"] = llm_output.get("with", "")
    record["Standard/Approvals"] = llm_output.get("standard_approvals", "")
    record["Prop 65"] = llm_output.get("prop_65", "")
    record["Application"] = llm_output.get("application", "")
    record["Includes"] = llm_output.get("includes", "")
    record["Product Name"] = llm_output.get("product_name", "Dishwasher")

    attributes = llm_output.get("attributes", [])
    for i in range(50):
        n = i + 1
        if i < len(attributes):
            attr = attributes[i]
            record[f"ATTRIBUTE_LABEL {n}"] = attr.get("label", "")
            record[f"ATTRIBUTE_VALUE {n}"] = attr.get("value", "")
            record[f"ATTRIBUTE_UOM {n}"] = attr.get("uom", "")
        else:
            record[f"ATTRIBUTE_LABEL {n}"] = ""
            record[f"ATTRIBUTE_VALUE {n}"] = ""
            record[f"ATTRIBUTE_UOM {n}"] = ""

    record["_llm_confidence"] = llm_output.get("confidence", "")
    record["_llm_confidence_notes"] = llm_output.get("confidence_notes", "")

    return record


def main():
    with open(SKELETON_PATH, encoding="utf-8") as f:
        skeleton_records = json.load(f)
    with open(TIER1_RAW_PATH, encoding="utf-8") as f:
        raw_rows = json.load(f)

    enriched = []
    for i, (skeleton_record, raw_row) in enumerate(zip(skeleton_records, raw_rows)):
        mpn = raw_row.get("Mfg_Part_Num", "")
        print(f"[{i+1}/{len(raw_rows)}] Enriching {mpn} ...")

        llm_output = call_llm(raw_row)
        if llm_output is None:
            print(f"  ✗ Skipped {mpn} due to parse failure — kept skeleton as-is")
            enriched.append(skeleton_record)
        else:
            merged = merge_into_skeleton(skeleton_record, llm_output)
            enriched.append(merged)
            print(f"  ✓ Confidence: {llm_output.get('confidence', 'n/a')}")

        time.sleep(1)  # be gentle on rate limits

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2)

    print(f"\nDone. Saved {len(enriched)} enriched records -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()