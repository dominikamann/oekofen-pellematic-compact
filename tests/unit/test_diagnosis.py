"""Tests for the diagnosis checks (pure Python, no Home Assistant)."""

import pytest

from custom_components.oekofen_pellematic_compact.diagnosis import (
    BASELINE_LEARN_SECONDS,
    DAY,
    STATUS_CLEANING_DUE,
    STATUS_CLEANING_SOON,
    STATUS_FAULT,
    STATUS_INEFFICIENT,
    STATUS_LEARNING,
    STATUS_MAINTENANCE_DUE,
    STATUS_NOTICE,
    STATUS_OK,
    STATUS_WARNING,
    AmbientHealth,
    CircuitHealth,
    Diagnosis,
    HeaterHealth,
    HeatPumpHealth,
    MessageLog,
    baseline_from_history,
    decode_state,
    is_problem,
    overall_status,
    parse_message,
)
from tests.conftest import load_fixture

STEP = 30  # seconds between polls

START = {"val": 2, "factor": 1}
IGNITION = {"val": 4, "factor": 1}
SOFTSTART = {"val": 8, "factor": 1}
FULL_BURN = {"val": 16, "factor": 1}
SUCTION = {"val": 128, "factor": 1}
OFF = {"val": 2147483648, "factor": 1}
FAULT_STATE = {"val": 2048, "factor": 1}


def _pe(state, fan=41, modulation=100, starts=None, runtime=None):
    pe = {
        "L_state": state,
        "L_fluegas": {"val": fan, "unit": "%", "factor": 1},
        "L_modulation": {"val": modulation, "unit": "%", "factor": 1},
    }
    if starts is not None:
        pe["L_starts"] = {"val": starts, "factor": 1}
        pe["L_runtime"] = {"val": runtime, "unit": "h", "factor": 1}
    return pe


def _burn(heater, seconds, fan, start=0.0, modulation=100):
    """Feed `seconds` of full-load polls; return the next timestamp."""
    t = start
    while t < start + seconds:
        heater.update(_pe(FULL_BURN, fan, modulation), t)
        t += STEP
    return t


def _codes(findings):
    return [f["code"] for f in findings]


# -- decoding -------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ({"val": 16, "factor": 1}, {4}),  # bit mask firmware: Leistungsbrand
        ({"val": 4, "factor": 1}, {2}),  # bit mask: Zündung
        ({"val": 268435472, "factor": 1}, {4, 28}),  # Leistungsbrand + flag
        ({"val": 2048, "factor": 1}, {11}),  # Störung
        ({"val": 4, "format": "0:Dauerlauf|1:Start|2:Zuendung|3:Softstart|4:Leistungsbrand"}, {4}),
        (5, {5}),  # bare value, old firmware: index
        (99, {99}),
        ("2415919104", {28, 31}),  # bare value beyond the index range
        (None, set()),
    ],
)
def test_decode_state(raw, expected):
    assert decode_state(raw) == expected


def test_decode_state_matches_statetext_in_fixtures():
    """Every fixture whose state text says Leistungsbrand decodes to index 4."""
    for name in (
        "api_response_base_da.json",
        "api_response_basic.json",
        "api_response_be72.json",
        "api_response_fren.json",
        "api_response_will.json",
        "api_v352_r49.json",
        "api_response_with_sk_dash.json",
    ):
        pe = load_fixture(name)["pe1"]
        assert "Leistungsbrand" in pe["L_statetext"], name
        assert 4 in decode_state(pe["L_state"]), name


def test_parse_message_from_fixture():
    raw = load_fixture("api_response_base_da.json")["error"]["error_1"]
    assert parse_message(raw) == {
        "time": "2026-01-29T18:21:32",
        "text": "PE 1 Aschebox in Kürze voll Bitte in den nächsten Tagen entleeren",
        "code": 5050,
    }


def test_parse_message_without_code_or_time():
    assert parse_message("") is None
    assert parse_message(None) is None
    assert parse_message("Something odd") == {"time": None, "text": "Something odd", "code": None}


# -- flue-gas fan ---------------------------------------------------------


