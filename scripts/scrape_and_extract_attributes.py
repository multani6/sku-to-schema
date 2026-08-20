"""
scrape_and_extract_attributes.py
-----------------------------------
RAG-style attribute extraction: fetches the REAL manufacturer product
page for each Tier-1 row, then asks Groq to extract attributes ONLY
from that real page text — not from the model's memory. This is what
actually fixes the low attribute-accuracy problem in a way that
scales to Tier 2 and Tier 3 too (same script, different input list).

Setup:
  pip install groq requests beautifulsoup4

Run (from the project root, e.g. via scripts/run_pipeline.py, or
directly as `python scripts/scrape_and_extract_attributes.py` from
the project root — NOT from inside scripts/):
  python scripts/scrape_and_extract_attributes.py

Note (20 Aug 2026): this file was briefly patched to use "../"-prefixed
paths on the assumption the pipeline should run from inside scripts/.
A full scan of every script's path constants showed that's backwards —
every other script in the pipeline uses root-relative paths. Reverted
to the original, correct root-relative paths below.
"""

import os
import json
import time
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq

FINAL_PATH = "raw_data/html/tier1_final.json"
SOURCE_DATA_MODULE = "tier1_source_data"
OUTPUT_PATH = "raw_data/html/tier1_final.json"  # overwrite in place

API_KEY = os.environ.get("GROQ_API_KEY", "PASTE_YOUR_KEY_HERE")
MODEL = "openai/gpt-oss-120b"
client = Groq(api_key=API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

EXTRACTION_SYSTEM_PROMPT = """You are a precise data-extraction tool. You will \
be given raw text scraped from a manufacturer's product page for a specific \
dishwasher model. Extract ONLY facts that are EXPLICITLY STATED in the \
provided text. Do NOT use outside knowledge. Do NOT guess or infer values \
that aren't directly written in the text.

Respond with ONLY valid JSON, no markdown fences, no commentary, matching:

{
  "attributes": [
    {"label": "", "value": "", "uom": ""}
  ],
  "list_price": "",
  "warranty": "",
  "extraction_notes": ""
}

If the text doesn't clearly state a fact, leave the field empty rather than \
guessing. Prefer standard UOM abbreviations (in, V, A, dBA, cu ft)."""


def fetch_page_text(url, max_chars=6000):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"    ⚠ Fetch failed: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


def strip_code_fences(text):
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text)
    text = re.sub(r"```$", "", text)
    return text.strip()


def extract_from_text(mpn, page_text):
    user_prompt = f"Product model number: {mpn}\n\nScraped page text:\n{page_text}"

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content
    cleaned = strip_code_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"    ⚠ JSON parse failed: {e}")
        return None


def merge_new_attributes(record, extracted):
    existing_labels = {
        record.get(f"ATTRIBUTE_LABEL {i}", "").strip().lower()
        for i in range(1, 51)
    }

    new_attrs = extracted.get("attributes", [])
    added = 0
    for attr in new_attrs:
        label = attr.get("label", "").strip()
        if not label or label.lower() in existing_labels:
            continue  # skip duplicates and empty labels
        for i in range(1, 51):
            if not record.get(f"ATTRIBUTE_LABEL {i}", "").strip():
                record[f"ATTRIBUTE_LABEL {i}"] = label
                record[f"ATTRIBUTE_VALUE {i}"] = attr.get("value", "")
                record[f"ATTRIBUTE_UOM {i}"] = attr.get("uom", "")
                existing_labels.add(label.lower())
                added += 1
                break

    if extracted.get("list_price") and not record.get("List Price"):
        record["List Price"] = extracted["list_price"]
    if extracted.get("warranty") and not record.get("Warranty"):
        record["Warranty"] = extracted["warranty"]

    return record, added


def main():
    import sys
    sys.path.insert(0, "scripts")
    from tier1_source_data import SOURCE_DATA

    with open(FINAL_PATH, encoding="utf-8") as f:
        records = json.load(f)

    for record in records:
        mpn = record.get("Mfg_Part_Num", "")
        source = SOURCE_DATA.get(mpn, {})
        url = source.get("mfr_url") or (source.get("ref_urls") or [None])[0]

        print(f"[{mpn}] Fetching {url} ...")
        if not url:
            print("  ⚠ No URL available — skipping")
            continue

        page_text = fetch_page_text(url)
        if not page_text:
            continue

        extracted = extract_from_text(mpn, page_text)
        if extracted is None:
            continue

        record_updated, added = merge_new_attributes(record, extracted)
        print(f"  ✓ Added {added} new grounded attributes")

        time.sleep(1)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"\nDone. Updated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()