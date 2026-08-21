"""
Software Engineering Resume Ingestion Experiment
=================================================
Batch-runs the improved resume extraction pipeline over all files in
Software_Engineering_Resume_Dataset_CVParserPro/ (100 .docx resumes)
and reports extraction quality metrics.

Extends the original ENGINEERING experiment with DOCX support via python-docx.
Does NOT write to the database — exercises only the extraction layer.

Usage:
    cd <repo_root>
    python backend/scripts/run_software_eng_experiment.py

Output:
    backend/experiments/software_engineering_resume_results.json
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
DATASET_DIR = REPO_ROOT / "Software_Engineering_Resume_Dataset_CVParserPro"
OUTPUT_DIR = BACKEND_DIR / "experiments"
RESULTS_PATH = OUTPUT_DIR / "software_engineering_resume_results.json"


# ---------------------------------------------------------------------------
# DOCX extractor (not in core modules — experiment-only helper)
# ---------------------------------------------------------------------------

def extract_text_from_docx(file_path: str) -> str:
    """Extract plain text from a .docx file using python-docx.

    Joins all paragraph texts with newlines to preserve section structure
    (important for section-header detection in skill_extractor).
    """
    import docx  # lazy import — only needed for this experiment  # noqa: PLC0415

    doc = docx.Document(file_path)
    lines = [para.text for para in doc.paragraphs if para.text.strip()]
    text = "\n".join(lines)
    return text


# ---------------------------------------------------------------------------
# Shared extraction dispatcher
# ---------------------------------------------------------------------------

def extract_text(file_path: Path) -> str:
    """Dispatch to the appropriate extractor based on file extension."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(str(file_path))
    if suffix == ".docx":
        return extract_text_from_docx(str(file_path))
    raise ValueError(f"Unsupported file type: {suffix}")


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

def run_experiment() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    resume_files = sorted(
        f for f in DATASET_DIR.iterdir()
        if f.suffix.lower() in {".pdf", ".docx"}
    )
    total = len(resume_files)
    print(f"[Experiment] Found {total} resume files in {DATASET_DIR}")

    pdf_count = sum(1 for f in resume_files if f.suffix.lower() == ".pdf")
    docx_count = sum(1 for f in resume_files if f.suffix.lower() == ".docx")
    print(f"[Experiment] Format breakdown: {pdf_count} PDF, {docx_count} DOCX\n")

    per_resume: list[dict] = []
    skill_counter: Counter = Counter()
    all_confidences: list[float] = []
    errors: list[dict] = []

    for i, file_path in enumerate(resume_files, start=1):
        print(f"[{i:3d}/{total}] Processing {file_path.name} ...", end=" ", flush=True)
        try:
            text = extract_text(file_path)
            results = extract_skills_with_semantic_fallback(text)
        except Exception as exc:
            print(f"ERROR: {exc}")
            errors.append({"file": file_path.name, "error": str(exc)})
            per_resume.append({
                "file": file_path.name,
                "format": file_path.suffix.lower().lstrip("."),
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
            "file": file_path.name,
            "format": file_path.suffix.lower().lstrip("."),
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
        "dataset": str(DATASET_DIR.name),
        "total_resumes": processed,
        "pdf_count": pdf_count,
        "docx_count": docx_count,
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
    print("SOFTWARE ENGINEERING RESUME EXPERIMENT — RESULTS")
    print("=" * 60)
    print(f"  Dataset                    : {DATASET_DIR.name}")
    print(f"  Total resumes processed    : {processed}  (PDF: {pdf_count}, DOCX: {docx_count})")
    print(f"  Resumes with skills        : {with_skills}")
    print(f"  Resumes without skills     : {processed - with_skills}")
    print(f"  Extraction success rate    : {extraction_rate:.1f}%")
    print(f"  Avg skills per resume      : {avg_skills:.2f}")
    print(f"  Median skills per resume   : {median_skills:.1f}")
    print(f"  Avg confidence score       : {avg_confidence:.4f}")
    print(f"  Median confidence score    : {median_confidence:.4f}")
    if errors:
        print(f"  Parse errors               : {len(errors)}")
        for e in errors:
            print(f"    - {e['file']}: {e['error']}")
    print()
    print("  Top 20 detected skills:")
    for rank, (skill, count) in enumerate(top_20, start=1):
        bar = "#" * min(count, 40)
        print(f"    {rank:2d}. {skill:<20s}  {count:3d}  {bar}")
    print("=" * 60)
    print(f"\n[Experiment] Results saved → {RESULTS_PATH}")


if __name__ == "__main__":
    run_experiment()
