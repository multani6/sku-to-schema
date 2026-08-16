import json
from normalize_specs import normalize_specifications

# Load the scraped products
with open("../raw_data/html/products.json", "r", encoding="utf-8") as f:
    products = json.load(f)

# Normalize specifications for every product
for product in products:
    raw_specs = product.get("specifications", {})
    normalized = normalize_specifications(raw_specs)
    product["normalized_specs"] = normalized

# Save to a new file (keeps original products.json untouched)
with open("../raw_data/html/products_normalized.json", "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2, ensure_ascii=False)

# Print a quick summary
total = len(products)
found = {"voltage_rating": 0, "current_rating": 0, "operating_temperature": 0, "mounting_type": 0}
for product in products:
    norm = product["normalized_specs"]
    for field in found:
        if norm[field] != "Not found":
            found[field] += 1

print(f"Total products processed: {total}")
print("\nField coverage:")
for field, count in found.items():
    print(f"  {field}: {count}/{total}")

print(f"\nSaved output to: raw_data/html/products_normalized.json")