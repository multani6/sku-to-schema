import json
import subprocess
import shutil

# 1. Make a safe copy of tier2 data so we don't touch the real file
shutil.copy("../raw_data/html/tier2_llm_enriched.json", "../raw_data/html/tier2_test_copy.json")

with open("../raw_data/html/tier2_test_copy.json", encoding="utf-8") as f:
    data = json.load(f)

# 2. Inject a brand-new, never-seen-before Element row with a WRONG manufacturer
#    This simulates an evaluator's unseen dataset containing a new Element SKU
fake_row = dict(data[0])  # copy structure of an existing row
fake_row["Mfg_Part_Num"] = "EUF99SIMULATED"
fake_row["BRAND_NAME"] = "Element"
fake_row["MANUFACTURER_NAME"] = "Electrolux"  # deliberately WRONG, like the real bug
fake_row["_llm_confidence"] = "high"
data.append(fake_row)

with open("../raw_data/html/tier2_test_copy.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Injected fake unseen row: EUF99SIMULATED, Brand=Element, wrong Manufacturer=Electrolux")
print("Running enforce_manufacturer_consistency.py on the test copy...\n")

subprocess.run(["python", "enforce_manufacturer_consistency.py", "../raw_data/html/tier2_test_copy.json"])