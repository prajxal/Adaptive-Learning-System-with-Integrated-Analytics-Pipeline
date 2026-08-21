"""
Large-Scale Learning Progression Simulation

Simulates 1,000 synthetic learners across 20 quiz attempts using the EMA
update from backend/services/skill_profile_service.py:

    C_new = min(1.0, C_old + 0.2)
    P_new = (P_old * C_old + score * 0.8) / (C_old + 0.8)

Learner types:
    Improving  — scores rise linearly from ~50 to ~95 with small noise
    Consistent — scores sampled from N(75, 5)
    Volatile   — scores sampled from N(70, 20)

Usage:
    cd <repo root>
    python -m backend.scripts.simulate_large_learning_progression

Output:
    backend/experiments/large_learning_progression_simulation.csv
    backend/experiments/learning_progression_curve.png
    backend/experiments/proficiency_distribution.png
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — safe on headless environments
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
N_LEARNERS     = 1000
N_ATTEMPTS     = 20
RANDOM_SEED    = 42

# EMA constants (must match skill_profile_service.py)
QUIZ_SIGNAL_WEIGHT       = 0.8
QUIZ_CONFIDENCE_INCREMENT = 0.2
MAX_CONFIDENCE           = 1.0

LEARNER_TYPES = ["Improving", "Consistent", "Volatile"]
# Split 1000 evenly: 334 + 333 + 333
TYPE_COUNTS = {"Improving": 334, "Consistent": 333, "Volatile": 333}

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
OUTPUT_CSV  = EXPERIMENTS_DIR / "large_learning_progression_simulation.csv"
PLOT_CURVE  = EXPERIMENTS_DIR / "learning_progression_curve.png"
PLOT_DIST   = EXPERIMENTS_DIR / "proficiency_distribution.png"

# Colours per type (consistent across both plots)
COLOURS = {"Improving": "#2196F3", "Consistent": "#4CAF50", "Volatile": "#FF5722"}


# ---------------------------------------------------------------------------
# Score generators
# Return (n_learners, N_ATTEMPTS) array of scores in [0, 100]
# ---------------------------------------------------------------------------

def gen_improving(n: int, rng: np.random.Generator) -> np.ndarray:
    """Scores rise linearly from ~50 to ~95 with N(0,5) noise per attempt."""
    base = np.linspace(50, 95, N_ATTEMPTS)           # (N_ATTEMPTS,)
    noise = rng.normal(0, 5, size=(n, N_ATTEMPTS))
    return np.clip(base + noise, 0, 100)


def gen_consistent(n: int, rng: np.random.Generator) -> np.ndarray:
    """Scores sampled from N(75, 5)."""
    return np.clip(rng.normal(75, 5, size=(n, N_ATTEMPTS)), 0, 100)


def gen_volatile(n: int, rng: np.random.Generator) -> np.ndarray:
    """Scores sampled from N(70, 20)."""
    return np.clip(rng.normal(70, 20, size=(n, N_ATTEMPTS)), 0, 100)


# ---------------------------------------------------------------------------
# Vectorised EMA simulation
# ---------------------------------------------------------------------------

def simulate_ema(scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Run the EMA update for all learners in parallel.

    Args:
        scores: (n_learners, N_ATTEMPTS) array of quiz scores

    Returns:
        proficiency : (n_learners, N_ATTEMPTS)
        confidence  : (n_learners, N_ATTEMPTS)
    """
    n = scores.shape[0]
    P = np.zeros(n)
    C = np.zeros(n)

    prof_history = np.empty((n, N_ATTEMPTS))
    conf_history = np.empty((n, N_ATTEMPTS))

    for t in range(N_ATTEMPTS):
        C_old = C.copy()
        C = np.minimum(MAX_CONFIDENCE, C_old + QUIZ_CONFIDENCE_INCREMENT)
        P = (P * C_old + scores[:, t] * QUIZ_SIGNAL_WEIGHT) / (C_old + QUIZ_SIGNAL_WEIGHT)
        prof_history[:, t] = P
        conf_history[:, t] = C

    return prof_history, conf_history


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------