def test_baseline_is_learned_from_full_load_only():
    heater = HeaterHealth()
    t = _burn(heater, BASELINE_LEARN_SECONDS / 2, fan=41)
    for _ in range(500):  # part load and other states must not count
        heater.update(_pe(FULL_BURN, fan=90, modulation=50), t)
        heater.update(_pe(OFF, fan=90), t + 1)
        t += STEP
    assert heater.baseline is None
    assert heater.learning
    _burn(heater, BASELINE_LEARN_SECONDS / 2 + 10 * STEP, fan=41, start=t)
    assert heater.baseline == pytest.approx(41)
    assert heater.flue_gas_index == pytest.approx(100, abs=0.5)
    assert heater.findings() == []


def test_fouling_raises_cleaning_findings_and_recovers():
    heater = HeaterHealth()
    t = _burn(heater, BASELINE_LEARN_SECONDS + STEP, fan=41)
    for fan in (44, 46, 48):  # fan speed creeps up over weeks of full load
        t = _burn(heater, 12 * 3600, fan, start=t)
    assert _codes(heater.findings()) == ["cleaning_soon"]
    for fan in (55, 60):
        t = _burn(heater, 12 * 3600, fan, start=t)
    assert _codes(heater.findings()) == ["cleaning_due"]
    assert heater.baseline == pytest.approx(41, abs=1.5)  # fouling is not learned
    _burn(heater, 30 * 3600, fan=41, start=t)
    assert heater.findings() == []


def test_maintenance_button_clears_cleaning_warning_at_once():
    heater = HeaterHealth()
    t = _burn(heater, BASELINE_LEARN_SECONDS + STEP, fan=41)
    t = _burn(heater, 48 * 3600, fan=65, start=t)
    assert _codes(heater.findings()) == ["cleaning_due"]
    heater.maintenance_done(t)
    _burn(heater, 10 * STEP, fan=41, start=t)
    assert heater.findings() == []
    assert heater.baseline == pytest.approx(41, abs=1.5)


def _history(fans, modulation=100, start=0.0):
    """Hourly (start, mean) rows for fan and modulation."""
    times = [start + i * 3600 for i in range(len(fans))]
    return list(zip(times, fans)), [(t, modulation) for t in times]


def test_history_baseline_stays_clean_while_fouling():
    # Half a year clean at ~41 %, then weeks of fouling up to 65 %.
    fans = [41 + (i % 5) * 0.3 for i in range(200)] + [45 + i * 0.25 for i in range(80)]
    fan_rows, modulation_rows = _history(fans)
    baseline, recent, hours = baseline_from_history(fan_rows, modulation_rows, fan_rows[-1][0])
    assert hours == 280
    assert baseline == pytest.approx(41.3, abs=0.5)
    assert recent == pytest.approx(64.5, abs=0.5)


def test_history_counts_full_load_hours_only():
    fan_rows, _ = _history([90] * 30 + [41] * 10)
    modulation_rows = [(t, 50 if i < 30 else 100) for i, (t, _) in enumerate(fan_rows)]
    assert baseline_from_history(fan_rows, modulation_rows, fan_rows[-1][0]) is None
    fan_rows, modulation_rows = _history([41] * 25)
    assert baseline_from_history(fan_rows, modulation_rows, fan_rows[-1][0])[0] == pytest.approx(41)


def test_history_recent_only_when_fresh():
    fan_rows, modulation_rows = _history([41] * 25)
    result = baseline_from_history(fan_rows, modulation_rows, fan_rows[-1][0] + 30 * DAY)
    assert result[1] is None


def test_seed_from_history_warns_at_once_on_a_fouled_boiler():
    heater = HeaterHealth()
    t = _burn(heater, 3600, fan=60)  # installed on a fouled boiler: still learning
    assert heater.learning
    assert heater.seed_from_history(41.0, None)
    assert heater.baseline_source == "history" and not heater.learning
    _burn(heater, 3600, fan=60, start=t)
    assert _codes(heater.findings()) == ["cleaning_due"]


def test_seed_from_history_replaces_a_baseline_learned_while_fouling():
    heater = HeaterHealth()
    _burn(heater, BASELINE_LEARN_SECONDS + STEP, fan=50)
    assert heater.baseline == pytest.approx(50)
    assert not heater.seed_from_history(48.5, None)  # within 5 %: keep the learned one
    assert heater.seed_from_history(41.0, None)
    assert heater.baseline == 41.0 and heater.history_checked
    restored = HeaterHealth(heater.as_dict())
    assert restored.baseline_source == "history" and restored.history_checked


