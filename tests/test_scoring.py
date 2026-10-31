from training.tinker import spec
from training.tinker.scoring import mcnemar, score_A, wilson


def test_wilson_bounds():
    lo, hi = wilson(95, 100)
    assert 0.88 < lo < 0.95 < hi < 0.99


def test_mcnemar_counts():
    r = mcnemar([True, True, False, False], [True, False, True, True])
    assert r["base_only_correct"] == 1 and r["tuned_only_correct"] == 2


def test_score_A_perfect_and_unsupported_cause():
    p = "On 1 June 2022 the magnetometer CADC0872 showed gaps."
    ex = {"gold": spec.label(p), "passage": p}
    perfect = score_A([ex], [spec.to_lines(ex["gold"])])
    assert perfect["field_exact_match"] == 1.0 and perfect["unsupported_root_causes"] == 0
    bad = dict(ex["gold"]); bad["root_cause"] = "The gaps were caused by cosmic rays."
    r = score_A([ex], [spec.to_lines(bad)])
    assert r["unsupported_root_causes"] == 1 and r["field_exact_match"] < 1.0