def write_csv(
    all_scores: dict[str, np.ndarray],
    all_prof:   dict[str, np.ndarray],
    all_conf:   dict[str, np.ndarray],
) -> None:
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = ["learner_id", "learner_type", "attempt", "score",
                  "proficiency", "confidence"]
    learner_id = 0
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for ltype in LEARNER_TYPES:
            scores = all_scores[ltype]
            prof   = all_prof[ltype]
            conf   = all_conf[ltype]
            n = scores.shape[0]
            for i in range(n):
                for t in range(N_ATTEMPTS):
                    writer.writerow({
                        "learner_id":   learner_id,
                        "learner_type": ltype,
                        "attempt":      t + 1,
                        "score":        round(float(scores[i, t]), 4),
                        "proficiency":  round(float(prof[i, t]),   4),
                        "confidence":   round(float(conf[i, t]),   4),
                    })
                learner_id += 1


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def print_summary(
    all_scores: dict[str, np.ndarray],
    all_prof:   dict[str, np.ndarray],
) -> None:
    sep = "─" * 65
    print(f"\n{'=' * 65}")
    print("SUMMARY STATISTICS")
    print(f"{'=' * 65}")
    header = f"  {'Type':<12}  {'Mean Score':>10}  {'Final Mean P':>12}  {'Final Var P':>11}"
    print(header)
    print(sep)
    for ltype in LEARNER_TYPES:
        mean_score    = float(all_scores[ltype].mean())
        final_prof    = all_prof[ltype][:, -1]
        final_mean_p  = float(final_prof.mean())
        final_var_p   = float(final_prof.var())
        print(
            f"  {ltype:<12}  {mean_score:>10.2f}  "
            f"{final_mean_p:>12.4f}  {final_var_p:>11.4f}"
        )
    print(f"{'=' * 65}\n")


# ---------------------------------------------------------------------------
# Plot 1 — Average proficiency curve
# ---------------------------------------------------------------------------

def plot_proficiency_curve(all_prof: dict[str, np.ndarray]) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    attempts = np.arange(1, N_ATTEMPTS + 1)

    for ltype in LEARNER_TYPES:
        mean_p = all_prof[ltype].mean(axis=0)
        std_p  = all_prof[ltype].std(axis=0)
        color = COLOURS[ltype]
        ax.plot(attempts, mean_p, label=ltype, color=color, linewidth=2)
        ax.fill_between(attempts, mean_p - std_p, mean_p + std_p,
                        alpha=0.15, color=color)

    ax.set_xlabel("Quiz Attempt", fontsize=12)
    ax.set_ylabel("Mean Proficiency", fontsize=12)
    ax.set_title("Average Proficiency vs Quiz Attempt\n(shaded = ±1 std dev)", fontsize=13)
    ax.legend(fontsize=11)
    ax.set_xlim(1, N_ATTEMPTS)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOT_CURVE, dpi=150)
    plt.close(fig)
    print(f"[OK] Plot saved: {PLOT_CURVE}")


# ---------------------------------------------------------------------------
# Plot 2 — Final proficiency distribution
# ---------------------------------------------------------------------------

def plot_proficiency_distribution(all_prof: dict[str, np.ndarray]) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))

    for ltype in LEARNER_TYPES:
        final_prof = all_prof[ltype][:, -1]
        color = COLOURS[ltype]
        ax.hist(final_prof, bins=40, alpha=0.5, color=color,
                label=f"{ltype} (n={len(final_prof)})", density=True)

    ax.set_xlabel("Final Proficiency (after 20 attempts)", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.set_title("Distribution of Final Proficiency by Learner Type", fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOT_DIST, dpi=150)
    plt.close(fig)
    print(f"[OK] Plot saved: {PLOT_DIST}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(RANDOM_SEED)

    generators = {
        "Improving":  gen_improving,
        "Consistent": gen_consistent,
        "Volatile":   gen_volatile,
    }

    all_scores: dict[str, np.ndarray] = {}
    all_prof:   dict[str, np.ndarray] = {}
    all_conf:   dict[str, np.ndarray] = {}

    print(f"Simulating {N_LEARNERS} learners × {N_ATTEMPTS} attempts ...")
    for ltype in LEARNER_TYPES:
        n = TYPE_COUNTS[ltype]
        scores = generators[ltype](n, rng)
        prof, conf = simulate_ema(scores)
        all_scores[ltype] = scores
        all_prof[ltype]   = prof
        all_conf[ltype]   = conf
        print(f"  {ltype:<12}  {n} learners done.")

    print_summary(all_scores, all_prof)

    print("Writing CSV ...")
    write_csv(all_scores, all_prof, all_conf)
    print(f"[OK] CSV saved: {OUTPUT_CSV}")
    print(f"     {N_LEARNERS * N_ATTEMPTS:,} rows written.\n")

    print("Generating plots ...")
    plot_proficiency_curve(all_prof)
    plot_proficiency_distribution(all_prof)


if __name__ == "__main__":
    main()
