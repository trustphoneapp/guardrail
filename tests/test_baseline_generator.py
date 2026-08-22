from guardrail.synthetic.baseline_generator import generate_baseline


def test_baseline_is_deterministic_for_seed():
    a = generate_baseline("actor-1", seed=7)
    b = generate_baseline("actor-1", seed=7)
    assert a.mcc_distribution == b.mcc_distribution


def test_mcc_distribution_sums_to_one():
    profile = generate_baseline("actor-1")
    assert abs(sum(profile.mcc_distribution.values()) - 1.0) < 1e-9
