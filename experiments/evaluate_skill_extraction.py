"""
Evaluation pipeline for the LearnPathAI resume skill extraction system.

Measures precision, recall, and F1 against manually annotated ground truth
for 118 resumes in the ENGINEERING/ corpus.

Evaluation mode: ontology-constrained — ground-truth skills that fall outside
the platform's supported skill ontology (RESUME_SKILL_MAP values) are excluded
before computing metrics.  This ensures we only penalise the extractor for
skills it was actually designed to find.

Usage:
    python experiments/evaluate_skill_extraction.py
"""

import csv
import datetime
import json
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — import production resume_parser without modifying it
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from services.resume_parser import extract_text_from_pdf  # noqa: E402
from services.skill_alias_map import RESUME_SKILL_MAP  # noqa: E402
from services.skill_extractor import extract_skills_from_text as _extract_skills_raw  # noqa: E402


def extract_skills_from_text(text: str) -> dict:
    """Adapter: new API returns list[dict]; evaluation script expects dict[skill_id, count]."""
    return {r["skill"]: 1 for r in _extract_skills_raw(text)}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINEERING_DIR = REPO_ROOT / "ENGINEERING"
GROUND_TRUTH_PATH = REPO_ROOT / "experiments" / "skill_ground_truth" / "resume_skill_annotations.json"
RESULTS_DIR = REPO_ROOT / "experiments" / "results"
METRICS_PATH = RESULTS_DIR / "skill_extraction_metrics.json"
PER_RESUME_CSV_PATH = RESULTS_DIR / "skill_extraction_per_resume.csv"
REPORT_PATH = RESULTS_DIR / "experiment_report.md"

# Lowercase lookup table built once from the production alias map
_LOWER_SKILL_MAP: dict[str, str] = {k.lower(): v for k, v in RESUME_SKILL_MAP.items()}

# The platform's supported skill ontology — the complete set of canonical IDs
# the extractor can ever produce.  Ground-truth skills that don't map into
# this set are excluded from evaluation (ontology-constrained mode).
SUPPORTED_SKILLS: set[str] = set(RESUME_SKILL_MAP.values())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_skill(skill: str) -> str:
    """Lowercase + strip whitespace."""
    return skill.lower().strip()


def ground_truth_to_canonicals(annotated_skills: list[str]) -> tuple[set[str], set[str]]:
    """
    Map human-readable ground-truth skill names to canonical IDs.

    Returns:
        in_ontology  — canonicals that exist in SUPPORTED_SKILLS (used for metrics)
        out_of_scope — raw skill names that have no canonical in the ontology
                       (excluded from evaluation; tracked for reporting only)
    """
    in_ontology: set[str] = set()
    out_of_scope: set[str] = set()
    for skill in annotated_skills:
        key = normalize_skill(skill)
        canonical = _LOWER_SKILL_MAP.get(key)
        if canonical is not None and canonical in SUPPORTED_SKILLS:
            in_ontology.add(canonical)
        else:
            out_of_scope.add(skill)
    return in_ontology, out_of_scope