def test_baseline_follows_a_cleaner_boiler_faster():
    heater = HeaterHealth()
    t = _burn(heater, BASELINE_LEARN_SECONDS + STEP, fan=50)  # learned while fouled
    _burn(heater, 50 * 3600, fan=41, start=t)  # cleaned, without pressing the button
    assert heater.baseline < 45


# -- ignition -------------------------------------------------------------


def test_ignition_time_and_gaps():
    heater = HeaterHealth()
    heater.update(_pe(OFF), 0)
    heater.update(_pe(IGNITION), 30)
    heater.update(_pe(SOFTSTART), 630)
    assert heater.ignition_last == 10.0
    assert heater.ignition_count == 1
    heater.update(_pe(IGNITION), 1000)  # hours of polling gap: not an ignition time
    heater.update(_pe(FULL_BURN), 1000 + 5 * 3600)
    assert heater.ignition_count == 1


def test_failed_ignitions_warn():
    heater = HeaterHealth()
    t = 0
    for _ in range(3):
        heater.update(_pe(START), t)
        heater.update(_pe(IGNITION), t + 30)
        heater.update(_pe(START), t + 630)  # ignition gave up, no softstart
        t += 3600
    assert heater.failed_ignitions() == 3
    assert heater.ignition_count == 0
    finding = heater.findings()[0]
    assert finding["code"] == "ignition_failures" and finding["status"] == STATUS_WARNING
    # A week later they have aged out.
    heater.update(_pe(OFF), t + 8 * DAY)
    assert heater.findings() == []


def test_suction_during_ignition_is_not_a_failure():
    # Seen on a Pellematic: the hopper refill pauses the ignition, the flame
    # catches during the suction and the boiler goes straight to softstart.
    heater = HeaterHealth()
    heater.update(_pe(OFF), 0)
    heater.update(_pe(IGNITION), 30)
    heater.update(_pe(SUCTION), 240)
    heater.update(_pe(SUCTION), 270)
    heater.update(_pe(SOFTSTART), 360)
    heater.update(_pe(FULL_BURN), 420)
    assert heater.failed_ignitions() == 0
    assert heater.ignition_count == 0  # the time would include the suction


def test_suction_then_new_ignition_is_judged_on_the_new_one():
    heater = HeaterHealth()
    heater.update(_pe(OFF), 0)
    heater.update(_pe(IGNITION), 30)
    heater.update(_pe(SUCTION), 240)
    heater.update(_pe(START), 600)
    heater.update(_pe(IGNITION), 630)
    heater.update(_pe(SOFTSTART), 870)
    assert heater.failed_ignitions() == 0
    assert heater.ignition_last == 4.0
    assert heater.ignition_count == 1


def test_suction_then_giving_up_is_a_failure():
    heater = HeaterHealth()
    heater.update(_pe(OFF), 0)
    heater.update(_pe(IGNITION), 30)
    heater.update(_pe(SUCTION), 240)
    heater.update(_pe(OFF), 420)
    assert heater.failed_ignitions() == 1


def test_suction_then_new_ignition_that_fails_counts_once():
    heater = HeaterHealth()
    heater.update(_pe(IGNITION), 0)
    heater.update(_pe(SUCTION), 210)
    heater.update(_pe(START), 400)
    heater.update(_pe(IGNITION), 430)
    heater.update(_pe(START), 1030)  # second ignition gave up
    assert heater.failed_ignitions() == 1


def test_polling_gap_after_suction_gives_no_verdict():
    heater = HeaterHealth()
    heater.update(_pe(IGNITION), 0)
    heater.update(_pe(SUCTION), 210)
    heater.update(_pe(OFF), 210 + 2 * 3600)
    assert heater.failed_ignitions() == 0


def test_slow_ignition_against_reference():
    heater = HeaterHealth()
    t = 0

    def ignite(minutes):
        nonlocal t
        heater.update(_pe(OFF), t)
        heater.update(_pe(IGNITION), t + 30)
        heater.update(_pe(SOFTSTART), t + 30 + minutes * 60)
        t += 3600

    for _ in range(20):
        ignite(10)
    assert heater.ignition_reference == 10
    for _ in range(20):
        ignite(17)
    assert "ignition_slow" in _codes(heater.findings())
    heater.maintenance_done(t)
    assert heater.ignition_reference is None


# -- cycling --------------------------------------------------------------


