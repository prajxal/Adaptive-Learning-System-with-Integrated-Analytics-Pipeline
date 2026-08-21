"""
GitHub Skill Fusion Evaluation Pipeline for LearnPathAI.

Compares three skill inference strategies against manually annotated ground truth:
  1. Resume-only   — production extract_text_from_pdf + extract_skills_from_text
  2. GitHub-only   — public GitHub API language bytes → canonical skill IDs
  3. Fusion        — union of resume-only and GitHub-only sets

Only resumes that contain a detectable GitHub profile URL participate in the
GitHub-only and fusion comparisons.  The resume-only baseline is computed over
the full annotated corpus, so it is directly comparable to evaluate_skill_extraction.py.

Evaluation mode: ontology-constrained (same as evaluate_skill_extraction.py).
Ground-truth skills outside the platform ontology are excluded before metrics.

Usage:
    python experiments/evaluate_github_fusion.py [--no-cache]

Environment variables:
    GITHUB_TOKEN   — GitHub personal access token (strongly recommended).
                     Without it the unauthenticated rate limit is 60 req/hr,
                     which is likely insufficient for this experiment.
"""

import csv
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup — import production modules and sibling evaluation helpers
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
EXPERIMENTS_DIR = REPO_ROOT / "experiments"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(EXPERIMENTS_DIR))