def compute_metrics(
    predicted: set[str],
    ground_truth: set[str],
) -> tuple[int, int, int, float, float, float]:
    """Return (TP, FP, FN, precision, recall, f1)."""
    tp = len(predicted & ground_truth)
    fp = len(predicted - ground_truth)
    fn = len(ground_truth - predicted)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return tp, fp, fn, precision, recall, f1


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def run_evaluation() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load ground truth
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as fh:
        ground_truth_data = json.load(fh)

    annotations: list[dict] = ground_truth_data["annotations"]
    print(f"[Eval] Loaded ground truth for {len(annotations)} resumes.")
    print(f"[Eval] Platform ontology: {len(SUPPORTED_SKILLS)} canonical skill IDs")
    print(f"[Eval] Mode: ontology-constrained (out-of-scope ground-truth skills excluded)\n")

    per_resume_rows: list[dict] = []
    total_tp = total_fp = total_fn = 0
    total_filtered_out = 0
    all_fp_skills: list[str] = []
    all_fn_skills: list[str] = []
    all_out_of_scope: list[str] = []
    all_predicted_skills: set[str] = set()

    evaluated = skipped = 0

    for entry in annotations:
        resume_file: str = entry["resume_file"]
        annotated_skills: list[str] = entry["annotated_skills"]
        pdf_path = ENGINEERING_DIR / resume_file

        if not pdf_path.exists():
            print(f"[Eval] SKIP (not found): {resume_file}")
            skipped += 1
            continue

        # --- Extract predicted skills via production code ---
        try:
            text = extract_text_from_pdf(str(pdf_path))
            predicted_canonicals: set[str] = set(extract_skills_from_text(text).keys())
        except Exception as exc:
            print(f"[Eval] ERROR processing {resume_file}: {exc}")
            skipped += 1
            continue

        # --- Map ground truth → canonicals, filter to ontology ---
        gt_canonicals, out_of_scope = ground_truth_to_canonicals(annotated_skills)
        total_filtered_out += len(out_of_scope)
        all_out_of_scope.extend(out_of_scope)

        # --- Per-resume metrics (ontology-constrained) ---
        tp, fp, fn, precision, recall, f1 = compute_metrics(predicted_canonicals, gt_canonicals)

        total_tp += tp
        total_fp += fp
        total_fn += fn

        # Collect FP/FN skill names for the report
        fp_skills = sorted(predicted_canonicals - gt_canonicals)
        fn_skills = sorted(gt_canonicals - predicted_canonicals)
        all_fp_skills.extend(fp_skills)
        all_fn_skills.extend(fn_skills)
        all_predicted_skills.update(predicted_canonicals)

        per_resume_rows.append(
            {
                "resume_id": resume_file,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "predicted_skills": "|".join(sorted(predicted_canonicals)),
                "ground_truth_skills": "|".join(sorted(gt_canonicals)),
                "excluded_skills": "|".join(sorted(out_of_scope)),
            }
        )

        evaluated += 1
        oos_note = f"  excluded={len(out_of_scope)}" if out_of_scope else ""
        print(
            f"[Eval] {resume_file:30s}  P={precision:.2f}  R={recall:.2f}  F1={f1:.2f}"
            f"  TP={tp}  FP={fp}  FN={fn}{oos_note}"
        )

    # --- Dataset-level metrics ---
    avg_precision = sum(r["precision"] for r in per_resume_rows) / evaluated if evaluated else 0.0
    avg_recall = sum(r["recall"] for r in per_resume_rows) / evaluated if evaluated else 0.0
    avg_f1 = sum(r["f1_score"] for r in per_resume_rows) / evaluated if evaluated else 0.0

    # Micro-averaged (totals)
    micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if (micro_precision + micro_recall) > 0
        else 0.0
    )

    top_fp = Counter(all_fp_skills).most_common(10)
    top_fn = Counter(all_fn_skills).most_common(10)
    top_oos = Counter(all_out_of_scope).most_common(15)

    # -----------------------------------------------------------------------
    # Write skill_extraction_metrics.json
    # -----------------------------------------------------------------------
    metrics = {
        "evaluation_mode": "ontology_constrained",
        "ontology_size": len(SUPPORTED_SKILLS),
        "precision": round(avg_precision, 4),
        "recall": round(avg_recall, 4),
        "f1_score": round(avg_f1, 4),
        "micro_precision": round(micro_precision, 4),
        "micro_recall": round(micro_recall, 4),
        "micro_f1": round(micro_f1, 4),
        "true_positives": total_tp,
        "false_positives": total_fp,
        "false_negatives": total_fn,
        "ground_truth_skills_excluded": total_filtered_out,
        "resumes_evaluated": evaluated,
        "resumes_skipped": skipped,
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    print(f"\n[Eval] Metrics saved → {METRICS_PATH}")

    # -----------------------------------------------------------------------
    # Write skill_extraction_per_resume.csv
    # -----------------------------------------------------------------------
    csv_columns = ["resume_id", "precision", "recall", "f1_score", "predicted_skills", "ground_truth_skills", "excluded_skills"]
    with open(PER_RESUME_CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(per_resume_rows)
    print(f"[Eval] Per-resume CSV saved → {PER_RESUME_CSV_PATH}")

    # -----------------------------------------------------------------------
    # Write experiment_report.md
    # -----------------------------------------------------------------------
    today = datetime.date.today()

    report_lines = [
        "# Experiment Report — Resume Skill Extraction Evaluation (Ontology-Constrained)",
        "",
        "## Dataset Description",
        "",
        f"- **Corpus**: `ENGINEERING/` — 118 engineering resumes (PDF)",
        f"- **Ground truth**: `experiments/skill_ground_truth/resume_skill_annotations.json`",
        f"- **Resumes evaluated**: {evaluated}",
        f"- **Resumes skipped** (file not found or parse error): {skipped}",
        f"- **Unique predicted skills** (canonical IDs): {len(all_predicted_skills)}",
        "",
        "### Corpus Notes",
        "",
        "49 of the 118 resumes contain zero software-engineering skills — they belong to",
        "hardware, civil, mechanical, or general-management engineering roles.",
        "The ground truth reflects this: those resumes have empty `annotated_skills` lists.",
        "",
        "## Evaluation Methodology: Ontology-Constrained",
        "",
        "This evaluation only measures performance on skills the platform was designed to",
        "detect. Ground-truth annotations are pre-filtered to the **platform's supported",
        "skill ontology** before computing any metrics.",
        "",
        "### What the ontology is",
        "",
        "The platform's ontology is the set of canonical skill IDs produced by",
        "`RESUME_SKILL_MAP` in `backend/services/resume_parser.py`.",
        f"It contains **{len(SUPPORTED_SKILLS)} canonical skills**: `{'`, `'.join(sorted(SUPPORTED_SKILLS))}`.",
        "",
        "### Why out-of-scope skills are excluded",
        "",
        "Skills like `MATLAB`, `LabVIEW`, `SQL`, `Jira`, `JUnit`, `Oracle`, `XML` appear",
        "in ground-truth annotations but have **no entry in `RESUME_SKILL_MAP`**. The",
        "extractor is structurally incapable of finding them regardless of resume text",
        "quality. Including them as False Negatives would penalise text-extraction",
        "performance for what is actually a vocabulary-coverage decision.",
        "",
        f"- **Ground-truth skill mentions excluded (total across corpus)**: {total_filtered_out}",
        "",
        "### Comparison steps",
        "",
        "1. Extract predicted skills from PDF using `extract_text_from_pdf` + `extract_skills_from_text`.",
        "2. Map each ground-truth skill name → canonical ID via `RESUME_SKILL_MAP`.",
        "3. **Drop** any ground-truth canonical that is not in `SUPPORTED_SKILLS`.",
        "4. Compute TP / FP / FN on the filtered sets.",
        "",
        "## Final Evaluation Metrics",
        "",
        "| Metric | Macro-avg | Micro (totals) |",
        "| --- | --- | --- |",
        f"| Precision | {avg_precision:.4f} | {micro_precision:.4f} |",
        f"| Recall    | {avg_recall:.4f} | {micro_recall:.4f} |",
        f"| F1 Score  | {avg_f1:.4f} | {micro_f1:.4f} |",
        "",
        f"**Total TP**: {total_tp} &nbsp; **Total FP**: {total_fp} &nbsp; **Total FN**: {total_fn}",
        "",
        "## Top 10 Most Common False Positives",
        "",
        "*(Skills the extractor predicted that were not in the (filtered) ground truth)*",
        "",
        "| Rank | Skill (canonical) | Count |",
        "| --- | --- | --- |",
    ]
    for i, (skill, count) in enumerate(top_fp, start=1):
        report_lines.append(f"| {i} | `{skill}` | {count} |")

    report_lines += [
        "",
        "## Top 10 Most Commonly Missed Skills (False Negatives)",
        "",
        "*(In-ontology ground-truth skills the extractor failed to find)*",
        "",
        "| Rank | Skill (canonical) | Count |",
        "| --- | --- | --- |",
    ]
    for i, (skill, count) in enumerate(top_fn, start=1):
        report_lines.append(f"| {i} | `{skill}` | {count} |")

    report_lines += [
        "",
        "## Most Common Out-of-Scope Skills (Excluded from Metrics)",
        "",
        "*(Ground-truth skills outside the platform ontology — not counted as TP/FP/FN)*",
        "",
        "| Rank | Skill (raw) | Count |",
        "| --- | --- | --- |",
    ]
    for i, (skill, count) in enumerate(top_oos, start=1):
        report_lines.append(f"| {i} | `{skill}` | {count} |")

    report_lines += [
        "",
        "## Interpretation",
        "",
        "**False Positives** are driven by overly broad aliases: `\"r\"` (single character)",
        "fires on any resume token `r`; `\"qa\"`, `\"security\"`, `\"backend\"` match generic",
        "prose. Tightening these patterns would improve precision.",
        "",
        "**False Negatives** (in-ontology) reflect text-extraction failures or PDF encoding",
        "issues (e.g. `C++` rendered without `+` signs by pdfplumber). These are genuine",
        "parsing gaps worth fixing.",
        "",
        "**Out-of-scope exclusions** (`MATLAB`, `SQL`, `LabVIEW`, `Jira`, etc.) represent",
        "vocabulary-coverage gaps. Adding these to `RESUME_SKILL_MAP` would expand the",
        "ontology and is the highest-leverage improvement for recall on this corpus.",
        "",
        "---",
        f"*Generated by `experiments/evaluate_skill_extraction.py` on {today}*",
    ]

    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(report_lines) + "\n")
    print(f"[Eval] Report saved → {REPORT_PATH}")

    # -----------------------------------------------------------------------
    # Print final summary to terminal
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("FINAL METRICS  [ontology-constrained]")
    print("=" * 60)
    print(f"  Ontology size     : {len(SUPPORTED_SKILLS)} canonical skills")
    print(f"  GT skills excluded: {total_filtered_out} (out of platform ontology)")
    print(f"  Resumes evaluated : {evaluated}")
    print(f"  Macro Precision   : {avg_precision:.4f}")
    print(f"  Macro Recall      : {avg_recall:.4f}")
    print(f"  Macro F1          : {avg_f1:.4f}")
    print(f"  Micro Precision   : {micro_precision:.4f}")
    print(f"  Micro Recall      : {micro_recall:.4f}")
    print(f"  Micro F1          : {micro_f1:.4f}")
    print(f"  Total TP          : {total_tp}")
    print(f"  Total FP          : {total_fp}")
    print(f"  Total FN          : {total_fn}")
    print("=" * 60)
    print(f"\nTop 10 FP skills  : {[s for s, _ in top_fp]}")
    print(f"Top 10 FN skills  : {[s for s, _ in top_fn]}")
    print(f"Top 10 excluded   : {[s for s, _ in top_oos[:10]]}")


if __name__ == "__main__":
    run_evaluation()
