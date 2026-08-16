import json

# ⚠️ Apni Tier 2 enriched file ka sahi path yahan daal do
INPUT_FILE = "../raw_data/html/tier2_llm_enriched.json"
OUTPUT_FILE = "../outputs/brand_consistency_flags.csv"

# Known brand -> manufacturer mapping (jo bhi brands tumhare data mein hain, unko yahan add karte raho)
KNOWN_BRANDS = [
    "Element", "GE", "Frigidaire", "Whirlpool", "LG", "Samsung", "Sharp",
    "Speed Queen", "Maytag", "KitchenAid", "Beko", "Cafe", "Café",
    "Electrolux", "Bosch", "Haier"
]

def find_brands_in_text(text):
    """Text mein se koi bhi known brand naam dhoondo"""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for brand in KNOWN_BRANDS:
        if brand.lower() in text_lower:
            found.append(brand)
    return found

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    flagged_rows = []

    for row in data:
        mpn = row.get("Mfg_Part_Num", "")
        part_desc = row.get("Part_Desc", "")
        assigned_brand = row.get("BRAND_NAME", "")
        assigned_mfr = row.get("MANUFACTURER_NAME", "")

        # Part_Desc mein jo bhi brand naam mile
        brands_in_desc = find_brands_in_text(part_desc)

        # Agar description mein koi brand mila HAI, lekin wo assigned brand se match nahi karta
        if brands_in_desc:
            match_found = any(
                b.lower() == assigned_brand.lower() for b in brands_in_desc
            )
            if not match_found:
                flagged_rows.append({
                    "Mfg_Part_Num": mpn,
                    "Part_Desc": part_desc,
                    "Assigned_Brand": assigned_brand,
                    "Assigned_Manufacturer": assigned_mfr,
                    "Brand_Found_In_Description": ", ".join(brands_in_desc),
                })

    print(f"Total rows checked: {len(data)}")
    print(f"Flagged rows (possible mismatch): {len(flagged_rows)}")
    print("-" * 60)

    for r in flagged_rows:
        print(f"MPN: {r['Mfg_Part_Num']}")
        print(f"  Part_Desc says: '{r['Part_Desc']}'")
        print(f"  But assigned brand: {r['Assigned_Brand']} (mfr: {r['Assigned_Manufacturer']})")
        print(f"  Brand mentioned in desc: {r['Brand_Found_In_Description']}")
        print()

    # CSV mein bhi save kar do
    import csv
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        if flagged_rows:
            writer = csv.DictWriter(f, fieldnames=flagged_rows[0].keys())
            writer.writeheader()
            writer.writerows(flagged_rows)
    print(f"Saved flagged rows to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()