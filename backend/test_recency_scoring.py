# Test script for recency boosting
import math
from datetime import datetime, timedelta, date

# Configuration
RECENCY_DECAY_LAMBDA = 0.03

def calculate_recency_score(posted_at):
    """Calculate recency score using exponential decay."""
    if not posted_at:
        return 0.1
    
    today = datetime.now().date()
    days_old = (today - posted_at).days
    
    # Exponential decay
    recency_score = math.exp(-RECENCY_DECAY_LAMBDA * days_old)
    return max(0.0, min(1.0, recency_score))

# Test cases
today = datetime.now().date()
test_cases = [
    ("Today", today),
    ("7 days ago", today - timedelta(days=7)),
    ("30 days ago", today - timedelta(days=30)),
    ("60 days ago", today - timedelta(days=60)),
    ("90 days ago", today - timedelta(days=90)),
]

print("=" * 60)
print("RECENCY SCORING TEST")
print("=" * 60)
print(f"Decay Lambda: {RECENCY_DECAY_LAMBDA}")
print()

for label, date_val in test_cases:
    score = calculate_recency_score(date_val)
    print(f"{label:20} | Recency Score: {score:.4f}")

print()
print("=" * 60)
print("HYBRID SCORING EXAMPLES (60% semantic + 40% recency)")
print("=" * 60)

# Scenario: Old perfect match vs Fresh good match
SEMANTIC_WEIGHT = 0.6
RECENCY_WEIGHT = 0.4

scenarios = [
    ("Perfect match (1.0), today", 1.0, today),
    ("Perfect match (1.0), 60 days", 1.0, today - timedelta(days=60)),
    ("Good match (0.7), today", 0.7, today),
    ("Medium match (0.6), 7 days", 0.6, today - timedelta(days=7)),
]

for label, semantic, posted in scenarios:
    recency = calculate_recency_score(posted)
    hybrid = (semantic * SEMANTIC_WEIGHT) + (recency * RECENCY_WEIGHT)
    print(f"{label:35} | Hybrid: {hybrid:.3f} (S:{semantic:.2f}, R:{recency:.2f})")

print()
print("✅ Fresh jobs get prioritized!")
print("=" * 60)
