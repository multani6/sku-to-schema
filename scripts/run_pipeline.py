"""
run_pipeline.py
--------------------------------------
Master orchestration script — runs the full UniHack product-enrichment
pipeline end-to-end, in the correct dependency order, with ONE command.

Why this exists: the pipeline was originally built as 25+ separate
scripts run manually in sequence. That's fragile for an evaluator (or
anyone re-running this on a fresh/unseen dataset) — one missed step or
wrong order silently breaks the run. This script makes the whole
pipeline traceable and reproducible with a single command, per the
UniHack live-session guidance that submissions must be end-to-end
executable from an evaluator's perspective.

IMPORTANT — run this from the PROJECT ROOT, not from inside scripts/:
    python scripts/run_pipeline.py

Every other script in scripts/ (build_schema_map.py, enrich_tier1_llm.py,
etc.) uses root-relative paths like "raw_data/html/..." and "outputs/...".
That is the pipeline's actual, consistent convention — confirmed by
scanning every script's path constants on 20 Aug 2026. This script
respects that convention: it calls each script as "scripts/<name>.py"
and passes root-relative paths as args, so python resolves everything
correctly when you run it from unihack-project/ itself.

Notes:
  - LLM-calling steps (enrich_tier1_llm, enrich_tier2_llm, tier3_enrich)
    are SKIPPED AUTOMATICALLY if their output file already exists, so
    re-running this script doesn't burn API quota re-doing work that's
    already done. Delete the relevant output file if you want to force
    a re-run of a specific stage.
  - Requires GROQ_API_KEY to be set as an environment variable if any
    LLM stage needs to actually run.

Changelog (18 Aug 2026 — found via full unseen-dataset test):
  - Added Stage 4.1b: enforce_manufacturer_consistency.py for Tier 3.
    This step existed for Tier 1/2 but was never wired up for Tier 3
    (916 of 1000 rows) — meaning distributor-code-as-manufacturer bugs
    could slip through on 92% of the dataset undetected. Testing on
    a fabricated unseen dataset caught this before submission.
  - Added Stage 4.2b: flag_hallucinated_terms.py. Also found via the
    same unseen-dataset test: SHORT_DESC occasionally includes a word
    that isn't anywhere in the raw source description (e.g. "water
    filter" invented for a row whose only relevant text was the brand
    name "Element"). This doesn't try to prevent that — LLM hallucination
    isn't fully preventable — it flags it for review instead, so nothing
    unverified reaches the final submission silently.

Changelog (20 Aug 2026 — found while doing the Day 2 fresh/unseen-
dataset run):
  - Added Stage 3.3: check_brand_consistency.py for Tier 2. This step
    was documented as part of the locked pipeline order but had been
    dropped from this orchestration script — it was never actually
    being run. It's a read-only diagnostic (writes
    outputs/brand_consistency_flags.csv, does not modify the enriched
    data) that cross-checks BRAND_NAME against brand mentions found in
    Part_Desc, and must run BEFORE enforce_manufacturer_consistency so
    its report reflects pre-correction state.
  - CORRECTED A WRONG ASSUMPTION: earlier today, individual scripts
    (scrape_and_extract_attributes.py, benchmark_tier1_ground_truth.py,
    diagnose_tier2_quality.py) were patched to add "../" to their path
    constants, on the assumption that the pipeline should be run from
    inside scripts/. A full scan of every script's path constants
    showed every other script in the pipeline (20+ files) uses
    root-relative paths with no "../" — meaning that assumption was
    backwards. Those three scripts have been reverted to their
    original root-relative paths, and this script itself is now the
    only place that needs to account for being invoked as
    "scripts/run_pipeline.py" — it does so by prefixing every script
    call with "scripts/" while leaving all file-path args root-relative.
"""

import subprocess
import sys
import os

def run(script, args=None, skip_if_exists=None, label=None):
    """
    Runs `python scripts/<script> [args]`. If skip_if_exists is given
    and that file already exists, the stage is skipped (saves LLM API
    quota on already-completed runs).
    """
    display = label or script
    if skip_if_exists and os.path.exists(skip_if_exists):
        print(f"\n[SKIP] {display} — output already exists at {skip_if_exists}")
        return
    print(f"\n{'='*70}\n[RUN] {display}\n{'='*70}")
    cmd = [sys.executable, os.path.join("scripts", script)] + (args or [])
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n❌ FAILED at: {display} (exit code {result.returncode})")
        print("Pipeline stopped. Fix the error above and re-run — completed")
        print("stages will be skipped automatically where applicable.")
        sys.exit(1)


