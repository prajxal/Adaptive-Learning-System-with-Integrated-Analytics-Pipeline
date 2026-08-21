"""
GitHub Skill Extraction Accuracy Evaluation
============================================
Evaluates how accurately the production GitHub skill extraction pipeline
identifies a developer's primary programming language.

For each of 30 hardcoded public GitHub users the script:
  1. Fetches language byte distribution and per-repo commit counts via the
     GitHub REST API (responses are cached to disk for offline replay).
  2. Calls compute_skill_weights() — imported directly from the production
     extractor — to obtain the ranked skill predictions.
  3. Derives ground truth as the SKILL_LANGUAGE_MAP language with the highest
     aggregate byte count across non-fork, non-archived repos.
  4. Computes top-1 accuracy, top-3 accuracy, per-class precision/recall/F1
     (macro-averaged), and dominant_language_ratio per user.

Usage:
    cd <repo_root>
    python backend/scripts/evaluate_github_skill_extraction.py \\
        --token $GITHUB_TOKEN

    # Quick smoke test (first 5 users only):
    python backend/scripts/evaluate_github_skill_extraction.py \\
        --token $GITHUB_TOKEN --limit 5

    # Force API refresh (ignore disk cache):
    python backend/scripts/evaluate_github_skill_extraction.py \\
        --token $GITHUB_TOKEN --no-cache

Outputs:
    backend/experiments/github_skill_evaluation.csv
    backend/experiments/github_skill_evaluation_metrics.json
    Terminal: per-user table + aggregate metrics + LaTeX snippet
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allows bare imports from backend/
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Import the canonical weighting logic and language map directly from the
# production extractor.  No database connection is required because we moved
# the DB-coupled imports to lazy (function-body) imports in that module.
from services.github_skill_extractor import (  # noqa: E402
    SKILL_LANGUAGE_MAP,
    compute_skill_weights,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_DIR = BACKEND_DIR / "experiments"
CSV_PATH = OUTPUT_DIR / "github_skill_evaluation.csv"
METRICS_PATH = OUTPUT_DIR / "github_skill_evaluation_metrics.json"
CACHE_DIR = OUTPUT_DIR / ".github_cache"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GITHUB_API_BASE = "https://api.github.com"
# Reverse map: roadmap_skill → canonical language name
ROADMAP_TO_LANGUAGE: dict[str, str] = {v: k for k, v in SKILL_LANGUAGE_MAP.items()}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded candidate users (30 total)
# Sampled for language diversity across all 9 keys in SKILL_LANGUAGE_MAP.
# "sampled_for" is only used for diversity bookkeeping; actual ground truth
# is derived from the GitHub API at runtime.
# To regenerate this list run: python ... --discover
# ---------------------------------------------------------------------------
CANDIDATE_USERS: list[dict[str, str]] = [
    # Python (5)
    {"username": "gvanrossum",      "sampled_for": "Python"},
    {"username": "tiangolo",        "sampled_for": "Python"},
    {"username": "kennethreitz",    "sampled_for": "Python"},
    {"username": "agronholm",       "sampled_for": "Python"},
    {"username": "pawamoy",         "sampled_for": "Python"},
    # JavaScript (5)
    {"username": "sindresorhus",    "sampled_for": "JavaScript"},
    {"username": "nicolo-ribaudo",  "sampled_for": "JavaScript"},
    {"username": "developit",       "sampled_for": "JavaScript"},
    {"username": "jlongster",       "sampled_for": "JavaScript"},
    {"username": "ljharb",          "sampled_for": "JavaScript"},
    # TypeScript (4)
    {"username": "orta",            "sampled_for": "TypeScript"},
    {"username": "antfu",           "sampled_for": "TypeScript"},
    {"username": "wesbos",          "sampled_for": "TypeScript"},
    {"username": "DavidWells",      "sampled_for": "TypeScript"},
    # Go (5)
    {"username": "bradfitz",        "sampled_for": "Go"},
    {"username": "rsc",             "sampled_for": "Go"},
    {"username": "peterbourgon",    "sampled_for": "Go"},
    {"username": "mvdan",           "sampled_for": "Go"},
    {"username": "cespare",         "sampled_for": "Go"},
    # Rust (5)
    {"username": "steveklabnik",    "sampled_for": "Rust"},
    {"username": "dtolnay",         "sampled_for": "Rust"},
    {"username": "aturon",          "sampled_for": "Rust"},
    {"username": "withoutboats",    "sampled_for": "Rust"},
    {"username": "BurntSushi",      "sampled_for": "Rust"},
    # Java (3)
    {"username": "iluwatar",        "sampled_for": "Java"},
    {"username": "cbeust",          "sampled_for": "Java"},
    {"username": "brunoborges",     "sampled_for": "Java"},
    # C++ (3)
    {"username": "nothings",        "sampled_for": "C++"},
    {"username": "ericniebler",     "sampled_for": "C++"},
    {"username": "jfbastien",       "sampled_for": "C++"},
]

assert len(CANDIDATE_USERS) == 30, "CANDIDATE_USERS must contain exactly 30 entries"
assert len({u["username"] for u in CANDIDATE_USERS}) == 30, "Duplicate username detected"

# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _cache_path(username: str) -> Path:
    return CACHE_DIR / f"{username}.json"


def _load_cache(username: str) -> dict | None:
    p = _cache_path(username)
    if p.exists():
        with p.open() as f:
            return json.load(f)
    return None


def _save_cache(username: str, data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with _cache_path(username).open("w") as f:
        json.dump(data, f)


async def _get(client, url: str, headers: dict, backoff: float = 1.0) -> dict | list | None:
    """GET with simple exponential backoff on rate-limit responses."""
    for attempt in range(4):
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (403, 429):
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + backoff))
            wait = max(0.5, reset - time.time()) if attempt == 0 else backoff * (2 ** attempt)
            logger.warning("Rate limited on %s — sleeping %.1fs", url, wait)
            await asyncio.sleep(wait)
        else:
            logger.debug("HTTP %d for %s", resp.status_code, url)
            return None
    return None


async def fetch_user_language_data(
    username: str,
    token: str | None,
    use_cache: bool = True,
) -> dict:
    """Fetch raw language bytes and commit counts for a GitHub user.

    Returns a dict with keys:
        language_bytes   — {language: total_bytes across non-fork/non-archived repos}
        language_commits — {language: commit_count based on repo primary language}
        repos_analyzed   — number of repos processed
        total_bytes      — sum of all language_bytes values
        error            — error message string, or None
    """
    if use_cache:
        cached = _load_cache(username)
        if cached is not None:
            logger.info("[cache] %s", username)
            return cached

    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    language_bytes: dict[str, int] = {}
    language_commits: dict[str, int] = {}
    repos_analyzed = 0
    error: str | None = None

    try:
        import httpx  # noqa: PLC0415 — already in requirements.txt

        async with httpx.AsyncClient(timeout=20.0) as client:
            # Collect non-fork, non-archived repos (paginated)
            repos: list[dict] = []
            page = 1
            while True:
                url = f"{GITHUB_API_BASE}/users/{username}/repos?per_page=100&page={page}&type=owner"
                data = await _get(client, url, headers)
                if not data:
                    break
                batch = [r for r in data if not r.get("fork") and not r.get("archived")]
                repos.extend(batch)
                if len(data) < 100:
                    break
                page += 1

            repos_analyzed = len(repos)

            # Fetch language bytes and commit counts per repo
            for repo in repos:
                full_name = repo["full_name"]

                lang_data = await _get(
                    client,
                    f"{GITHUB_API_BASE}/repos/{full_name}/languages",
                    headers,
                )
                if lang_data:
                    for lang, byte_count in lang_data.items():
                        language_bytes[lang] = language_bytes.get(lang, 0) + byte_count

                # Commit count: mirrors production behaviour — fetches one page (max 30)
                # and counts the list length based on repo primary language.
                commits_data = await _get(
                    client,
                    f"{GITHUB_API_BASE}/repos/{full_name}/commits?author={username}&per_page=30",
                    headers,
                )
                if isinstance(commits_data, list):
                    count = len(commits_data)
                    primary_lang = repo.get("language")
                    if primary_lang and count > 0:
                        language_commits[primary_lang] = language_commits.get(primary_lang, 0) + count

    except Exception as exc:
        error = str(exc)
        logger.error("Error fetching %s: %s", username, exc)

    result = {
        "language_bytes": language_bytes,
        "language_commits": language_commits,
        "repos_analyzed": repos_analyzed,
        "total_bytes": sum(language_bytes.values()),
        "error": error,
    }
    if use_cache and error is None:
        _save_cache(username, result)
    return result


# ---------------------------------------------------------------------------
# Ground truth + prediction helpers
# ---------------------------------------------------------------------------

def compute_ground_truth(language_bytes: dict[str, int]) -> tuple[str | None, str | None]:
    """Return (dominant_language, dominant_roadmap_skill) from raw byte counts.

    Only considers languages present in SKILL_LANGUAGE_MAP.  Returns
    (None, None) if no mapped language has any bytes.
    """
    best_lang: str | None = None
    best_bytes = 0
    for lang in SKILL_LANGUAGE_MAP:
        b = language_bytes.get(lang, 0)
        if b > best_bytes:
            best_bytes = b
            best_lang = lang
    if best_lang is None:
        return None, None
    return best_lang, SKILL_LANGUAGE_MAP[best_lang]


# ---------------------------------------------------------------------------
# Per-user evaluation
# ---------------------------------------------------------------------------

async def evaluate_user(
    entry: dict[str, str],
    token: str | None,
    use_cache: bool,
) -> dict:
    username = entry["username"]
    raw = await fetch_user_language_data(username, token, use_cache)

    result: dict = {
        "username": username,
        "sampled_for": entry["sampled_for"],
        "repos_analyzed": raw["repos_analyzed"],
        "total_bytes": raw["total_bytes"],
        "error": raw["error"],
        "ground_truth_language": None,
        "ground_truth_roadmap_skill": None,
        "predicted_primary_language": None,
        "predicted_primary_skill": None,
        "match": False,
        "top3_match": False,
        "dominant_language_ratio": None,
        "all_weights": "{}",
    }

    if raw["error"]:
        return result

    if raw["total_bytes"] == 0:
        result["error"] = "no_bytes"
        return result

    gt_lang, gt_skill = compute_ground_truth(raw["language_bytes"])

    if gt_lang is None:
        result["error"] = "unmapped_dominant_language"
        return result

    # Dominant language ratio: fraction of total bytes in the dominant mapped language
    dominant_bytes = raw["language_bytes"].get(gt_lang, 0)
    total_bytes = raw["total_bytes"]
    dominant_language_ratio = dominant_bytes / total_bytes if total_bytes > 0 else 0.0

    # Run the production weighting formula (imported from the extractor)
    skill_weights = compute_skill_weights(raw["language_bytes"], raw["language_commits"])

    all_weights_dict = {w["roadmap_skill"]: round(w["combined_weight"], 6) for w in skill_weights}

    top1 = skill_weights[0] if skill_weights else None
    top3_skills = {w["roadmap_skill"] for w in skill_weights[:3]}

    match = top1 is not None and top1["roadmap_skill"] == gt_skill
    top3_match = gt_skill in top3_skills

    result.update({
        "ground_truth_language": gt_lang,
        "ground_truth_roadmap_skill": gt_skill,
        "predicted_primary_language": top1["language"] if top1 else None,
        "predicted_primary_skill": top1["roadmap_skill"] if top1 else None,
        "match": match,
        "top3_match": top3_match,
        "dominant_language_ratio": round(dominant_language_ratio, 4),
        "all_weights": json.dumps(all_weights_dict),
    })
    return result


# ---------------------------------------------------------------------------
# Metrics (hand-rolled — no sklearn dependency)
# ---------------------------------------------------------------------------

def compute_metrics(results: list[dict]) -> dict:
    evaluated = [r for r in results if r["error"] is None and r["ground_truth_roadmap_skill"]]

    if not evaluated:
        return {}

    top1_correct = sum(1 for r in evaluated if r["match"])
    top3_correct = sum(1 for r in evaluated if r["top3_match"])
    n = len(evaluated)

    top1_accuracy = top1_correct / n
    top3_accuracy = top3_correct / n

    # Collect dominant_language_ratio stats (only for evaluated users)
    ratios = [r["dominant_language_ratio"] for r in evaluated if r["dominant_language_ratio"] is not None]
    mean_dominant_ratio = sum(ratios) / len(ratios) if ratios else 0.0

    # Per-class TP / FP / FN
    classes = sorted({r["ground_truth_roadmap_skill"] for r in evaluated})
    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)
    support: dict[str, int] = defaultdict(int)

    for r in evaluated:
        gt = r["ground_truth_roadmap_skill"]
        pred = r["predicted_primary_skill"]
        support[gt] += 1
        if pred == gt:
            tp[gt] += 1
        else:
            fn[gt] += 1
            if pred:
                fp[pred] += 1

    per_class: list[dict] = []
    for cls in classes:
        p = tp[cls] / (tp[cls] + fp[cls]) if (tp[cls] + fp[cls]) > 0 else 0.0
        r_score = tp[cls] / (tp[cls] + fn[cls]) if (tp[cls] + fn[cls]) > 0 else 0.0
        f1 = 2 * p * r_score / (p + r_score) if (p + r_score) > 0 else 0.0
        per_class.append({
            "roadmap_skill": cls,
            "support": support[cls],
            "precision": round(p, 4),
            "recall": round(r_score, 4),
            "f1": round(f1, 4),
        })

    macro_precision = sum(c["precision"] for c in per_class) / len(per_class) if per_class else 0.0
    macro_recall = sum(c["recall"] for c in per_class) / len(per_class) if per_class else 0.0
    macro_f1 = sum(c["f1"] for c in per_class) / len(per_class) if per_class else 0.0

    return {
        "n_evaluated": n,
        "n_unmapped_or_error": len(results) - n,
        "top1_accuracy": round(top1_accuracy, 4),
        "top3_accuracy": round(top3_accuracy, 4),
        "mean_dominant_language_ratio": round(mean_dominant_ratio, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
CSV_COLUMNS = [
    "username",
    "sampled_for",
    "ground_truth_language",
    "ground_truth_roadmap_skill",
    "predicted_primary_language",
    "predicted_primary_skill",
    "match",
    "top3_match",
    "repos_analyzed",
    "total_bytes",
    "dominant_language_ratio",
    "all_weights",
    "error",
]


def write_csv(results: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for r in results:
            writer.writerow({col: r.get(col) for col in CSV_COLUMNS})
    logger.info("CSV → %s", CSV_PATH)


def write_metrics_json(metrics: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime  # noqa: PLC0415
    payload = {"generated_at": datetime.utcnow().isoformat() + "Z", **metrics}
    with METRICS_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    logger.info("Metrics JSON → %s", METRICS_PATH)


def print_summary(results: list[dict], metrics: dict) -> None:
    COL_W = 22

    print("\n" + "=" * 72)
    print("GITHUB SKILL EXTRACTION — EVALUATION RESULTS")
    print("=" * 72)

    # Per-user table
    header = (
        f"{'username':<20} {'ground_truth':<22} {'predicted':<22} "
        f"{'match':<6} {'top3':<5} {'dom_ratio':<10}"
    )
    print(header)
    print("-" * 72)
    for r in results:
        gt = r.get("ground_truth_roadmap_skill") or r.get("error") or "—"
        pred = r.get("predicted_primary_skill") or "—"
        match_sym = "Y" if r.get("match") else ("—" if r.get("error") else "N")
        top3_sym = "Y" if r.get("top3_match") else ("—" if r.get("error") else "N")
        ratio = f"{r['dominant_language_ratio']:.3f}" if r.get("dominant_language_ratio") is not None else "—"
        print(
            f"{r['username']:<20} {gt:<22} {pred:<22} "
            f"{match_sym:<6} {top3_sym:<5} {ratio:<10}"
        )

    if not metrics:
        print("\n[No evaluated users — check --token and network connectivity]")
        return

    # Aggregate metrics
    print("\n" + "=" * 72)
    print("AGGREGATE METRICS")
    print("=" * 72)
    print(f"  Users evaluated              : {metrics['n_evaluated']}")
    print(f"  Unmapped / error             : {metrics['n_unmapped_or_error']}")
    print(f"  Top-1 accuracy               : {metrics['top1_accuracy']:.4f}")
    print(f"  Top-3 accuracy               : {metrics['top3_accuracy']:.4f}")
    print(f"  Mean dominant_language_ratio : {metrics['mean_dominant_language_ratio']:.4f}")
    print(f"  Macro precision              : {metrics['macro_precision']:.4f}")
    print(f"  Macro recall                 : {metrics['macro_recall']:.4f}")
    print(f"  Macro F1                     : {metrics['macro_f1']:.4f}")

    # Per-class table
    print()
    hdr = f"{'Roadmap skill':<{COL_W}} {'Support':>8}  {'Precision':>10}  {'Recall':>8}  {'F1':>8}"
    print(hdr)
    print("-" * 65)
    for c in metrics["per_class"]:
        print(
            f"{c['roadmap_skill']:<{COL_W}} {c['support']:>8}  "
            f"{c['precision']:>10.4f}  {c['recall']:>8.4f}  {c['f1']:>8.4f}"
        )
    print("-" * 65)
    print(
        f"{'MACRO AVERAGE':<{COL_W}} {metrics['n_evaluated']:>8}  "
        f"{metrics['macro_precision']:>10.4f}  {metrics['macro_recall']:>8.4f}  "
        f"{metrics['macro_f1']:>8.4f}"
    )
    print("=" * 72)

    # LaTeX table snippet
    print("\n% --- LaTeX table (copy into paper) ---")
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\begin{tabular}{lrrrr}")
    print(r"\hline")
    print(r"Roadmap Skill & Support & Precision & Recall & F1 \\")
    print(r"\hline")
    for c in metrics["per_class"]:
        skill_tex = c["roadmap_skill"].replace("_", r"\_")
        print(
            f"{skill_tex} & {c['support']} & "
            f"{c['precision']:.4f} & {c['recall']:.4f} & {c['f1']:.4f} \\\\"
        )
    print(r"\hline")
    print(
        f"\\textbf{{Macro avg}} & {metrics['n_evaluated']} & "
        f"{metrics['macro_precision']:.4f} & {metrics['macro_recall']:.4f} & "
        f"{metrics['macro_f1']:.4f} \\\\"
    )
    print(r"\hline")
    print(r"\end{tabular}")
    print(
        r"\caption{GitHub skill extraction accuracy — top-1: "
        f"{metrics['top1_accuracy']:.4f}, "
        f"top-3: {metrics['top3_accuracy']:.4f}, "
        f"mean dominant-language ratio: {metrics['mean_dominant_language_ratio']:.4f}"
        r"}"
    )
    print(r"\label{tab:github-skill-eval}")
    print(r"\end{table}")
    print("% --- end LaTeX ---\n")


# ---------------------------------------------------------------------------
# Discover mode (regenerate CANDIDATE_USERS list)
# ---------------------------------------------------------------------------

async def discover_users(token: str | None, per_lang: int = 4) -> None:
    """Query the GitHub Search API and print a fresh CANDIDATE_USERS list."""
    import httpx  # noqa: PLC0415

    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    print("# Auto-generated CANDIDATE_USERS\nCANDIDATE_USERS = [")
    async with httpx.AsyncClient(timeout=20.0) as client:
        for lang in SKILL_LANGUAGE_MAP:
            url = (
                f"{GITHUB_API_BASE}/search/users"
                f"?q=language:{lang}&sort=followers&per_page={per_lang}"
            )
            data = await _get(client, url, headers)
            if data and "items" in data:
                for item in data["items"]:
                    print(f'    {{"username": "{item["login"]}", "sampled_for": "{lang}"}},')
            await asyncio.sleep(1.0)  # respect secondary rate limits
    print("]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    if args.discover:
        await discover_users(args.token)
        return

    users = CANDIDATE_USERS[: args.limit] if args.limit else CANDIDATE_USERS
    use_cache = not args.no_cache

    print(f"[Experiment] Evaluating {len(users)} GitHub users …")

    results: list[dict] = []
    for i, entry in enumerate(users, 1):
        print(f"  [{i:2d}/{len(users)}] {entry['username']} …", end=" ", flush=True)
        r = await evaluate_user(entry, args.token, use_cache)
        status = "✓" if r["match"] else ("!" if r.get("error") else "✗")
        gt = r.get("ground_truth_roadmap_skill") or r.get("error") or "?"
        pred = r.get("predicted_primary_skill") or "?"
        print(f"{status}  gt={gt}  pred={pred}")
        results.append(r)

    metrics = compute_metrics(results)

    write_csv(results)
    write_metrics_json(metrics)
    print_summary(results, metrics)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate GitHub skill extraction accuracy.")
    p.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub personal access token (falls back to $GITHUB_TOKEN). "
             "Strongly recommended — unauthenticated requests are rate-limited to 60/hr.",
    )
    p.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore disk cache and fetch fresh data from the GitHub API.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Evaluate only the first N users (useful for quick smoke tests).",
    )
    p.add_argument(
        "--discover",
        action="store_true",
        help="Run user discovery mode: query GitHub Search API and print a new "
             "CANDIDATE_USERS list to stdout.",
    )
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
