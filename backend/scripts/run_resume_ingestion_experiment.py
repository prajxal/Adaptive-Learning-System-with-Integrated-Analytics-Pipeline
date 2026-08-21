"""
Resume Ingestion Experiment
===========================
Batch-runs the improved resume extraction pipeline over all PDFs in
ENGINEERING/ and reports extraction quality metrics.

This script does NOT write to the database — it exercises only the
extraction layer (extract_text_from_pdf + extract_skills_with_semantic_fallback)
so no real user_id or DB connection is required.

Usage:
    cd <repo_root>
    python backend/scripts/run_resume_ingestion_experiment.py

Output:
    backend/experiments/resume_ingestion_results.json
    Terminal summary
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow bare imports from backend/
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from services.resume_parser import extract_text_from_pdf  # noqa: E402
from services.skill_extractor import extract_skills_with_semantic_fallback  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINEERING_DIR = REPO_ROOT / "ENGINEERING"
OUTPUT_DIR = BACKEND_DIR / "experiments"
RESULTS_PATH = OUTPUT_DIR / "resume_ingestion_results.json"


def run_experiment() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(ENGINEERING_DIR.glob("*.pdf"))
    total = len(pdfs)
    print(f"[Experiment] Found {total} PDFs in {ENGINEERING_DIR}\n")

    per_resume: list[dict] = []
    skill_counter: Counter = Counter()
    all_confidences: list[float] = []
    errors: list[str] = []

    for i, pdf_path in enumerate(pdfs, start=1):
        print(f"[{i:3d}/{total}] Processing {pdf_path.name} ...", end=" ", flush=True)
        try:
            text = extract_text_from_pdf(str(pdf_path))
            results = extract_skills_with_semantic_fallback(text)
        except Exception as exc:
            print(f"ERROR: {exc}")
            errors.append({"file": pdf_path.name, "error": str(exc)})
            per_resume.append({
                "file": pdf_path.name,
                "skills_found": 0,
                "skills": [],
                "error": str(exc),
            })
            continue

        skills = [r["skill"] for r in results]
        confidences = [r["confidence"] for r in results]

        for skill in skills:
            skill_counter[skill] += 1
        all_confidences.extend(confidences)

        per_resume.append({
            "file": pdf_path.name,
            "skills_found": len(skills),
            "skills": skills,
            "avg_confidence": round(statistics.mean(confidences), 4) if confidences else 0.0,
        })
        print(f"{len(skills)} skills detected")

    # -------------------------------------------------------------------------
    # Aggregate statistics
    # -------------------------------------------------------------------------
    processed = len(per_resume)
    with_skills = sum(1 for r in per_resume if r["skills_found"] > 0)
    extraction_rate = with_skills / processed * 100 if processed else 0.0
    skill_counts = [r["skills_found"] for r in per_resume]
    avg_skills = statistics.mean(skill_counts) if skill_counts else 0.0
    median_skills = statistics.median(skill_counts) if skill_counts else 0.0
    avg_confidence = statistics.mean(all_confidences) if all_confidences else 0.0
    median_confidence = statistics.median(all_confidences) if all_confidences else 0.0
    top_20 = skill_counter.most_common(20)

    summary = {
        "total_resumes": processed,
        "resumes_with_skills": with_skills,
        "resumes_without_skills": processed - with_skills,
        "extraction_success_rate_pct": round(extraction_rate, 2),
        "avg_skills_per_resume": round(avg_skills, 2),
        "median_skills_per_resume": round(median_skills, 2),
        "avg_confidence": round(avg_confidence, 4),
        "median_confidence": round(median_confidence, 4),
        "top_20_skills": [{"skill": s, "count": c} for s, c in top_20],
        "errors": errors,
    }

    output = {"summary": summary, "per_resume": per_resume}

    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)

    # -------------------------------------------------------------------------
    # Terminal summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("RESUME INGESTION EXPERIMENT — RESULTS")
    print("=" * 60)
    print(f"  Total resumes processed    : {processed}")
    print(f"  Resumes with skills        : {with_skills}")
    print(f"  Resumes without skills     : {processed - with_skills}")
    print(f"  Extraction success rate    : {extraction_rate:.1f}%")
    print(f"  Avg skills per resume      : {avg_skills:.2f}")
    print(f"  Median skills per resume   : {median_skills:.1f}")
    print(f"  Avg confidence score       : {avg_confidence:.4f}")
    print(f"  Median confidence score    : {median_confidence:.4f}")
    if errors:
        print(f"  Parse errors               : {len(errors)}")
    print()
    print("  Top 20 detected skills:")
    for rank, (skill, count) in enumerate(top_20, start=1):
        bar = "#" * min(count, 40)
        print(f"    {rank:2d}. {skill:<20s}  {count:3d}  {bar}")
    print("=" * 60)
    print(f"\n[Experiment] Results saved → {RESULTS_PATH}")


if __name__ == "__main__":
    run_experiment()
