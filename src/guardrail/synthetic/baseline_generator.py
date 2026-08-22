import random
from datetime import datetime

from guardrail.models import BaselineProfile

MERCHANT_CATEGORIES = ["groceries", "pharmacy", "utilities", "restaurants", "medical", "retail", "insurance"]


def generate_baseline(actor_id: str, seed: int = 42) -> BaselineProfile:
    """Procedural, not learned — disclosed on-screen as synthetic. Deterministic per
    seed so the demo is reproducible. ponytail: add drift-learning only if the demo
    needs to show "adapts over months" — this is honest and sufficient without it."""
    rng = random.Random(seed)
    weights = [rng.uniform(0.5, 1.0) for _ in MERCHANT_CATEGORIES]
    total = sum(weights)
    mcc_distribution = {cat: w / total for cat, w in zip(MERCHANT_CATEGORIES, weights)}
    cadence_hist = {
        "weekday_txn_rate": round(rng.uniform(0.8, 2.5), 2),
        "weekend_txn_rate": round(rng.uniform(0.3, 1.2), 2),
        "median_amount": round(rng.uniform(15, 120), 2),
    }
    seasonal_drift = {"holiday_multiplier": round(rng.uniform(1.1, 1.6), 2)}
    return BaselineProfile(
        actor_id=actor_id,
        mcc_distribution=mcc_distribution,
        cadence_hist=cadence_hist,
        seasonal_drift=seasonal_drift,
        updated_at=datetime.utcnow(),
    )
