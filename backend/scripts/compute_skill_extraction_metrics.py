"""
Skill Extraction Evaluation — Step 6-7: Compute Precision / Recall / F1

Usage:
    cd <repo root>
    python -m backend.scripts.compute_skill_extraction_metrics

or (from backend/ with services on PYTHONPATH):
    cd backend
    python scripts/compute_skill_extraction_metrics.py

Prerequisites:
    backend/experiments/manual_skill_annotation.csv  must exist and have the
    'manual_true_skills' column populated by a human reviewer.

Output:
    • Per-resume breakdown (TP / FP / FN)
    • Aggregate Precision, Recall, F1
    • Top-N False Positives (predicted but not actually present)
    • Top-N False Negatives (present but not predicted)
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ANNOTATION_CSV = BACKEND_DIR / "experiments" / "manual_skill_annotation.csv"

TOP_N = 10  # how many top FPs / FNs to print

# Inferred category labels added by the recommendation engine — NOT explicit
# resume skills.  We strip these from the predicted set before computing
# metrics so the evaluation reflects only explicit extraction accuracy.
IGNORED_SKILLS: frozenset[str] = frozenset({
    "backend",
    "frontend",
    "ai",
    "devops",
})


# ---------------------------------------------------------------------------
# CSV loading helpers
# ---------------------------------------------------------------------------

def _parse_skill_list(raw: str, sep: str = ";") -> list[str]:
    """Parse a delimited skill string into a clean, deduplicated list.

    Lowercases and strips whitespace. Empty strings are removed.
    Supports both semicolon-separated (predicted) and comma-separated (manual) fields.
    """
    if not raw or not raw.strip():
        return []
    seen: set[str] = set()
    result: list[str] = []
    for s in raw.split(sep):
        normalized = s.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def load_annotations(csv_path: Path) -> list[dict]:
    """Load the annotation CSV and return a list of row dicts.

    Handles an optional title row before the real header row.
    Each returned dict has:
        resume_file         : str
        predicted_skills    : list[str]   (semicolon-separated in CSV)
        manual_true_skills  : list[str]   (comma-separated in CSV)
    """
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        # Peek at the first line; skip if it's a bare title (no commas or just
        # one field that doesn't look like a column header list).
        first_line = fh.readline().strip()
        if "," not in first_line or first_line.split(",")[0] != "resume_file":
            # It's a title row — read the real header next
            header_line = fh.readline().strip()
            fieldnames = [f.strip() for f in header_line.split(",")]
        else:
            # First line IS the header
            fieldnames = [f.strip() for f in first_line.split(",")]

        reader = csv.DictReader(fh, fieldnames=fieldnames)
        for row in reader:
            predicted = _parse_skill_list(row.get("predicted_skills", ""), sep=";")
            manual    = _parse_skill_list(row.get("manual_true_skills", ""), sep=",")
            rows.append({
                "resume_file": row.get("resume_file", "").strip(),
                "predicted_skills": predicted,
                "manual_true_skills": manual,
            })
    return rows


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

def compute_per_resume_metrics(row: dict) -> dict:
    """Compute TP / FP / FN for a single resume (set-based comparison)."""
    predicted = set(row["predicted_skills"])
    ground_truth = set(row["manual_true_skills"])

    tp = predicted & ground_truth
    fp = predicted - ground_truth
    fn = ground_truth - predicted

    return {
        "resume_file": row["resume_file"],
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tp_count": len(tp),
        "fp_count": len(fp),
        "fn_count": len(fn),
    }


def compute_per_resume_metrics_filtered(
    row: dict, ignored: frozenset[str]
) -> dict:
    """Same as compute_per_resume_metrics but strips ignored labels from predicted."""
    predicted = {s for s in row["predicted_skills"] if s not in ignored}
    ground_truth = set(row["manual_true_skills"])  # ground truth is never filtered

    tp = predicted & ground_truth
    fp = predicted - ground_truth
    fn = ground_truth - predicted

    return {
        "resume_file": row["resume_file"],
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tp_count": len(tp),
        "fp_count": len(fp),
        "fn_count": len(fn),
    }


def aggregate_metrics(per_resume: list[dict]) -> tuple[float, float, float]:
    """Compute macro-averaged Precision, Recall, and F1.

    Uses micro-aggregation (sum TPs, FPs, FNs across all resumes) rather than
    averaging per-resume ratios, which is more stable when some resumes have
    no annotations.
    """
    total_tp = sum(r["tp_count"] for r in per_resume)
    total_fp = sum(r["fp_count"] for r in per_resume)
    total_fn = sum(r["fn_count"] for r in per_resume)

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return precision, recall, f1


def top_errors(per_resume: list[dict], error_key: str, n: int = TOP_N) -> list[tuple[str, int]]:
    """Return the top-N most common FP or FN skill labels across all resumes."""
    counter: Counter = Counter()
    for row in per_resume:
        for skill in row[error_key]:
            counter[skill] += 1
    return counter.most_common(n)


# ---------------------------------------------------------------------------
# Pretty printing helpers
# ---------------------------------------------------------------------------

def _sep(char: str = "─", width: int = 60) -> str:
    return char * width


def _safe_div(num: float, den: float) -> str:
    if den == 0:
        return "N/A"
    return f"{num / den:.4f}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # ---- 0. Validate CSV exists -------------------------------------------
    if not ANNOTATION_CSV.exists():
        print(f"[ERROR] Annotation CSV not found: {ANNOTATION_CSV}")
        print("  Run generate_skill_annotation_sheet.py first, then fill in")
        print("  the 'manual_true_skills' column before running this script.")
        sys.exit(1)

    # ---- 1. Load annotations ------------------------------------------------
    rows = load_annotations(ANNOTATION_CSV)

    # Filter to rows that have been annotated (manual_true_skills not empty)
    annotated = [r for r in rows if r["manual_true_skills"]]
    unannotated = [r for r in rows if not r["manual_true_skills"]]

    print(_sep("=", 70))
    print("SKILL EXTRACTION EVALUATION REPORT")
    print(_sep("=", 70))
    print(f"Total resumes in CSV   : {len(rows)}")
    print(f"Annotated resumes      : {len(annotated)}")
    print(f"Unannotated (skipped)  : {len(unannotated)}")

    if unannotated:
        print("\n[NOTE] The following resumes have no manual annotations and are excluded:")
        for r in unannotated:
            print(f"  • {r['resume_file']}")

    if not annotated:
        print("\n[ERROR] No annotated rows found. Please fill in 'manual_true_skills'.")
        sys.exit(1)

    # ---- 2. Per-resume TP / FP / FN (original + filtered) -------------------
    per_resume          = [compute_per_resume_metrics(r) for r in annotated]
    per_resume_filtered = [
        compute_per_resume_metrics_filtered(r, IGNORED_SKILLS) for r in annotated
    ]

    print(f"\n{_sep('─', 70)}")
    print("PER-RESUME BREAKDOWN")
    print(_sep("─", 70))
    print(f"{'Resume':<35}  {'TP':>4}  {'FP':>4}  {'FN':>4}  {'Prec':>6}  {'Rec':>6}")
    print(_sep("─", 70))

    for m in per_resume:
        prec_str = _safe_div(m["tp_count"], m["tp_count"] + m["fp_count"])
        rec_str  = _safe_div(m["tp_count"], m["tp_count"] + m["fn_count"])
        print(
            f"{m['resume_file']:<35}  "
            f"{m['tp_count']:>4}  {m['fp_count']:>4}  {m['fn_count']:>4}  "
            f"{prec_str:>6}  {rec_str:>6}"
        )

    # ---- 3. Aggregate metrics ------------------------------------------------
    total_tp = sum(m["tp_count"] for m in per_resume)
    total_fp = sum(m["fp_count"] for m in per_resume)
    total_fn = sum(m["fn_count"] for m in per_resume)
    total_skills_evaluated = total_tp + total_fp + total_fn

    precision, recall, f1 = aggregate_metrics(per_resume)

    # Filtered (inferred category labels removed from predictions)
    f_tp = sum(m["tp_count"] for m in per_resume_filtered)
    f_fp = sum(m["fp_count"] for m in per_resume_filtered)
    f_fn = sum(m["fn_count"] for m in per_resume_filtered)

    filtered_precision, filtered_recall, filtered_f1 = aggregate_metrics(per_resume_filtered)

    print(f"\n{_sep('=', 70)}")
    print("AGGREGATE METRICS (micro-averaged)")
    print(_sep("=", 70))
    print(f"  Annotated resumes       : {len(annotated)}")
    print(f"  Total skills evaluated  : {total_skills_evaluated}")
    print(f"  True Positives (TP)     : {total_tp}")
    print(f"  False Positives (FP)    : {total_fp}")
    print(f"  False Negatives (FN)    : {total_fn}")
    print(_sep("─", 70))
    print(f"  Precision               : {precision:.4f}  "
          f"  [{total_tp} / ({total_tp} + {total_fp})]")
    print(f"  Recall                  : {recall:.4f}  "
          f"  [{total_tp} / ({total_tp} + {total_fn})]")
    print(f"  F1 Score                : {f1:.4f}  "
          f"  [2 × {precision:.4f} × {recall:.4f} / ({precision:.4f} + {recall:.4f})]")

    print(f"\n{_sep('=', 70)}")
    print(f"METRICS COMPARISON  (ignored: {', '.join(sorted(IGNORED_SKILLS))})")
    print(_sep("=", 70))
    print(f"  {'':30}  {'Precision':>9}  {'Recall':>9}  {'F1':>9}")
    print(_sep("─", 70))
    print(f"  {'Original (with inferred labels)':<30}  {precision:>9.4f}  {recall:>9.4f}  {f1:>9.4f}")
    print(f"  {'Filtered (explicit only)':<30}  {filtered_precision:>9.4f}  {filtered_recall:>9.4f}  {filtered_f1:>9.4f}")
    print(_sep("─", 70))
    print(f"\n  Original F1 : {f1:.4f}")
    print(f"  Filtered F1 : {filtered_f1:.4f}")
    print(f"  F1 delta    : {filtered_f1 - f1:+.4f}")

    # ---- 4. Top false positives / negatives ----------------------------------
    top_fps = top_errors(per_resume, "fp", n=TOP_N)
    top_fns = top_errors(per_resume, "fn", n=TOP_N)

    print(f"\n{_sep('─', 70)}")
    print(f"TOP {TOP_N} FALSE POSITIVES  (predicted but NOT in ground truth)")
    print(_sep("─", 70))
    if top_fps:
        for rank, (skill, count) in enumerate(top_fps, 1):
            print(f"  {rank:>2}. {skill:<30}  ({count} resume(s))")
    else:
        print("  (none — perfect precision!)")

    print(f"\n{_sep('─', 70)}")
    print(f"TOP {TOP_N} FALSE NEGATIVES  (in ground truth but NOT predicted)")
    print(_sep("─", 70))
    if top_fns:
        for rank, (skill, count) in enumerate(top_fns, 1):
            print(f"  {rank:>2}. {skill:<30}  ({count} resume(s))")
    else:
        print("  (none — perfect recall!)")

    print(f"\n{_sep('=', 70)}\n")

    # ---- 5. Save JSON report -------------------------------------------------
    output_path = BACKEND_DIR / "experiments" / "skill_extraction_metrics.json"
    report = {
        "num_resumes_evaluated": len(annotated),
        # Original metrics (all predicted labels, including inferred categories)
        "original_precision": round(precision, 4),
        "original_recall": round(recall, 4),
        "original_f1": round(f1, 4),
        "original_tp": total_tp,
        "original_fp": total_fp,
        "original_fn": total_fn,
        # Filtered metrics (inferred category labels stripped from predictions)
        "filtered_precision": round(filtered_precision, 4),
        "filtered_recall": round(filtered_recall, 4),
        "filtered_f1": round(filtered_f1, 4),
        "filtered_tp": f_tp,
        "filtered_fp": f_fp,
        "filtered_fn": f_fn,
        "ignored_skills": sorted(IGNORED_SKILLS),
        # Convenience aliases (point to original for backwards compatibility)
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": total_tp,
        "fp": total_fp,
        "fn": total_fn,
        "avg_predicted_skills_per_resume": round(
            sum(len(r["predicted_skills"]) for r in annotated) / len(annotated), 2
        ),
        "avg_true_skills_per_resume": round(
            sum(len(r["manual_true_skills"]) for r in annotated) / len(annotated), 2
        ),
        "top_false_positives": [{"skill": s, "count": c} for s, c in top_fps],
        "top_false_negatives": [{"skill": s, "count": c} for s, c in top_fns],
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[OK] Metrics saved to {output_path}\n")


if __name__ == "__main__":
    main()
