from __future__ import annotations

import math

import scripts.run_r449_p1_sensitivity as runner


def test_r449_uses_distinct_create_only_output_root() -> None:
    assert runner.ROUND == "R449"
    assert runner.OUT.name == "r449_p1_sensitivity"
    assert runner.FORMAL.name == "formal_analysis.json"


def test_classify_pre_registered_branches() -> None:
    assert runner._classify(-2.68, 3.01, 0.1)[0] == "MIXED"
    assert runner._classify(4.0, 1.0, 0.1)[0] == "CANDIDATE-DOMINANT"
    assert runner._classify(1.0, -4.0, 0.1)[0] == "REFERENCE-DOMINANT"
    assert runner._classify(1.0, 1.0, 0.0)[0] == "CANARY-INVALID"
    assert runner._classify(math.nan, 1.0, 0.1)[0] == "CANARY-INVALID"