def _feed_counters(heater, days, starts_per_day, minutes_per_start):
    starts, runtime_h = 4000, 8000.0
    for hour in range(int(days * 24) + 1):
        heater.update(_pe(OFF, starts=starts, runtime=round(runtime_h)), hour * 3600)
        starts += starts_per_day / 24
        runtime_h += starts_per_day / 24 * minutes_per_start / 60
    return heater


def test_healthy_cycling_has_no_finding():
    heater = _feed_counters(HeaterHealth(), 7, starts_per_day=5, minutes_per_start=100)
    assert heater.starts_per_day == pytest.approx(5, abs=0.3)
    assert heater.runtime_per_start == pytest.approx(100, abs=10)
    assert "short_cycling" not in _codes(heater.findings())


@pytest.mark.parametrize(
    "starts, minutes, status",
    [(12, 70, STATUS_NOTICE), (6, 45, STATUS_NOTICE), (20, 25, STATUS_INEFFICIENT), (17, 70, STATUS_INEFFICIENT)],
)
def test_short_cycling(starts, minutes, status):
    heater = _feed_counters(HeaterHealth(), 7, starts_per_day=starts, minutes_per_start=minutes)
    finding = next(f for f in heater.findings() if f["code"] == "short_cycling")
    assert finding["status"] == status


def test_cycling_needs_two_days():
    heater = _feed_counters(HeaterHealth(), 1, starts_per_day=30, minutes_per_start=10)
    assert heater.starts_per_day is None
    assert heater.findings() == []


# -- maintenance ----------------------------------------------------------


def test_maintenance_due_after_full_load_hours():
    heater = HeaterHealth()
    heater.update(_pe(FULL_BURN, modulation=50), 0)
    heater.full_load_seconds = 1799 * 3600
    _burn(heater, 3600, fan=41, start=STEP)
    assert heater.full_load_hours >= 1800
    assert _codes(heater.findings()) == ["maintenance_due"]
    heater.maintenance_done(10 * 3600)
    assert heater.full_load_hours == 0
    assert heater.findings() == []


def test_maintenance_due_after_a_year():
    heater = HeaterHealth()
    heater.update(_pe(OFF), 0)
    heater.update(_pe(OFF), 366 * DAY)
    assert _codes(heater.findings()) == ["maintenance_due"]


def test_full_load_hours_weight_modulation():
    heater = HeaterHealth()
    _burn(heater, 3600 + STEP, fan=41, modulation=50)
    assert heater.full_load_hours == pytest.approx(0.5, abs=0.02)


# -- heating circuit, outside sensor, heat pump -----------------------------


def _hk(actual, target, pump=1):
    return {
        "L_flowtemp_act": {"val": actual * 10, "factor": 0.1},
        "L_flowtemp_set": {"val": target * 10, "factor": 0.1},
        "L_pump": {"val": pump, "factor": 1},
    }


def test_flow_temperature_low_only_after_hours():
    circuit = CircuitHealth()
    circuit.update(_hk(30, 45), 0)
    circuit.update(_hk(30, 45), 3 * 3600)
    assert circuit.findings() == []
    circuit.update(_hk(30, 45), 4 * 3600)
    assert circuit.findings()[0]["value"] == 15
    circuit.update(_hk(30, 45, pump=0), 5 * 3600)  # pump off: no demand, no finding
    assert circuit.findings() == []


