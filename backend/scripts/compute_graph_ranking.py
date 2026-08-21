"""
Graph Ranking Script — Compute importance scores for all courses.

Usage:
    cd <repo root>
    python -m backend.scripts.compute_graph_ranking

or (from backend/ with services on PYTHONPATH):
    cd backend
    python scripts/compute_graph_ranking.py

Formula (mirrors learning_priority_service.compute_importance_score):
    importance_score = (descendants_count * 3) + (out_degree * 2) + (10 - graph_depth)

Output:
    • Sorted ranking table printed to stdout
    • backend/experiments/graph_ranking_results.csv
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict, deque
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — mirrors pattern used in compute_difficulty.py
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
OUTPUT_CSV = BACKEND_DIR / "experiments" / "graph_ranking_results.csv"

sys.path.append(str(BACKEND_DIR))

from db.database import SessionLocal  # noqa: E402
from models.course import Course  # noqa: E402
from models.course_prerequisite import CoursePrerequisite  # noqa: E402


# ---------------------------------------------------------------------------
# In-memory graph metric helpers
# ---------------------------------------------------------------------------

def _build_maps(
    edges: list[CoursePrerequisite],
    course_ids: list[str],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return (forward_map, prereq_map) built from prerequisite edges.

    forward_map : prerequisite_id -> set of course_ids that depend on it
    prereq_map  : course_id       -> set of prerequisite_ids it needs
    """
    forward_map: dict[str, set[str]] = defaultdict(set)
    prereq_map: dict[str, set[str]] = defaultdict(set)

    for edge in edges:
        forward_map[edge.prerequisite_id].add(edge.course_id)
        prereq_map[edge.course_id].add(edge.prerequisite_id)

    return forward_map, prereq_map


def _count_descendants(cid: str, forward_map: dict[str, set[str]]) -> int:
    """BFS to count all downstream reachable nodes from cid."""
    visited: set[str] = set()
    queue = [cid]
    while queue:
        current = queue.pop(0)
        for dep in forward_map.get(current, set()):
            if dep not in visited:
                visited.add(dep)
                queue.append(dep)
    return len(visited)


def _compute_all_depths(
    all_ids: list[str],
    prereq_map: dict[str, set[str]],
) -> dict[str, int]:
    """Compute longest-path depth for every node via Kahn's topological sort.

    Cycles in the data are handled gracefully: nodes in a cycle are never
    enqueued and retain depth 0 (same treatment as roots).
    """
    # in-degree = number of prerequisites each node has
    in_degree: dict[str, int] = {cid: len(prereq_map.get(cid, set())) for cid in all_ids}
    depth: dict[str, int] = {cid: 0 for cid in all_ids}

    # forward_from_prereq: prereq_id -> set of nodes that depend on it
    # (we need to propagate depth updates forward)
    forward_from_prereq: dict[str, set[str]] = defaultdict(set)
    for cid, prereqs in prereq_map.items():
        for p in prereqs:
            forward_from_prereq[p].add(cid)

    queue: deque[str] = deque(cid for cid in all_ids if in_degree[cid] == 0)

    while queue:
        node = queue.popleft()
        node_depth = depth[node]
        for dependent in forward_from_prereq.get(node, set()):
            candidate = node_depth + 1
            if candidate > depth[dependent]:
                depth[dependent] = candidate
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    return depth


def _importance_score(descendants: int, out_degree: int, depth: int) -> float:
    """Formula from learning_priority_service.compute_importance_score."""
    return float((descendants * 3) + (out_degree * 2) + (10 - depth))


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------

def _sep(char: str = "─", width: int = 90) -> str:
    return char * width


def _print_table(rows: list[dict]) -> None:
    header = f"{'Rank':>4}  {'Course Name':<45}  {'Desc':>5}  {'OutDeg':>6}  {'Depth':>5}  {'Score':>7}"
    print(_sep("=", 90))
    print("COURSE GRAPH RANKING  (sorted by importance score, descending)")
    print(_sep("=", 90))
    print(header)
    print(_sep("─", 90))
    for r in rows:
        print(
            f"{r['rank']:>4}  "
            f"{r['course_name']:<45}  "
            f"{r['descendants_count']:>5}  "
            f"{r['out_degree']:>6}  "
            f"{r['graph_depth']:>5}  "
            f"{r['importance_score']:>7.1f}"
        )
    print(_sep("=", 90))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    db = SessionLocal()
    try:
        # Q1 — all courses
        courses: list[Course] = db.query(Course).all()
        if not courses:
            print("[ERROR] No courses found in the database.")
            sys.exit(1)

        course_ids = [c.id for c in courses]
        course_map = {c.id: c for c in courses}

        # Q2 — all prerequisite edges
        edges: list[CoursePrerequisite] = db.query(CoursePrerequisite).all()

    finally:
        db.close()

    print(f"Loaded {len(courses)} courses and {len(edges)} prerequisite edges.")

    # Build in-memory maps
    forward_map, prereq_map = _build_maps(edges, course_ids)

    # Compute depth for all courses in one pass (handles cycles safely)
    all_depths = _compute_all_depths(course_ids, prereq_map)

    # Compute remaining metrics per course
    results = []

    for cid in course_ids:
        course = course_map[cid]
        out_degree = len(forward_map.get(cid, set()))
        descendants = _count_descendants(cid, forward_map)
        depth = all_depths[cid]
        score = _importance_score(descendants, out_degree, depth)

        results.append({
            "course_id": cid,
            "course_name": course.title,
            "descendants_count": descendants,
            "out_degree": out_degree,
            "graph_depth": depth,
            "importance_score": score,
        })

    # Sort descending by importance_score, then stable by course_id
    results.sort(key=lambda r: (-r["importance_score"], r["course_id"]))

    # Assign ranks
    for i, row in enumerate(results, 1):
        row["rank"] = i

    # Print table
    _print_table(results)

    # Save CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "course_name",
        "descendants_count",
        "out_degree",
        "graph_depth",
        "importance_score",
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[OK] Results saved to {OUTPUT_CSV}")
    print(f"     {len(results)} courses ranked.\n")


if __name__ == "__main__":
    main()
