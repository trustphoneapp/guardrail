"""One-time-per-run baseline seed. Production seeds once at enrollment and persists
it; this MVP script re-seeds in-memory on every call since there's no persistence yet."""

from guardrail.config import settings
from guardrail.memory.manager import seed_baseline

if __name__ == "__main__":
    profile = seed_baseline(settings.demo_actor_id)
    print(f"Seeded baseline for {settings.demo_actor_id}: {profile.model_dump()}")