from services.resume_parser import (  # noqa: E402
    RESUME_SKILL_MAP,
    extract_skills_from_text,
    extract_text_from_pdf,
)
from evaluate_skill_extraction import (  # noqa: E402
    SUPPORTED_SKILLS,
    compute_metrics,
    ground_truth_to_canonicals,
    normalize_skill,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINEERING_DIR = REPO_ROOT / "ENGINEERING"
GROUND_TRUTH_PATH = EXPERIMENTS_DIR / "skill_ground_truth" / "resume_skill_annotations.json"
RESULTS_DIR = EXPERIMENTS_DIR / "results"

METRICS_PATH = RESULTS_DIR / "github_fusion_metrics.json"
PER_RESUME_CSV_PATH = RESULTS_DIR / "github_fusion_per_resume.csv"
REPORT_PATH = RESULTS_DIR / "github_fusion_report.md"
CACHE_PATH = RESULTS_DIR / "github_cache.json"

# ---------------------------------------------------------------------------
# GitHub language → canonical skill ID mapping
# Superset of production SKILL_LANGUAGE_MAP in github_skill_extractor.py.
# Canonical IDs must exist in SUPPORTED_SKILLS (i.e. in RESUME_SKILL_MAP.values()).
# ---------------------------------------------------------------------------
GITHUB_LANGUAGE_TO_SKILL: dict[str, str] = {
    # From production SKILL_LANGUAGE_MAP (normalised to ontology IDs)
    "Python": "python",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Go": "golang",
    "Rust": "rust",
    "Java": "java",
    "C++": "cpp",
    "CSS": "html-css",
    "HTML": "html-css",
    # Extended — map to canonical IDs already present in RESUME_SKILL_MAP values
    "Ruby": "ruby",
    "PHP": "php",
    "Swift": "swift",
    "Kotlin": "kotlin",
    "Scala": "scala",
    "C#": "csharp",
    "R": "r",
    "Dart": "flutter",        # Dart is used almost exclusively for Flutter
    "Shell": "linux",
    "Dockerfile": "docker",
    "HCL": "terraform",       # HashiCorp Configuration Language → Terraform
    "Solidity": "blockchain",
    "C": "cpp",               # Map C to closest canonical
}

# Minimum fraction of total language bytes required to claim a skill.
# Avoids spurious skills from tiny boilerplate files.
MIN_LANGUAGE_FRACTION = 0.01  # 1 %

# GitHub URL path segments that are NOT usernames
GITHUB_USERNAME_BLACKLIST: frozenset[str] = frozenset({
    "topics", "settings", "orgs", "enterprise", "features",
    "security", "pulls", "issues", "marketplace", "explore",
    "notifications", "new", "login", "join", "pricing",
    "about", "contact", "blog", "docs", "apps", "sponsors",
    "trending", "collections", "events", "discussions",
    "actions", "packages", "codespaces", "copilot",
})

GITHUB_API_BASE = "https://api.github.com"


# ---------------------------------------------------------------------------
# GitHub URL extraction
# ---------------------------------------------------------------------------

def extract_github_username(text: str) -> Optional[str]:
    """
    Find the first GitHub profile username in raw resume text.

    Handles common PDF text-extraction artifacts:
      - spaces around dots/slashes (e.g. "github . com / username")
      - http / https prefix or no prefix
      - trailing path components (only the first path segment = username)

    Returns the username string, or None if no valid username found.
    """
    # Normalise text: collapse whitespace around slashes and dots
    # to handle PDF artifacts like "github . com / username"
    normalised = re.sub(r'\s*\.\s*', '.', text.lower())
    normalised = re.sub(r'\s*/\s*', '/', normalised)

    # Primary pattern: github.com/<username>[/<anything>]
    pattern = r'github\.com/([a-z0-9](?:[a-z0-9\-]*[a-z0-9])?)'
    matches = re.findall(pattern, normalised)

    for candidate in matches:
        if candidate not in GITHUB_USERNAME_BLACKLIST and len(candidate) >= 1:
            return candidate

    return None


# ---------------------------------------------------------------------------
# GitHub API cache helpers
# ---------------------------------------------------------------------------

def load_github_cache(cache_path: Path) -> dict:
    """Load the API response cache from disk. Returns {} if file not found."""
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_github_cache(cache: dict, cache_path: Path) -> None:
    """Atomically write the cache to disk."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2)
    tmp_path.replace(cache_path)


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _github_get(url: str, headers: dict, retries: int = 3) -> Optional[dict | list]:
    """
    Make a GET request to the GitHub API.

    Handles:
      - 404  → returns None silently (user/repo not found)
      - 403 / 429 (rate limit) → sleeps until X-RateLimit-Reset, then retries
      - Other errors → returns None after logging

    Returns parsed JSON or None.
    """
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                remaining = resp.headers.get("X-RateLimit-Remaining", "999")
                if int(remaining) < 5:
                    reset_ts = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                    sleep_sec = max(1, reset_ts - int(time.time()) + 2)
                    print(f"  [GitHub] Rate limit low — sleeping {sleep_sec}s …")
                    time.sleep(sleep_sec)
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code in (403, 429):
                reset_ts_raw = exc.headers.get("X-RateLimit-Reset")
                sleep_sec = max(5, int(reset_ts_raw or 0) - int(time.time()) + 2) if reset_ts_raw else 60
                print(f"  [GitHub] Rate limited (HTTP {exc.code}) — sleeping {sleep_sec}s …")
                time.sleep(sleep_sec)
                continue
            print(f"  [GitHub] HTTP {exc.code} for {url}")
            return None
        except Exception as exc:
            print(f"  [GitHub] Error fetching {url}: {exc}")
            if attempt < retries - 1:
                time.sleep(2)
    return None


def fetch_github_languages(username: str, cache: dict, headers: dict) -> dict[str, int]:
    """
    Return aggregated language-byte counts for all non-fork, non-archived repos
    owned by `username`.  Results are read from / written to `cache` (mutated).

    Cache key: username
    Cache value: {"language_bytes": {lang: int}, "fetched_at": ISO timestamp}
    """
    cache_key = username.lower()

    if cache_key in cache:
        return cache[cache_key].get("language_bytes", {})

    print(f"  [GitHub] Fetching repos for '{username}' …")
    repos_url = f"{GITHUB_API_BASE}/users/{username}/repos?per_page=100&type=owner"
    repos_data = _github_get(repos_url, headers)

    if not isinstance(repos_data, list):
        print(f"  [GitHub] Could not fetch repos for '{username}' (user may not exist).")
        cache[cache_key] = {"language_bytes": {}, "fetched_at": datetime.datetime.utcnow().isoformat()}
        return {}

    language_bytes: dict[str, int] = {}
    api_calls = 0

    for repo in repos_data:
        if repo.get("fork") or repo.get("archived"):
            continue
        repo_full = repo.get("full_name", "")
        if not repo_full:
            continue

        lang_url = f"{GITHUB_API_BASE}/repos/{repo_full}/languages"
        lang_data = _github_get(lang_url, headers)
        api_calls += 1

        if isinstance(lang_data, dict):
            for lang, byte_count in lang_data.items():
                language_bytes[lang] = language_bytes.get(lang, 0) + byte_count

    print(f"  [GitHub] '{username}': {len(repos_data)} repos, {api_calls} lang API calls, "
          f"{len(language_bytes)} distinct languages found.")

    cache[cache_key] = {
        "language_bytes": language_bytes,
        "fetched_at": datetime.datetime.utcnow().isoformat(),
    }
    return language_bytes


# ---------------------------------------------------------------------------
# Language bytes → canonical skill IDs
# ---------------------------------------------------------------------------

def github_languages_to_skills(language_bytes: dict[str, int]) -> set[str]:
    """
    Map a {language: bytes} dict to a set of canonical platform skill IDs.

    Only languages that account for >= MIN_LANGUAGE_FRACTION of total bytes
    are included, to avoid noise from tiny boilerplate files.
    Only maps to canonical IDs that exist in SUPPORTED_SKILLS (ontology-constrained).
    """
    if not language_bytes:
        return set()

    total = sum(language_bytes.values()) or 1
    skills: set[str] = set()

    for lang, byte_count in language_bytes.items():
        if byte_count / total < MIN_LANGUAGE_FRACTION:
            continue
        canonical = GITHUB_LANGUAGE_TO_SKILL.get(lang)
        if canonical and canonical in SUPPORTED_SKILLS:
            skills.add(canonical)

    return skills


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def _macro_avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _micro_metrics(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def run_fusion_evaluation(no_cache: bool = False) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Setup GitHub API headers
    # -----------------------------------------------------------------------
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not github_token:
        print(
            "\n[WARN] GITHUB_TOKEN environment variable is not set.\n"
            "       The unauthenticated GitHub API rate limit is 60 requests/hour,\n"
            "       which is likely insufficient for this experiment.\n"
            "       Set GITHUB_TOKEN to a personal access token for 5000 req/hr.\n"
        )
    headers: dict[str, str] = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "LearnPathAI-Eval/1.0",
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    # -----------------------------------------------------------------------
    # Load ground truth and cache
    # -----------------------------------------------------------------------
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as fh:
        ground_truth_data = json.load(fh)
    annotations: list[dict] = ground_truth_data["annotations"]

    cache: dict = {} if no_cache else load_github_cache(CACHE_PATH)

    print(f"[Eval] Loaded ground truth for {len(annotations)} resumes.")
    print(f"[Eval] Platform ontology: {len(SUPPORTED_SKILLS)} canonical skill IDs")
    print(f"[Eval] GitHub cache entries loaded: {len(cache)}")
    print(f"[Eval] Mode: ontology-constrained\n")

    # -----------------------------------------------------------------------
    # Per-resume tracking
    # -----------------------------------------------------------------------
    per_resume_rows: list[dict] = []

    # All-corpus (resume-only) counters
    ro_total_tp = ro_total_fp = ro_total_fn = 0
    ro_precisions: list[float] = []
    ro_recalls: list[float] = []
    ro_f1s: list[float] = []

    # GitHub-cohort counters (resumes with a detectable GitHub username)
    gh_total_tp = gh_total_fp = gh_total_fn = 0
    gh_precisions: list[float] = []
    gh_recalls: list[float] = []
    gh_f1s: list[float] = []

    fu_total_tp = fu_total_fp = fu_total_fn = 0
    fu_precisions: list[float] = []
    fu_recalls: list[float] = []
    fu_f1s: list[float] = []

    ro_total_fp_skills: list[str] = []
    ro_total_fn_skills: list[str] = []

    evaluated_total = skipped = 0
    github_cohort_count = 0
    github_usernames_found: dict[str, str] = {}   # resume_id → username

    for entry in annotations:
        resume_file: str = entry["resume_file"]
        annotated_skills: list[str] = entry["annotated_skills"]
        pdf_path = ENGINEERING_DIR / resume_file

        if not pdf_path.exists():
            print(f"[Eval] SKIP (not found): {resume_file}")
            skipped += 1
            continue

        # --- Production resume extraction ---
        try:
            text = extract_text_from_pdf(str(pdf_path))
            resume_skills: set[str] = set(extract_skills_from_text(text).keys())
        except Exception as exc:
            print(f"[Eval] ERROR processing {resume_file}: {exc}")
            skipped += 1
            continue

        # --- Ground truth preparation ---
        gt_canonicals, _ = ground_truth_to_canonicals(annotated_skills)

        # --- Resume-only metrics (all corpus) ---
        ro_tp, ro_fp, ro_fn, ro_p, ro_r, ro_f1 = compute_metrics(resume_skills, gt_canonicals)
        ro_total_tp += ro_tp
        ro_total_fp += ro_fp
        ro_total_fn += ro_fn
        ro_precisions.append(ro_p)
        ro_recalls.append(ro_r)
        ro_f1s.append(ro_f1)
        ro_total_fp_skills.extend(sorted(resume_skills - gt_canonicals))
        ro_total_fn_skills.extend(sorted(gt_canonicals - resume_skills))

        evaluated_total += 1

        # --- GitHub username extraction ---
        username = extract_github_username(text)

        # --- GitHub skill fetching (only if username found) ---
        github_skills: set[str] = set()
        if username:
            github_usernames_found[resume_file] = username
            print(f"[Eval] {resume_file} → GitHub: '{username}'")
            language_bytes = fetch_github_languages(username, cache, headers)
            github_skills = github_languages_to_skills(language_bytes)
            # Save cache after each user to preserve progress
            save_github_cache(cache, CACHE_PATH)
        else:
            print(f"[Eval] {resume_file} → no GitHub link detected")

        # --- Fusion ---
        fusion_skills: set[str] = resume_skills | github_skills

        # --- GitHub cohort metrics ---
        gh_tp, gh_fp, gh_fn, gh_p, gh_r, gh_f1 = compute_metrics(github_skills, gt_canonicals)
        fu_tp, fu_fp, fu_fn, fu_p, fu_r, fu_f1 = compute_metrics(fusion_skills, gt_canonicals)

        if username:
            github_cohort_count += 1
            gh_total_tp += gh_tp
            gh_total_fp += gh_fp
            gh_total_fn += gh_fn
            gh_precisions.append(gh_p)
            gh_recalls.append(gh_r)
            gh_f1s.append(gh_f1)

            fu_total_tp += fu_tp
            fu_total_fp += fu_fp
            fu_total_fn += fu_fn
            fu_precisions.append(fu_p)
            fu_recalls.append(fu_r)
            fu_f1s.append(fu_f1)

        per_resume_rows.append({
            "resume_id": resume_file,
            "github_username": username or "",
            "has_github": "yes" if username else "no",
            "resume_skills": "|".join(sorted(resume_skills)),
            "github_skills": "|".join(sorted(github_skills)),
            "fusion_skills": "|".join(sorted(fusion_skills)),
            "ground_truth_skills": "|".join(sorted(gt_canonicals)),
            "precision_resume": round(ro_p, 4),
            "precision_github": round(gh_p, 4) if username else "",
            "precision_fusion": round(fu_p, 4) if username else "",
            "recall_resume": round(ro_r, 4),
            "recall_github": round(gh_r, 4) if username else "",
            "recall_fusion": round(fu_r, 4) if username else "",
            "f1_resume": round(ro_f1, 4),
            "f1_github": round(gh_f1, 4) if username else "",
            "f1_fusion": round(fu_f1, 4) if username else "",
        })

    # Ensure cache is saved at the end
    save_github_cache(cache, CACHE_PATH)

    # -----------------------------------------------------------------------
    # Aggregate metrics
    # -----------------------------------------------------------------------

    # Resume-only (full corpus)
    ro_macro_p = _macro_avg(ro_precisions)
    ro_macro_r = _macro_avg(ro_recalls)
    ro_macro_f1 = _macro_avg(ro_f1s)
    ro_micro_p, ro_micro_r, ro_micro_f1 = _micro_metrics(ro_total_tp, ro_total_fp, ro_total_fn)

    # GitHub-only and fusion (GitHub cohort only)
    gh_macro_p = _macro_avg(gh_precisions)
    gh_macro_r = _macro_avg(gh_recalls)
    gh_macro_f1 = _macro_avg(gh_f1s)
    gh_micro_p, gh_micro_r, gh_micro_f1 = _micro_metrics(gh_total_tp, gh_total_fp, gh_total_fn)

    fu_macro_p = _macro_avg(fu_precisions)
    fu_macro_r = _macro_avg(fu_recalls)
    fu_macro_f1 = _macro_avg(fu_f1s)
    fu_micro_p, fu_micro_r, fu_micro_f1 = _micro_metrics(fu_total_tp, fu_total_fp, fu_total_fn)

    top_ro_fp = Counter(ro_total_fp_skills).most_common(10)
    top_ro_fn = Counter(ro_total_fn_skills).most_common(10)

    # -----------------------------------------------------------------------
    # Write github_fusion_metrics.json
    # -----------------------------------------------------------------------
    metrics = {
        "evaluation_mode": "ontology_constrained",
        "ontology_size": len(SUPPORTED_SKILLS),
        "resumes_evaluated_total": evaluated_total,
        "resumes_skipped": skipped,
        "resumes_with_github": github_cohort_count,
        "note_cohort": (
            "resume_only metrics computed over all evaluated resumes. "
            "github_only and fusion metrics computed only over resumes "
            "with a detectable GitHub profile URL."
        ),
        "resume_only": {
            "cohort": "all_resumes",
            "cohort_size": evaluated_total,
            "macro_precision": round(ro_macro_p, 4),
            "macro_recall": round(ro_macro_r, 4),
            "macro_f1": round(ro_macro_f1, 4),
            "micro_precision": round(ro_micro_p, 4),
            "micro_recall": round(ro_micro_r, 4),
            "micro_f1": round(ro_micro_f1, 4),
            "total_tp": ro_total_tp,
            "total_fp": ro_total_fp,
            "total_fn": ro_total_fn,
        },
        "github_only": {
            "cohort": "resumes_with_github",
            "cohort_size": github_cohort_count,
            "macro_precision": round(gh_macro_p, 4),
            "macro_recall": round(gh_macro_r, 4),
            "macro_f1": round(gh_macro_f1, 4),
            "micro_precision": round(gh_micro_p, 4),
            "micro_recall": round(gh_micro_r, 4),
            "micro_f1": round(gh_micro_f1, 4),
            "total_tp": gh_total_tp,
            "total_fp": gh_total_fp,
            "total_fn": gh_total_fn,
        },
        "fusion": {
            "cohort": "resumes_with_github",
            "cohort_size": github_cohort_count,
            "macro_precision": round(fu_macro_p, 4),
            "macro_recall": round(fu_macro_r, 4),
            "macro_f1": round(fu_macro_f1, 4),
            "micro_precision": round(fu_micro_p, 4),
            "micro_recall": round(fu_micro_r, 4),
            "micro_f1": round(fu_micro_f1, 4),
            "total_tp": fu_total_tp,
            "total_fp": fu_total_fp,
            "total_fn": fu_total_fn,
        },
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    print(f"\n[Eval] Metrics saved → {METRICS_PATH}")

    # -----------------------------------------------------------------------
    # Write github_fusion_per_resume.csv
    # -----------------------------------------------------------------------
    csv_columns = [
        "resume_id", "github_username", "has_github",
        "resume_skills", "github_skills", "fusion_skills", "ground_truth_skills",
        "precision_resume", "precision_github", "precision_fusion",
        "recall_resume", "recall_github", "recall_fusion",
        "f1_resume", "f1_github", "f1_fusion",
    ]
    with open(PER_RESUME_CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(per_resume_rows)
    print(f"[Eval] Per-resume CSV saved → {PER_RESUME_CSV_PATH}")

    # -----------------------------------------------------------------------
    # Write github_fusion_report.md
    # -----------------------------------------------------------------------
    today = datetime.date.today()
    fusion_recall_delta = round(fu_macro_r - ro_macro_r, 4)
    fusion_f1_delta = round(fu_macro_f1 - ro_macro_f1, 4)
    fusion_improves_recall = fusion_recall_delta > 0
    fusion_improves_f1 = fusion_f1_delta > 0

    report_lines = [
        "# Experiment Report — GitHub Skill Fusion Evaluation",
        "",
        "## Dataset Description",
        "",
        f"- **Corpus**: `ENGINEERING/` — 118 engineering resumes (PDF)",
        f"- **Ground truth**: `experiments/skill_ground_truth/resume_skill_annotations.json`",
        f"- **Total resumes annotated**: {len(annotations)}",
        f"- **Resumes successfully evaluated**: {evaluated_total}",
        f"- **Resumes skipped** (file not found or parse error): {skipped}",
        f"- **Resumes with detectable GitHub profile URL**: {github_cohort_count}",
        "",
        "### GitHub profiles found",
        "",
    ]
    if github_usernames_found:
        report_lines += [
            "| Resume | GitHub Username |",
            "| --- | --- |",
        ]
        for rid, uname in sorted(github_usernames_found.items()):
            report_lines.append(f"| `{rid}` | `{uname}` |")
    else:
        report_lines.append(
            "_No GitHub profile URLs were detected in any resume in this corpus._"
        )

    report_lines += [
        "",
        "## Evaluation Methodology",
        "",
        "This experiment evaluates three skill-inference strategies:",
        "",
        "| Strategy | Description |",
        "| --- | --- |",
        "| **Resume-only** | Production `extract_text_from_pdf` + `extract_skills_from_text` |",
        "| **GitHub-only** | Public GitHub API language bytes aggregated across all non-fork repos, mapped to canonical skill IDs |",
        "| **Fusion** | Union of resume-only and GitHub-only skill sets |",
        "",
        "**Evaluation mode**: ontology-constrained. Ground-truth skills that do not map",
        "to a canonical ID in the platform's `RESUME_SKILL_MAP` are excluded before",
        "computing TP/FP/FN. This is identical to the methodology in",
        "`experiments/evaluate_skill_extraction.py`.",
        "",
        "**Cohort note**: Resume-only metrics are computed over *all* evaluated resumes.",
        "GitHub-only and fusion metrics are computed only over the subset of resumes",
        "where a GitHub profile URL was detected — this makes the comparison fair.",
        "",
        "**GitHub language threshold**: Languages accounting for < 1% of total repository",
        "bytes are ignored to suppress noise from boilerplate files.",
        "",
        "## Results",
        "",
        "### Full-corpus resume-only baseline",
        "",
        f"(N = {evaluated_total} resumes)",
        "",
        "| Metric | Macro-avg | Micro (totals) |",
        "| --- | --- | --- |",
        f"| Precision | {ro_macro_p:.4f} | {ro_micro_p:.4f} |",
        f"| Recall    | {ro_macro_r:.4f} | {ro_micro_r:.4f} |",
        f"| F1 Score  | {ro_macro_f1:.4f} | {ro_micro_f1:.4f} |",
        "",
        f"Total TP: {ro_total_tp} &nbsp; FP: {ro_total_fp} &nbsp; FN: {ro_total_fn}",
        "",
    ]

    if github_cohort_count > 0:
        report_lines += [
            f"### GitHub-cohort comparison (N = {github_cohort_count} resumes)",
            "",
            "_All three methods evaluated on the same subset of resumes that have_",
            "_a detectable GitHub profile URL._",
            "",
            "| Strategy | Macro Prec | Macro Rec | Macro F1 | Micro Prec | Micro Rec | Micro F1 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            f"| Resume-only (cohort) | — | — | — | — | — | — |",
            f"| GitHub-only | {gh_macro_p:.4f} | {gh_macro_r:.4f} | {gh_macro_f1:.4f} | {gh_micro_p:.4f} | {gh_micro_r:.4f} | {gh_micro_f1:.4f} |",
            f"| Fusion | {fu_macro_p:.4f} | {fu_macro_r:.4f} | {fu_macro_f1:.4f} | {fu_micro_p:.4f} | {fu_micro_r:.4f} | {fu_micro_f1:.4f} |",
            "",
            "_(Resume-only cohort metrics are not shown separately here;",
            "see per-resume CSV for individual values.)_",
            "",
            "## Analysis",
            "",
        ]
        if fusion_improves_recall and fusion_improves_f1:
            report_lines += [
                f"Fusion **improves both recall and F1** over resume-only on the GitHub cohort.",
                f"Recall gain: +{fusion_recall_delta:.4f}  |  F1 gain: +{fusion_f1_delta:.4f}",
                "",
                "GitHub language data adds complementary signal — it catches skills that are",
                "present in code repositories but not explicitly named in the resume text.",
            ]
        elif fusion_improves_recall:
            report_lines += [
                f"Fusion **improves recall** (+{fusion_recall_delta:.4f}) but at the cost of",
                f"precision, leaving F1 {'improved' if fusion_f1_delta >= 0 else 'slightly reduced'} ({fusion_f1_delta:+.4f}).",
                "",
                "GitHub language data adds breadth (higher recall) but also introduces",
                "false positives for languages that appear in cloned/educational repos.",
            ]
        elif fusion_improves_f1:
            report_lines += [
                f"Fusion **improves F1** (+{fusion_f1_delta:.4f}).",
            ]
        else:
            report_lines += [
                "Fusion does not improve recall or F1 on this corpus.",
                "",
                "This is likely because the GitHub cohort is very small "
                f"(N = {github_cohort_count}) and/or the resumes belong to",
                "engineering roles where GitHub language signal overlaps heavily with",
                "what is already present in the resume text.",
            ]
    else:
        report_lines += [
            "## Analysis",
            "",
            f"No GitHub profile URLs were detected in any of the {evaluated_total} evaluated",
            "resumes. The GitHub-only and fusion experiments could not be run.",
            "",
            "**Possible reasons:**",
            "- The ENGINEERING corpus is predominantly hardware/civil/mechanical engineering",
            "  resumes, which typically do not include GitHub profiles.",
            "- GitHub URLs may be present but obscured by PDF encoding (e.g. fonts that",
            "  render the slash character differently).",
            "",
            "To test GitHub fusion with this pipeline, add resumes that contain",
            "detectable `github.com/<username>` links.",
        ]

    report_lines += [
        "",
        "## Top 10 Most Common False Positives (resume-only, full corpus)",
        "",
        "| Rank | Skill | Count |",
        "| --- | --- | --- |",
    ]
    for i, (skill, count) in enumerate(top_ro_fp, start=1):
        report_lines.append(f"| {i} | `{skill}` | {count} |")

    report_lines += [
        "",
        "## Top 10 Most Commonly Missed Skills (resume-only, full corpus)",
        "",
        "| Rank | Skill | Count |",
        "| --- | --- | --- |",
    ]
    for i, (skill, count) in enumerate(top_ro_fn, start=1):
        report_lines.append(f"| {i} | `{skill}` | {count} |")

    report_lines += [
        "",
        "---",
        f"*Generated by `experiments/evaluate_github_fusion.py` on {today}*",
    ]

    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(report_lines) + "\n")
    print(f"[Eval] Report saved → {REPORT_PATH}")

    # -----------------------------------------------------------------------
    # Terminal summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("GITHUB SKILL FUSION EVALUATION — SUMMARY")
    print("=" * 70)
    print(f"  Ontology size            : {len(SUPPORTED_SKILLS)} canonical skills")
    print(f"  Resumes evaluated        : {evaluated_total}")
    print(f"  Resumes with GitHub      : {github_cohort_count}")
    print()
    print("  === RESUME-ONLY (all corpus) ===")
    print(f"  Macro  P / R / F1        : {ro_macro_p:.4f}  /  {ro_macro_r:.4f}  /  {ro_macro_f1:.4f}")
    print(f"  Micro  P / R / F1        : {ro_micro_p:.4f}  /  {ro_micro_r:.4f}  /  {ro_micro_f1:.4f}")
    print(f"  TP / FP / FN             : {ro_total_tp} / {ro_total_fp} / {ro_total_fn}")

    if github_cohort_count > 0:
        print()
        print(f"  === GITHUB-ONLY (N={github_cohort_count} resumes with GitHub) ===")
        print(f"  Macro  P / R / F1        : {gh_macro_p:.4f}  /  {gh_macro_r:.4f}  /  {gh_macro_f1:.4f}")
        print(f"  Micro  P / R / F1        : {gh_micro_p:.4f}  /  {gh_micro_r:.4f}  /  {gh_micro_f1:.4f}")
        print(f"  TP / FP / FN             : {gh_total_tp} / {gh_total_fp} / {gh_total_fn}")
        print()
        print(f"  === FUSION (N={github_cohort_count} resumes with GitHub) ===")
        print(f"  Macro  P / R / F1        : {fu_macro_p:.4f}  /  {fu_macro_r:.4f}  /  {fu_macro_f1:.4f}")
        print(f"  Micro  P / R / F1        : {fu_micro_p:.4f}  /  {fu_micro_r:.4f}  /  {fu_micro_f1:.4f}")
        print(f"  TP / FP / FN             : {fu_total_tp} / {fu_total_fp} / {fu_total_fn}")
        print()
        recall_arrow = "▲" if fusion_recall_delta > 0 else ("▼" if fusion_recall_delta < 0 else "=")
        f1_arrow = "▲" if fusion_f1_delta > 0 else ("▼" if fusion_f1_delta < 0 else "=")
        print(f"  Fusion recall vs resume  : {recall_arrow} {fusion_recall_delta:+.4f}")
        print(f"  Fusion F1 vs resume      : {f1_arrow} {fusion_f1_delta:+.4f}")
    else:
        print()
        print("  No GitHub profiles detected — GitHub/fusion metrics not computed.")

    print("=" * 70)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    no_cache_flag = "--no-cache" in sys.argv
    if no_cache_flag:
        print("[Eval] --no-cache flag set: ignoring existing GitHub cache.")
    run_fusion_evaluation(no_cache=no_cache_flag)
