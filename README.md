# SKU → Schema

**AI-Powered Product Intelligence for Industrial Commerce** — built for UniHack 2026

Turns 1,000 raw, messy distributor rows into the official 252-column commerce-ready catalog schema, with explainable confidence tags and honest data-quality flags instead of fabricated values.

**Live demo:** https://shubman-kaur.github.io/sku-to-schema/

---

## The problem

Distributor product data arrives as short, inconsistent, often abbreviated text — no standard brand field, no manufacturer master list, no attribute structure. The task: transform this into a fully structured 252-column catalog schema, at scale, without inventing data that isn't there.

Only two files were provided by the organizers: a 1,000-row raw input CSV and a 252-column expected-output schema with two worked examples. No lookup tables, no manufacturer master list, no UOM standards — everything had to be engineered from the data itself.

## Approach — a 3-tier depth gradient

Rather than applying uniform shallow processing to all 1,000 rows, the pipeline allocates depth deliberately based on where it pays off:

| Tier | Rows | Depth | Why |
|---|---|---|---|
| **Tier 1** | 10 dishwashers | Full 252-column depth | Directly benchmarked against the organizers' own worked examples — this is the only tier where accuracy against ground truth can actually be measured |
| **Tier 2** | 74 major appliances | Medium depth | Dryers, washers, fridges, ranges, microwaves — high-value, well-identified SKUs |
| **Tier 3** | 916 mixed industrial rows | Light depth, honest flagging | Rough classification, one solid description, and explicit `DATA_QUALITY_FLAG`s where the source text is too generic to safely infer specs |

This is a deliberate architectural choice, not a shortcut: full-depth processing on all 1,000 rows wasn't going to be reliable given the source data quality, and a shallow pass on everything would waste the signal available in the better-identified SKUs.

## What makes this different

**1. It finds and fixes its own errors, and says so.**
35 rows were manually verified against real manufacturer records. Four real errors turned up — brand/manufacturer prefix collisions (e.g. `PD-` prefix rows wrongly attributed to Electrolux instead of GE Appliances/Haier). All four were tagged **HIGH confidence** by the model. The confidence-scoring system did not catch them — only independent verification did. That's documented as a known limitation, not hidden.

**2. Confidence claims are labeled honestly.**
An independent rule-based calibration check agreed with 73/73 high-confidence rows. That 100% figure is reported with an explicit caveat: the rule table's patterns were derived from the same prefix hints already given to the LLM, so this is *internal consistency*, not true external validation — and it's labeled that way everywhere it's cited.

**3. Fabrication is treated as worse than an honest gap.**
Where source data is too thin to responsibly fill a field (roughly 130 of the 916 Tier-3 rows), the pipeline flags it — `GENERIC_DESC_MPN_REQUIRED` — instead of guessing. The organizers' own scoring guidance states fabricated values score zero; this design choice follows directly from that.

**4. A real bug that majority-vote logic would have missed.**
Early manufacturer resolution used majority-vote across similar MPN patterns — which confidently misattributed Speed Queen dryers to Whirlpool. Fixed with an authoritative override table. Statistical agreement isn't the same as correctness.

## Architecture

```
raw_data/          → organizer-provided input + expected output
scripts/           → full pipeline: enrichment, classification, calibration,
                      ground-truth verification, bug fixes, dashboard generation
outputs/           → final submission CSV, verification worksheet,
                      confidence calibration report
archive/            → earlier IndiaMART-scraping iteration, kept as part of
                      the build history (pivoted to the official dataset)
index.html          → interactive dashboard (confidence ledger, category
                      breakdown, review queue, live enrichment walkthrough)
live_demo.html       → standalone version of the live walkthrough widget
```

**Pipeline:** Python + Groq API (LLM enrichment) → rule-based classification cascade (manufacturer rule → keyword fallback → LLM, in that cost order) → confidence calibration → manual ground-truth verification → merge into final 252-column CSV.

**Dashboard:** Static HTML + React (CDN) + Tailwind (CDN) — zero build step, zero install, deployed on GitHub Pages.

## Results

- **1,000 / 1,000** rows delivered in the official 252-column schema
- Tier 1 attribute accuracy: **56.2%** vs. **12.5%** for an LLM-only baseline, benchmarked against the organizers' worked examples
- **84%** of Tier 3 rows classified at zero LLM cost via rule-based cascade
- **0** LLM call failures across the full run
- **4** real manufacturer-attribution bugs found and fixed via manual ground-truth verification, all previously tagged high-confidence

## Honest limitations

- Ground-truth verification covers 35 of 1,000 rows (Tier 1 + Tier 2 sample) — Tier 3 correctness relies on the classification cascade and confidence flags, not manual spot-checks at the same depth.
- The 100% internal-consistency figure from calibration should not be read as independent validation (see above).
- Business-impact timing (~4–5 min automated vs. ~333 hours manual baseline) is a transparent *estimate* based on LLM call volume and typical API latency, not a measured production log — production timing logs were lost to a checkpoint overwrite during development.

## Running it locally

```bash
git clone https://github.com/shubman-kaur/sku-to-schema.git
cd sku-to-schema
python -m http.server 8000
```

Then open `http://localhost:8000/index.html`. No build step, no dependencies to install — the dashboard loads React, Tailwind, and fonts from CDN at runtime.

To re-run the enrichment pipeline itself, scripts in `scripts/` require a Groq API key set as the `GROQ_API_KEY` environment variable.