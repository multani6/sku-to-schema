"""
test_groq_connection.py
-------------------------
Quick sanity check that the Groq API key works and returns a response.

Setup:
  pip install groq

Run:
  python scripts/test_groq_connection.py
"""

import os
from groq import Groq

# Option A: set your key as an environment variable (recommended)
#   Windows PowerShell:  $env:GROQ_API_KEY="your_key_here"
# Option B: paste it directly below (only for quick local testing —
#           don't commit this to GitHub if you do this)
API_KEY = os.environ.get("GROQ_API_KEY", "PASTE_YOUR_KEY_HERE")

client = Groq(api_key=API_KEY)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "user", "content": "Reply with exactly: Groq connection successful."}
    ],
    temperature=0,
)

print(response.choices[0].message.content)