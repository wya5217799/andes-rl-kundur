from __future__ import annotations

import scripts.run_r471_u2_source_factorial as R471


def test_successor_changes_only_registered_terminal_rule() -> None:
    assert not R471.donor_terminal_invalid(
        done=False, tds_failed=False, time_index=5, steps=30
    )
    assert not R471.donor_terminal_invalid(
        done=True, tds_failed=False, time_index=29, steps=30
    )
    assert R471.donor_terminal_invalid(
        done=True, tds_failed=False, time_index=28, steps=30
    )
    assert R471.donor_terminal_invalid(
        done=False, tds_failed=True, time_index=5, steps=30
    )


def test_successor_contract_is_output_isolated_and_factorial_unchanged() -> None:
    contract = R471.build_contract()
    assert contract["round"] == "R471"
    assert "r470" not in contract
    assert contract["r471"]["successor_of"] == "R470"
    assert len(contract["r471"]["arms"]) == 18
    assert contract["r471"]["training_seeds"] == [401, 402, 403, 404, 405, 406]
    assert R471.OUT.name == "r471_u2_source_factorial"