def main():
    print("UniHack Product Intelligence Pipeline — full run")
    print("=" * 70)

    # ---- Stage 0: Schema ----
    run("build_schema_map.py",
        skip_if_exists="schema/schema_map.json",
        label="Stage 0: Build schema map")

    # ---- Stage 1: Segmentation ----
    run("segment_categories.py",
        skip_if_exists="raw_data/html/tier1_dishwashers.json",
        label="Stage 1: Segment input into Tier 1/2/3")

    # ---- Stage 2: Tier 1 (full depth) ----
    run("build_tier1_skeleton.py",
        skip_if_exists="raw_data/html/tier1_skeleton.json",
        label="Stage 2.1: Build Tier 1 skeleton")
    run("enrich_tier1_llm.py",
        skip_if_exists="raw_data/html/tier1_llm_enriched.json",
        label="Stage 2.2: LLM-enrich Tier 1 [uses Groq API]")
    run("enforce_manufacturer_consistency.py",
        args=["raw_data/html/tier1_llm_enriched.json"],
        label="Stage 2.3: Enforce brand/manufacturer consistency (Tier 1)")
    run("merge_tier1_source_data.py",
        skip_if_exists="raw_data/html/tier1_final.json",
        label="Stage 2.4: Merge verified source data into Tier 1")
    run("scrape_and_extract_attributes.py",
        label="Stage 2.5: RAG-extract attributes from real manufacturer pages [uses Groq API]")
    run("benchmark_tier1_ground_truth.py",
        label="Stage 2.6: Benchmark Tier 1 against official ground truth")
    run("export_tier1_csv.py",
        skip_if_exists="raw_data/html/tier1_output.csv",
        label="Stage 2.7: Export Tier 1 CSV")

    # ---- Stage 3: Tier 2 (medium depth) ----
    run("build_tier2_skeleton.py",
        skip_if_exists="raw_data/html/tier2_skeleton.json",
        label="Stage 3.1: Build Tier 2 skeleton")
    run("enrich_tier2_llm.py",
        skip_if_exists="raw_data/html/tier2_llm_enriched.json",
        label="Stage 3.2: LLM-enrich Tier 2 [uses Groq API]")
    run("check_brand_consistency.py",
        label="Stage 3.3: Check brand consistency vs Part_Desc (Tier 2, diagnostic only)")
    run("enforce_manufacturer_consistency.py",
        args=["raw_data/html/tier2_llm_enriched.json"],
        label="Stage 3.4: Enforce brand/manufacturer consistency (Tier 2)")
    run("diagnose_tier2_quality.py",
        label="Stage 3.5: Diagnose Tier 2 quality")
    run("export_tier2_csv.py",
        skip_if_exists="raw_data/html/tier2_output.csv",
        label="Stage 3.6: Export Tier 2 CSV")

    # ---- Stage 4: Tier 3 (light depth, 916 rows) ----
    run("tier3_enrich.py",
        skip_if_exists="outputs/tier3_enriched.json",
        label="Stage 4.1: Enrich Tier 3 (rule cascade + LLM) [uses Groq API]")
    run("enforce_manufacturer_consistency.py",
        args=["outputs/tier3_enriched.json"],
        label="Stage 4.1b: Enforce brand/manufacturer consistency (Tier 3)")
    run("flag_generic_descriptions.py",
        label="Stage 4.2: Flag generic/duplicate descriptions")
    run("flag_hallucinated_terms.py",
        label="Stage 4.2b: Flag possible SHORT_DESC hallucination")
    run("diagnose_tier3_duplicate_descriptions.py",
        label="Stage 4.3: Diagnose Tier 3 duplicate descriptions")
    run("export_tier3_csv.py",
        skip_if_exists="outputs/tier3_output.csv",
        label="Stage 4.4: Export Tier 3 CSV")

    # ---- Stage 5: Final merge ----
    run("merge_final_output.py",
        label="Stage 5: Merge Tier 1+2+3 into final submission CSV")

    # ---- Stage 6: Post-hoc analysis (pitch/Q&A support artifacts) ----
    run("generate_dashboard_data.py",
        label="Stage 6.1: Generate dashboard data")
    run("calibrate_confidence.py",
        label="Stage 6.2: Calibrate confidence (Tier 1/2 rule cross-check)")
    run("sample_for_manual_verification.py",
        label="Stage 6.3: Sample rows for manual verification")

    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETE")
    print("Final submission: outputs/unihack_final_submission.csv")
    print("=" * 70)


if __name__ == "__main__":
    main()