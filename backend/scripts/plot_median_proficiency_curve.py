"""
Median Proficiency Curve — Publication-Quality Plot

Loads backend/experiments/large_learning_progression_simulation.csv and
produces a clean figure showing median proficiency progression across 20
quiz attempts for each learner type.

For Improving learners only, a dashed overlay shows the median quiz score
trend, illustrating how the EMA estimate tracks (and lags behind) the
rising score signal.

Usage:
    cd <repo root>
    python -m backend.scripts.plot_median_proficiency_curve

Output:
    backend/experiments/learning_progression_median_curve.png  (300 dpi)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
INPUT_CSV  = EXPERIMENTS_DIR / "large_learning_progression_simulation.csv"
OUTPUT_PNG = EXPERIMENTS_DIR / "learning_progression_median_curve.png"

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
LEARNER_TYPES = ["Improving", "Consistent", "Volatile"]

COLORS = {
    "Improving":  "#1f77b4",   # matplotlib blue
    "Consistent": "#2ca02c",   # matplotlib green
    "Volatile":   "#d62728",   # matplotlib red
}

LINE_WIDTH  = 2.5
SCORE_ALPHA = 0.75   # slightly softer for the secondary dashed line


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"CSV not found: {INPUT_CSV}\n"
            "Run simulate_large_learning_progression.py first."
        )

    # ---- 1. Load & aggregate ------------------------------------------------
    df = pd.read_csv(INPUT_CSV)

    medians = (
        df.groupby(["learner_type", "attempt"])[["proficiency", "score"]]
        .median()
        .reset_index()
    )

    # ---- 2. Build figure ----------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))

    # Solid lines — median proficiency per learner type
    for ltype in LEARNER_TYPES:
        subset = medians[medians["learner_type"] == ltype].sort_values("attempt")
        ax.plot(
            subset["attempt"],
            subset["proficiency"],
            label=f"{ltype}",
            color=COLORS[ltype],
            linewidth=LINE_WIDTH,
            zorder=3,
        )

    # Dashed overlay — median quiz score for Improving learners only
    improving = medians[medians["learner_type"] == "Improving"].sort_values("attempt")
    ax.plot(
        improving["attempt"],
        improving["score"],
        label="Improving — quiz score (median)",
        color=COLORS["Improving"],
        linewidth=LINE_WIDTH,
        linestyle="--",
        alpha=SCORE_ALPHA,
        zorder=2,
    )

    # ---- 3. Axes, labels, styling -------------------------------------------
    ax.set_xlabel("Quiz Attempt", fontsize=12, labelpad=6)
    ax.set_ylabel("Median Proficiency", fontsize=12, labelpad=6)
    ax.set_title(
        "Median Proficiency Progression Across Quiz Attempts",
        fontsize=13,
        pad=10,
    )

    ax.set_xlim(1, 20)
    ax.set_xticks(range(1, 21))
    ax.grid(True, alpha=0.35, linestyle="--", linewidth=0.7)

    # Remove top and right spines for a cleaner look
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(fontsize=10, framealpha=0.9, loc="upper left")

    fig.tight_layout()

    # ---- 4. Save ------------------------------------------------------------
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"[OK] Figure saved: {OUTPUT_PNG}")
    print(f"     Size: {OUTPUT_PNG.stat().st_size / 1024:.1f} KB  |  dpi=300")


if __name__ == "__main__":
    main()
