"""
Tier 3 — Manufacturer -> Category mapping.

IMPORTANT: This table was built by manually inspecting real Part_Desc samples
for each manufacturer, not by guessing from the manufacturer/brand name alone.

Real finding during construction: "Milwaukee Accessory" and "Freud Inc" both
sell abrasive discs (cut-off discs, sanding belts) under those names, NOT
power tools. A naive brand-name-only classifier would have mis-categorized
154/916 rows (16.8% of Tier 3) into the wrong category. This is documented
as part of the iteration story.

Categories used (kept small and business-meaningful, matching what's
actually present in the Tier 3 data):
  - Lighting
  - Abrasives
  - Building Materials (decking, railing, roofing, sheathing)
  - Power Tools
  - Electrical (outlets, dimmers, boxes, fans)
  - Hand Tools & Accessories
  - Safety & PPE
  - Other / Needs Manual Classification
"""

# manufacturer name (exact string as it appears in Part_Manuf) -> category
MANUFACTURER_CATEGORY_MAP = {
    "Phillips Lighting (5831)": "Lighting",
    "Milwaukee Accessory (4031)": "Abrasives",              # verified: cut-off discs, not tools
    "Boise Cascade Building Materials (BOICA)": "Building Materials",
    "Kichler Lighting (KICLI)": "Lighting",
    "Parksite (6151)": "Building Materials",                 # Azek/Trex decking
    "Black & Decker/dewlt (2585)": "Power Tools",
    "Freud Inc (2435)": "Abrasives",                         # verified: Diablo sanding/cut-off discs
    "U S Lumber (3073)": "Building Materials",                # Trex/Biscayne decking, rail kits
    "Satco Prod Inc (5573)": "Lighting",
    "Makita Usa Inc (5142)": "Power Tools",
    "Southwire/g Turner (6603)": "Electrical",
    "Leviton Mfg Co (4927)": "Electrical",
    "Festool USA (FESTO)": "Power Tools",                    # note: also sells sanding sheets, but
                                                               # primary line is cordless power tools;
                                                               # ambiguous rows get keyword fallback
    "Tech Gear 5.7 Inc (TECGE)": "Safety & PPE",             # heated gloves
    "Kreg Tool Company (KRETO)": "Power Tools",
    "Edge Eyewear Inc (EDGSA)": "Safety & PPE",              # safety glasses
    "U S Tape Company (6694)": "Hand Tools & Accessories",   # mason line, tape
    "Mirka Abrasives Inc (MIRUS)": "Abrasives",
    "Palmer Donavin Mfg Company (PALDO)": "Building Materials",
    "Hunter Fan Co (4381)": "Electrical",                    # ceiling/wall fans
    "Premier Metals (PREME)": "Building Materials",          # metal roofing panels
    "Jam Industrial Supply LLC (JAMIN)": "Abrasives",        # 3M discs
    "Vessel Tools USA Inc (VESTO)": "Hand Tools & Accessories",
    "Oliver Machinery Company (OLIMA)": "Power Tools",       # shop machinery (jointers, planers)
    # "-" (no manufacturer given, 41 rows) is intentionally excluded here —
    # it is a mixed bucket (tire gauges, rail kits, etc.) and must go through
    # keyword-based fallback classification, not a manufacturer rule.
}

# Manufacturers below this row-count threshold in the top-25 list are still
# in this table above if they appeared in the top 25. Anything NOT in this
# dict (the long tail of ~50 manufacturers with <=3 rows each, ~70 rows total,
# plus "-") falls through to keyword-based classification.

CATEGORIES = [
    "Lighting",
    "Abrasives",
    "Building Materials",
    "Power Tools",
    "Electrical",
    "Hand Tools & Accessories",
    "Safety & PPE",
    "Other / Needs Manual Classification",
]