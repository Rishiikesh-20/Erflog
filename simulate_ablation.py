"""
ERFLOG Ablation Study Simulator
================================
Simulates the Recommendation Feasibility Score (RFS) across 5 application
cycles for a Junior User who repeatedly fails mock technical interviews.

Group A (Control -- Full ERFLOG, Feedback Active):
    After each interview failure, Agent 5 feeds structured performance data
    back to Agent 3 (Strategist) and Agent 6 (Learning Guide). Agents 3 and 6
    apply a recalibration algorithm:
        new_RFS = current_RFS + (100 - current_RFS) * learning_rate

Group B (Ablated -- Feedback Disabled):
    The feedback loop is severed. The system ignores interview failures and
    continues recommending based on the static initial resume profile.
    RFS remains stagnant with small market-noise variance (+/- 2%).

Metric: Recommendation Feasibility Score (RFS), 0-100%.
"""

import random

# ----------------------------------------------
# Configuration
# ----------------------------------------------
NUM_CYCLES = 5
INITIAL_RFS = 40.0          # Starting RFS for both groups (%)
LEARNING_RATE = 0.35        # Recalibration rate (Agents 3 + 6 adaptation)
NOISE_RANGE = 2.0           # Market noise amplitude for Group B (+/- %)
SEED = 42                   # Reproducibility

random.seed(SEED)


def simulate_group_a(initial_rfs: float, rate: float, cycles: int) -> list[float]:
    """
    Simulate the control group (Full ERFLOG).

    After each cycle, the feedback loop triggers:
        Agent 5 -> evaluates interview failure
        Agent 3 -> recalibrates recommendation difficulty
        Agent 6 -> injects targeted learning modules

    The recalibration follows:
        RFS_{t+1} = RFS_t + (100 - RFS_t) * learning_rate
    """
    scores = [initial_rfs]
    current = initial_rfs
    for _ in range(1, cycles):
        current = current + (100.0 - current) * rate
        scores.append(round(current, 1))
    return scores


def simulate_group_b(initial_rfs: float, noise: float, cycles: int) -> list[float]:
    """
    Simulate the ablated group (Feedback Disabled).

    No feedback propagation occurs. Agent 3 operates on the stale resume
    profile from Agent 1. RFS fluctuates only due to market noise as
    Agent 2 ingests new job listings each cycle.
    """
    scores = [initial_rfs]
    for _ in range(1, cycles):
        delta = random.uniform(-noise, noise)
        score = initial_rfs + delta
        scores.append(round(score, 1))
    return scores


def print_markdown_table(group_a: list[float], group_b: list[float]) -> None:
    """Print the results as a formatted Markdown table."""
    header = "| Application Cycle | Group A (Full ERFLOG -- Feedback Active) | Group B (Ablated -- Feedback Disabled) | Delta (A - B) |"
    separator = "|:---:|:---:|:---:|:---:|"

    print()
    print("**Table 8.3.** Recommendation Feasibility Score (%) across 5 consecutive")
    print("application cycles for a Junior User experiencing repeated interview failures.")
    print()
    print(header)
    print(separator)

    for i, (a, b) in enumerate(zip(group_a, group_b), start=1):
        delta = round(a - b, 1)
        sign = "+" if delta >= 0 else ""
        print(f"| {i} | {a:.1f}% | {b:.1f}% | {sign}{delta} |")

    print()


def print_summary_statistics(group_a: list[float], group_b: list[float]) -> None:
    """Print key summary statistics for the ablation study."""
    final_delta = round(group_a[-1] - group_b[-1], 1)
    a_improvement = round(group_a[-1] - group_a[0], 1)
    b_improvement = round(group_b[-1] - group_b[0], 1)

    print("### Summary Statistics")
    print()
    print(f"- **Group A total RFS improvement**: {group_a[0]:.1f}% -> {group_a[-1]:.1f}% (Delta = +{a_improvement})")
    print(f"- **Group B total RFS change**:      {group_b[0]:.1f}% -> {group_b[-1]:.1f}% (Delta = {'+' if b_improvement >= 0 else ''}{b_improvement})")
    print(f"- **Final divergence (Cycle 5)**:     +{final_delta} percentage points")
    print(f"- **Learning rate (alpha)**:          {LEARNING_RATE}")
    print(f"- **Market noise (epsilon)**:         +/-{NOISE_RANGE}%")
    print()


# ----------------------------------------------
# Main Execution
# ----------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("  ERFLOG ABLATION STUDY -- Feedback Loop Necessity Simulation")
    print("=" * 70)
    print()
    print(f"Configuration:")
    print(f"  Cycles            = {NUM_CYCLES}")
    print(f"  Initial RFS       = {INITIAL_RFS}%")
    print(f"  Learning Rate     = {LEARNING_RATE}")
    print(f"  Market Noise      = +/-{NOISE_RANGE}%")
    print(f"  Random Seed       = {SEED}")
    print()

    group_a_scores = simulate_group_a(INITIAL_RFS, LEARNING_RATE, NUM_CYCLES)
    group_b_scores = simulate_group_b(INITIAL_RFS, NOISE_RANGE, NUM_CYCLES)

    print_markdown_table(group_a_scores, group_b_scores)
    print_summary_statistics(group_a_scores, group_b_scores)

    print("-" * 70)
    print("  Recalibration Formula (Group A):")
    print("    RFS_{t+1} = RFS_t + (100 - RFS_t) * alpha")
    print()
    print("  Cycle-by-cycle derivation:")
    rfs = INITIAL_RFS
    for i in range(1, NUM_CYCLES + 1):
        if i == 1:
            print(f"    Cycle {i}: RFS = {rfs:.1f}%  (initial)")
        else:
            prev = rfs
            rfs = rfs + (100.0 - rfs) * LEARNING_RATE
            print(f"    Cycle {i}: RFS = {rfs:.1f}%  <- {prev:.1f} + (100 - {prev:.1f}) * {LEARNING_RATE}")
    print("-" * 70)
