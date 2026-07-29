from scripts.run_r279_formal import PRIMARY_ENDPOINTS, _classification


def _hier(point: float, upper: float):
    return {
        endpoint: {
            "ratio_of_means_percent": {
                "point": point,
                "percentile_95_interval": [point - 1.0, upper],
            }
        }
        for endpoint in PRIMARY_ENDPOINTS
    }


def _paired(point: float, upper: float):
    return {
        "endpoints": {
            endpoint: {
                "ratio_of_means_percent": {
                    "point": point,
                    "percentile_95_interval": [point - 1.0, upper],
                }
            }
            for endpoint in PRIMARY_ENDPOINTS
        }
    }


def _seed_counts(causal: int = 3, centralized: int = 3):
    return {
        "shared_vs_causal": {"both_endpoint_improvement_count": causal},
        "shared_vs_centralized": {
            "both_endpoint_improvement_count": centralized
        },
    }


def test_classification_identifies_unique_shared_value():
    result = _classification(
        valid=True,
        causal_vs_q0=_paired(-3.0, -0.1),
        hierarchical={
            "shared_vs_q0": _hier(-5.0, -1.0),
            "shared_vs_causal": _hier(-3.0, -0.2),
            "shared_vs_centralized": _hier(-4.0, -0.4),
            "centralized_vs_q0": _hier(-2.5, -0.1),
        },
        seed_effects=_seed_counts(),
    )
    assert result["classification"] == "MARL-IDENTIFIABLE-POSITIVE"


def test_classification_prioritizes_causal_explanation():
    result = _classification(
        valid=True,
        causal_vs_q0=_paired(-4.0, -0.2),
        hierarchical={
            "shared_vs_q0": _hier(-4.0, -0.2),
            "shared_vs_causal": _hier(-1.0, 0.5),
            "shared_vs_centralized": _hier(-3.0, -0.1),
            "centralized_vs_q0": _hier(-3.0, -0.1),
        },
        seed_effects=_seed_counts(),
    )
    assert result["classification"] == "CAUSAL-EXPLANATION-SUFFICIENT"


def test_classification_retains_nonunique_learned_branch():
    result = _classification(
        valid=True,
        causal_vs_q0=_paired(-1.0, 0.5),
        hierarchical={
            "shared_vs_q0": _hier(-4.0, -0.2),
            "shared_vs_causal": _hier(-3.0, -0.1),
            "shared_vs_centralized": _hier(-1.0, 0.5),
            "centralized_vs_q0": _hier(-1.0, 0.5),
        },
        seed_effects=_seed_counts(),
    )
    assert result["classification"] == "LEARNED-VALUE-NOT-MARL-IDENTIFIABLE"


def test_classification_invalid_guard_has_highest_priority():
    result = _classification(
        valid=False,
        causal_vs_q0={},
        hierarchical={},
        seed_effects={},
    )
    assert result["classification"] == "INVALID"
