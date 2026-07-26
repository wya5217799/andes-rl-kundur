import pytest

from andes_rl_kundur.control.active_power import (
    DroopPIActivePowerController,
    EnergyFeasibleBESSContract,
)


def test_contract_derives_the_frozen_module_aggregate_in_system_units():
    contract = EnergyFeasibleBESSContract(
        system_mva=100.0,
        device_count=4,
        modules_per_device=50,
        module_power_mva=0.72,
        module_energy_mwh=0.56,
        soc_initial=0.50,
        soc_min=0.20,
        soc_max=0.80,
        charge_efficiency=0.9848857802,
        discharge_efficiency=0.9848857802,
        full_scale_ramp_seconds=1.0,
        active_current_lag_seconds=0.02,
        source_ids=("gerini-2022", "wecc-esd-guideline", "andes-2.0.0"),
    )

    assert contract.device_power_mva == pytest.approx(36.0)
    assert contract.device_energy_mwh == pytest.approx(28.0)
    assert contract.device_power_limit_system_pu == pytest.approx(0.36)
    assert contract.device_ramp_limit_system_pu_per_s == pytest.approx(0.36)
    assert contract.initial_discharge_headroom_mwh == pytest.approx(8.4)
    assert contract.initial_charge_headroom_mwh == pytest.approx(8.4)
    assert contract.round_trip_efficiency == pytest.approx(0.97)


def test_contract_fails_closed_without_traceable_sources():
    with pytest.raises(ValueError, match="source_ids"):
        EnergyFeasibleBESSContract(
            system_mva=100.0,
            device_count=4,
            modules_per_device=50,
            module_power_mva=0.72,
            module_energy_mwh=0.56,
            soc_initial=0.50,
            soc_min=0.20,
            soc_max=0.80,
            charge_efficiency=0.9848857802,
            discharge_efficiency=0.9848857802,
            full_scale_ramp_seconds=1.0,
            active_current_lag_seconds=0.02,
            source_ids=(),
        )


def test_contract_rejects_an_initial_soc_outside_operating_bounds():
    with pytest.raises(ValueError, match="soc_min < soc_initial < soc_max"):
        EnergyFeasibleBESSContract(
            system_mva=100.0,
            device_count=4,
            modules_per_device=50,
            module_power_mva=0.72,
            module_energy_mwh=0.56,
            soc_initial=0.90,
            soc_min=0.20,
            soc_max=0.80,
            charge_efficiency=0.9848857802,
            discharge_efficiency=0.9848857802,
            full_scale_ramp_seconds=1.0,
            active_current_lag_seconds=0.02,
            source_ids=("gerini-2022",),
        )


def test_contract_integrates_charge_and_discharge_with_directional_efficiency():
    contract = EnergyFeasibleBESSContract(
        system_mva=100.0,
        device_count=2,
        modules_per_device=50,
        module_power_mva=0.72,
        module_energy_mwh=0.56,
        soc_initial=0.50,
        soc_min=0.20,
        soc_max=0.80,
        charge_efficiency=0.98,
        discharge_efficiency=0.95,
        full_scale_ramp_seconds=1.0,
        active_current_lag_seconds=0.02,
        source_ids=("worked-example",),
    )

    next_soc, charged_mwh, discharged_mwh = contract.integrate_soc(
        actual_power_system_pu=[0.10, -0.10],
        soc=[0.50, 0.50],
        dt_seconds=600.0,
    )

    assert next_soc == pytest.approx([0.4373433584, 0.5583333333])
    assert charged_mwh == pytest.approx([0.0, 1.6333333333])
    assert discharged_mwh == pytest.approx([1.7543859649, 0.0])


def test_power_projection_applies_the_shared_per_device_ramp_contract():
    contract = EnergyFeasibleBESSContract(
        system_mva=100.0,
        device_count=4,
        modules_per_device=50,
        module_power_mva=0.72,
        module_energy_mwh=0.56,
        soc_initial=0.50,
        soc_min=0.20,
        soc_max=0.80,
        charge_efficiency=0.98,
        discharge_efficiency=0.95,
        full_scale_ramp_seconds=1.0,
        active_current_lag_seconds=0.02,
        source_ids=("worked-example",),
    )

    projection = contract.project_power(
        requested_power_system_pu=[1.0, -1.0, 0.05, -0.05],
        previous_power_system_pu=[0.0, 0.0, 0.0, 0.0],
        soc=[0.50, 0.50, 0.50, 0.50],
        voltage_pu=[1.0, 1.0, 1.0, 1.0],
        dt_seconds=0.2,
    )

    assert projection.commanded_power_system_pu == pytest.approx(
        [0.072, -0.072, 0.05, -0.05]
    )
    assert projection.saturation_reasons == (
        ("ramp",),
        ("ramp",),
        (),
        (),
    )


