"""
Skill Extraction Evaluation — Step 1-5

This script:
  1. Randomly samples 20 resumes (seed=42) from the dataset directory
  2. Extracts text from each .docx file
  3. Runs extract_skills_with_semantic_fallback() on each resume
  4. Writes backend/experiments/manual_skill_annotation.csv
  5. Prints the Skills section text + predicted skills for each resume

Usage:
    cd <repo root>
    python -m backend.scripts.generate_skill_annotation_sheet

or (from the backend/ directory with the services package on PYTHONPATH):
    cd backend
    python scripts/generate_skill_annotation_sheet.py
"""

from __future__ import annotations

import csv
import os
import random
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path plumbing — make sure `services` is importable regardless of cwd
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent           # backend/scripts/
BACKEND_DIR = SCRIPT_DIR.parent                         # backend/
REPO_ROOT = BACKEND_DIR.parent                          # repo root

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------------
# Dataset location
# ---------------------------------------------------------------------------
DATASET_DIR = REPO_ROOT / "Software_Engineering_Resume_Dataset_CVParserPro"
OUTPUT_CSV = BACKEND_DIR / "experiments" / "manual_skill_annotation.csv"

# ---------------------------------------------------------------------------
# Imports from the existing pipeline (DO NOT MODIFY these modules)
# ---------------------------------------------------------------------------
from services.skill_extractor import extract_skills_with_semantic_fallback  # noqa: E402


# ---------------------------------------------------------------------------
# DOCX text extraction helper
# ---------------------------------------------------------------------------

def extract_text_from_docx(file_path: Path) -> str:
    """Extract plain text from a .docx file using python-docx."""
    try:
        from docx import Document  # type: ignore
        doc = Document(str(file_path))
        paragraphs = [para.text for para in doc.paragraphs]
        return "\n".join(paragraphs)
    except Exception as exc:
        print(f"  [WARN] Failed to read {file_path.name}: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Skills-section snippet extractor (for human review output)
# ---------------------------------------------------------------------------

_SKILLS_HEADERS_REVIEW = {
    "skills", "technical skills", "core skills", "skill highlights",
    "highlights", "technologies", "tools", "tech stack",
    "programming languages", "languages and frameworks",
}
_NON_SKILL_HEADERS_REVIEW = {
    "summary", "professional summary", "career summary", "profile",
    "experience", "work experience", "professional experience",
    "employment history", "education", "education and training",
    "academic background", "certifications", "projects",
    "references", "awards", "publications", "interests", "hobbies",
}


def extract_skills_section_text(text: str) -> str:
    """Return the raw lines belonging to the Skills section, if found."""
    lines = text.split("\n")
    snippet_lines: list[str] = []
    in_skills = False

    for line in lines:
        norm = line.strip().lower()
        if not norm:
            if in_skills:
                snippet_lines.append("")
            continue

        # Check for section header transition
        if norm in _SKILLS_HEADERS_REVIEW or any(
            norm.startswith(h + ":") or norm.startswith(h + " ")
            for h in _SKILLS_HEADERS_REVIEW
        ):
            in_skills = True
            snippet_lines.append(f">>> [{line.strip()}]")
            continue

        if norm in _NON_SKILL_HEADERS_REVIEW:
            if in_skills:
                break  # end of skills section
            continue

        if in_skills:
            snippet_lines.append(line.rstrip())

    if snippet_lines:
        # Trim trailing blank lines
        while snippet_lines and not snippet_lines[-1]:
            snippet_lines.pop()
        return "\n".join(snippet_lines)

    return "(Skills section not detected)"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # ---- 1. Collect all resume files ----------------------------------------
    all_files = sorted(DATASET_DIR.glob("*.docx"))
    if not all_files:
        print(f"[ERROR] No .docx files found in {DATASET_DIR}")
        sys.exit(1)

    print(f"[INFO] Found {len(all_files)} resumes in dataset.")

    # ---- 2. Sample 20 with deterministic seed --------------------------------
    random.seed(42)
    sampled = random.sample(all_files, min(20, len(all_files)))
    sampled.sort()  # sort for deterministic ordering in output

    print(f"[INFO] Sampled {len(sampled)} resumes (seed=42):")
    for f in sampled:
        print(f"  • {f.name}")

    # ---- 3. Run extraction pipeline on each resume ---------------------------
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    print("\n" + "=" * 70)
    print("RESUME SKILL EXTRACTION RESULTS")
    print("=" * 70)

    for resume_path in sampled:
        print(f"\n{'─' * 60}")
        print(f"FILE: {resume_path.name}")
        print(f"{'─' * 60}")

        # Extract raw text
        text = extract_text_from_docx(resume_path)

        if not text.strip():
            print("  [WARN] Empty text extracted — skipping.")
            rows.append({
                "resume_file": resume_path.name,
                "predicted_skills": "",
                "predicted_confidences": "",
                "manual_true_skills": "",
                "notes": "empty text",
            })
            continue

        # Run the extraction pipeline (DO NOT MODIFY)
        skill_results = extract_skills_with_semantic_fallback(text)

        # Sort by confidence descending
        skill_results_sorted = sorted(
            skill_results, key=lambda x: x["confidence"], reverse=True
        )

        predicted_skills = [r["skill"] for r in skill_results_sorted]
        predicted_confidences = [str(r["confidence"]) for r in skill_results_sorted]

        # ---- Print Skills section snippet ------------------------------------
        snippet = extract_skills_section_text(text)
        print("\n[Skills Section Detected]:")
        print(snippet)

        # ---- Print predicted skills -----------------------------------------
        print(f"\n[Predicted Skills ({len(predicted_skills)} total)]:")
        for skill, conf in zip(predicted_skills, predicted_confidences):
            print(f"  {skill:<30}  confidence={conf}")

        rows.append({
            "resume_file": resume_path.name,
            "predicted_skills": ";".join(predicted_skills),
            "predicted_confidences": ";".join(predicted_confidences),
            "manual_true_skills": "",   # to be filled by human reviewer
            "notes": "",
        })

    # ---- 4. Write CSV --------------------------------------------------------
    fieldnames = [
        "resume_file",
        "predicted_skills",
        "predicted_confidences",
        "manual_true_skills",
        "notes",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 70)
    print(f"[DONE] Annotation sheet written to:")
    print(f"       {OUTPUT_CSV}")
    print()
    print("Next step: Open the CSV and fill in the 'manual_true_skills' column")
    print("           with semicolon-separated skill names for each resume.")
    print("           Then run: python backend/scripts/compute_skill_extraction_metrics.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