def test_outside_sensor_in_the_sun():
    ambient = AmbientHealth()
    for day in range(3):
        base = day * DAY + 7 * 3600
        ambient.update({"L_ambient": {"val": 50, "factor": 0.1}}, base)
        ambient.update({"L_ambient": {"val": 150, "factor": 0.1}}, base + 2400)  # +10 K in 40 min
    assert ambient.findings()[0]["value"] == 3
    # Normal weather: a sunny spring morning warms by a few kelvin per hour.
    calm = AmbientHealth()
    for minute in range(0, 600, 10):
        calm.update({"L_ambient": {"val": 50 + minute // 3, "factor": 0.1}}, minute * 60)
    assert calm.findings() == []


def test_heat_pump_short_cycling():
    pump = HeatPumpHealth()
    count, t = 1000, 0.0
    for _ in range(3 * 24 * 2):  # 3 days, a 5-minute run every 30 minutes
        pump.update({"L_activation_count": count, "L_compressor_act": 0.5}, t)
        pump.update({"L_activation_count": count, "L_compressor_act": 0.0}, t + 300)
        count += 1
        t += 1800
    finding = pump.findings()[0]
    assert finding["code"] == "heat_pump_short_cycling"
    assert finding["status"] == STATUS_INEFFICIENT
    assert finding["experimental"] is True


def test_heat_pump_fixtures_have_the_keys():
    for name in ("api_response_base_csta.json", "api_response_greenmode.json"):
        wp = load_fixture(name)["wp1"]
        assert "L_activation_count" in wp and "L_compressor_act" in wp


# -- message log, status ----------------------------------------------------


def test_message_log_dedups_and_records_faults():
    log = MessageLog()
    heaters = {"pe1": HeaterHealth()}
    errors = {"error_1": "04-02-2026 16:12:43|PE 1 Pellets Warnung [5054]"}

    new = log.update(errors, heaters, {}, "2026-02-04T16:13:00+01:00")
    assert [m["code"] for m in new] == [5054]
    assert log.findings()[0]["status"] == STATUS_WARNING
    assert log.update(errors, heaters, {}, "later") == []
    assert log.count == 1

    heaters["pe1"].update(_pe(FAULT_STATE), 0)
    new = log.update({}, heaters, {"pe1": "Störung"}, "2026-02-05T08:00:00+01:00")
    assert new[0]["source"] == "pe1" and new[0]["text"] == "Störung"
    assert log.update({}, heaters, {"pe1": "Störung"}, "later") == []
    assert log.count == 2

    restored = MessageLog(log.as_dict())
    assert restored.update(errors, heaters, {"pe1": "Störung"}, "after restart") == []


def test_overall_status_ordering():
    assert overall_status([], learning=False) == STATUS_OK
    assert overall_status([], learning=True) == STATUS_LEARNING
    findings = [{"status": STATUS_NOTICE}, {"status": STATUS_CLEANING_DUE}, {"status": STATUS_MAINTENANCE_DUE}]
    assert overall_status(findings, learning=True) == STATUS_CLEANING_DUE
    assert not is_problem(STATUS_INEFFICIENT)
    assert is_problem(STATUS_CLEANING_SOON)
    assert is_problem(STATUS_FAULT)


def test_diagnosis_on_fixture_reports_changes_once():
    data = load_fixture("api_response_ext_zx.json")
    diagnosis = Diagnosis(language="de")
    messages, changes = diagnosis.update(data, 1000.0, "2026-02-04T16:13:00+01:00")
    assert [m["code"] for m in messages] == [5054]
    assert diagnosis.status == STATUS_WARNING
    finding = diagnosis.findings()[0]
    assert finding["message"] == "Kesselmeldung: PE 1 Pellets Warnung"
    assert [(c["code"], c["active"]) for c in changes] == [("boiler_message", True)]

    _, changes = diagnosis.update(data, 1030.0, "later")
    assert changes == []

    data = dict(data, error={})
    _, changes = diagnosis.update(data, 1060.0, "later")
    assert [(c["code"], c["active"]) for c in changes] == [("boiler_message", False)]

    restored = Diagnosis(diagnosis.as_dict(), "de")
    assert restored.heater("pe1").maintenance_since == diagnosis.heater("pe1").maintenance_since


def test_every_fixture_runs_through_the_diagnosis():
    """No fixture may crash the checks, whatever keys it carries."""
    import glob
    from pathlib import Path

    for path in sorted(glob.glob(str(Path(__file__).parents[1] / "fixtures" / "*.json"))):
        diagnosis = Diagnosis(language="en")
        data = load_fixture(Path(path).name)
        diagnosis.update(data, 0.0, "t0")
        diagnosis.update(data, 30.0, "t1")
        assert diagnosis.status in {
            STATUS_OK, STATUS_LEARNING, STATUS_NOTICE, STATUS_WARNING, STATUS_FAULT, STATUS_CLEANING_SOON
        }, path


def test_figures_are_shown_before_they_are_judged():
    heater = HeaterHealth()
    heater.update(_pe(OFF, starts=4190, runtime=8394), 0)
    # Right after install: lifetime average from the boiler's own counters.
    assert heater.runtime_per_start_display == (120, "lifetime")
    assert heater.starts_per_day_display is None
    heater.update(_pe(OFF, starts=4194, runtime=8402), 0.6 * DAY)
    assert heater.starts_per_day_display == pytest.approx(6.7, abs=0.1)
    assert heater.runtime_per_start_display == (120, "7_days")
    assert heater.starts_per_day is None  # not judged before two days
    assert heater.findings() == []
