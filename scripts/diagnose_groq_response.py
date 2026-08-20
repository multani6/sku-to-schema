"""
diagnose_groq_response.py
--------------------------------------
One-off diagnostic: makes a single Groq call identical in shape to
tier3_enrich.py's call, but prints the RAW response object so we can
see exactly what's coming back (empty content? reasoning field
instead of content? an error message disguised as a 200 response?).

Run:  python scripts/diagnose_groq_response.py
"""

import os
from groq import Groq

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("ERROR: GROQ_API_KEY not set in this terminal session.")
    exit(1)

client = Groq(api_key=api_key)

prompt = """Respond with ONLY a JSON object, no other text, no markdown fences:
{"category": "Power Tools", "brand_name": "Bosch", "manufacturer_name": "Robert Bosch Tool Corporation", "short_desc": "Bosch Dishwasher Stainless Steel", "confidence": "FAMILY_INFERRED"}
"""

print("Sending test request to Groq (model: openai/gpt-oss-120b, max_tokens=400)...\n")

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.2,
    max_tokens=400,
)

print("=== FULL RAW RESPONSE OBJECT ===")
print(response)
print("\n=== message.content (what tier3_enrich.py tries to JSON-parse) ===")
print(repr(response.choices[0].message.content))
print("\n=== finish_reason ===")
print(response.choices[0].finish_reason)