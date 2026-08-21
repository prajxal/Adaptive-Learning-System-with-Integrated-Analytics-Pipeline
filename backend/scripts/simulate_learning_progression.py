"""
Learning Progression Simulator

Simulates the EMA-based skill update from:
    backend/services/skill_profile_service.py :: update_skill_profile_from_quiz

Formulas (no cold-start data, so cold_weight == 0):
    C_new = min(1.0, C_old + 0.2)
    P_new = (P_old * C_old + score * 0.8) / (C_old + 0.8)

Usage:
    cd <repo root>
    python -m backend.scripts.simulate_learning_progression

or:
    cd backend
    python scripts/simulate_learning_progression.py

Output:
    • Per-learner table printed to stdout
    • backend/experiments/learning_progression_simulation.csv
"""

from __future__ import annotations

import csv
from pathlib import Path

# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = SCRIPT_DIR.parent / "experiments" / "learning_progression_simulation.csv"

# ---------------------------------------------------------------------------
# Learner profiles
# ---------------------------------------------------------------------------
LEARNERS: dict[str, list[int]] = {
    "Improving":  [60, 70, 80, 90, 95],
    "Consistent": [75, 76, 74, 77, 75],
    "Volatile":   [90, 40, 85, 50, 80],
}

QUIZ_SIGNAL_WEIGHT = 0.8
QUIZ_CONFIDENCE_INCREMENT = 0.2
MAX_CONFIDENCE = 1.0


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def simulate(scores: list[int]) -> list[dict]:
    """Apply the EMA update loop and return one row per attempt."""
    P = 0.0  # quiz_proficiency
    C = 0.0  # quiz_confidence
    rows = []
    for attempt, score in enumerate(scores, 1):
        # Capture old values before update (proficiency formula uses C_old)
        P_old, C_old = P, C

        C = min(MAX_CONFIDENCE, C_old + QUIZ_CONFIDENCE_INCREMENT)
        P = (P_old * C_old + score * QUIZ_SIGNAL_WEIGHT) / (C_old + QUIZ_SIGNAL_WEIGHT)

        rows.append({
            "attempt": attempt,
            "score": score,
            "proficiency": round(P, 4),
            "confidence": round(C, 4),
        })
    return rows


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------

def _sep(char: str = "─", width: int = 60) -> str:
    return char * width


def _print_learner(name: str, rows: list[dict]) -> None:
    print(f"\n{_sep('=', 60)}")
    print(f"  Learner: {name}")
    print(_sep("=", 60))
    header = f"  {'Attempt':>7}  {'Score':>6}  {'Proficiency':>12}  {'Confidence':>11}"
    print(header)
    print(_sep("─", 60))
    for r in rows:
        print(
            f"  {r['attempt']:>7}  {r['score']:>6}  "
            f"{r['proficiency']:>12.4f}  {r['confidence']:>11.4f}"
        )
    final = rows[-1]
    print(_sep("─", 60))
    print(
        f"  Final → proficiency={final['proficiency']:.4f}  "
        f"confidence={final['confidence']:.4f}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    all_rows: list[dict] = []

    for name, scores in LEARNERS.items():
        rows = simulate(scores)
        _print_learner(name, rows)
        for r in rows:
            all_rows.append({"learner": name, **r})

    # Save CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["learner", "attempt", "score", "proficiency", "confidence"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n{_sep('=', 60)}")
    print(f"[OK] Results saved to {OUTPUT_CSV}\n")


if __name__ == "__main__":
    main()