def test_power_projection_blocks_discharge_and_charge_at_soc_limits():
    contract = EnergyFeasibleBESSContract(
        system_mva=100.0,
        device_count=2,
        modules_per_device=50,
        module_power_mva=0.72,
        module_energy_mwh=0.56,
        soc_initial=0.50,
        soc_min=0.20,
        soc_max=0.80,
        charge_efficiency=0.98,
        discharge_efficiency=0.95,
        full_scale_ramp_seconds=1.0,
        active_current_lag_seconds=0.02,
        source_ids=("worked-example",),
    )

    projection = contract.project_power(
        requested_power_system_pu=[0.10, -0.10],
        previous_power_system_pu=[0.0, 0.0],
        soc=[0.20, 0.80],
        voltage_pu=[1.0, 1.0],
        dt_seconds=0.2,
    )

    assert projection.commanded_power_system_pu == pytest.approx([0.0, 0.0])
    assert projection.saturation_reasons == (("ramp", "soc_min"), ("ramp", "soc_max"))


def test_power_projection_enforces_nameplate_and_voltage_dependent_capability():
    contract = EnergyFeasibleBESSContract(
        system_mva=100.0,
        device_count=2,
        modules_per_device=50,
        module_power_mva=0.72,
        module_energy_mwh=0.56,
        soc_initial=0.50,
        soc_min=0.20,
        soc_max=0.80,
        charge_efficiency=0.98,
        discharge_efficiency=0.95,
        full_scale_ramp_seconds=1.0,
        active_current_lag_seconds=0.02,
        source_ids=("worked-example",),
    )

    projection = contract.project_power(
        requested_power_system_pu=[0.50, 0.36],
        previous_power_system_pu=[0.50, 0.36],
        soc=[0.50, 0.50],
        voltage_pu=[1.0, 0.80],
        dt_seconds=0.2,
    )

    assert projection.commanded_power_system_pu == pytest.approx([0.36, 0.288])
    assert projection.saturation_reasons == (("power",), ("capability",))


def test_power_projection_uses_remaining_energy_before_soc_crosses_its_bound():
    contract = EnergyFeasibleBESSContract(
        system_mva=100.0,
        device_count=1,
        modules_per_device=50,
        module_power_mva=0.72,
        module_energy_mwh=0.56,
        soc_initial=0.50,
        soc_min=0.20,
        soc_max=0.80,
        charge_efficiency=0.98,
        discharge_efficiency=0.95,
        full_scale_ramp_seconds=1.0,
        active_current_lag_seconds=0.02,
        source_ids=("worked-example",),
    )

    projection = contract.project_power(
        requested_power_system_pu=[0.10],
        previous_power_system_pu=[0.0],
        soc=[0.200001],
        voltage_pu=[1.0],
        dt_seconds=0.2,
    )

    assert projection.commanded_power_system_pu == pytest.approx([0.004788])
    assert projection.saturation_reasons == (("ramp", "energy"),)


def test_droop_pi_controller_uses_physical_common_frequency_and_resets_state():
    controller = DroopPIActivePowerController(
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz_per_device=2.0,
        ki_system_pu_per_hz_s_per_device=0.2,
    )

    first = controller.act(
        frequencies_hz=[59.9, 59.9, 59.9, 59.9],
        dt_seconds=0.2,
    )
    second = controller.act(
        frequencies_hz=[59.9, 59.9, 59.9, 59.9],
        dt_seconds=0.2,
    )
    controller.reset()
    after_reset = controller.act(
        frequencies_hz=[59.9, 59.9, 59.9, 59.9],
        dt_seconds=0.2,
    )

    assert first == pytest.approx([0.204, 0.204, 0.204, 0.204])
    assert second == pytest.approx([0.208, 0.208, 0.208, 0.208])
    assert after_reset == pytest.approx(first)


def test_droop_pi_controller_freezes_integral_when_projection_saturates_same_direction():
    contract = EnergyFeasibleBESSContract(
        system_mva=100.0,
        device_count=4,
        modules_per_device=50,
        module_power_mva=0.72,
        module_energy_mwh=0.56,
        soc_initial=0.50,
        soc_min=0.20,
        soc_max=0.80,
        charge_efficiency=0.98,
        discharge_efficiency=0.95,
        full_scale_ramp_seconds=1.0,
        active_current_lag_seconds=0.02,
        source_ids=("worked-example",),
    )
    controller = DroopPIActivePowerController(
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz_per_device=2.0,
        ki_system_pu_per_hz_s_per_device=0.2,
    )
    first = controller.act(
        frequencies_hz=[59.9, 59.9, 59.9, 59.9],
        dt_seconds=0.2,
    )
    projection = contract.project_power(
        requested_power_system_pu=first,
        previous_power_system_pu=[0.0, 0.0, 0.0, 0.0],
        soc=[0.50, 0.50, 0.50, 0.50],
        voltage_pu=[1.0, 1.0, 1.0, 1.0],
        dt_seconds=0.2,
    )

    second = controller.act(
        frequencies_hz=[59.9, 59.9, 59.9, 59.9],
        dt_seconds=0.2,
        previous_projection=projection,
    )

    assert second == pytest.approx(first)
