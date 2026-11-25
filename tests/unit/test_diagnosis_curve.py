"""Tests for the heating-curve analysis of the diagnosis (pure Python)."""

import csv
import glob
import re
from pathlib import Path

import pytest

from custom_components.oekofen_pellematic_compact.diagnosis import (
    CURVE_DETERMINED,
    CURVE_LEARNING,
    CURVE_UNDETERMINABLE,
    CurveHealth,
    Diagnosis,
    has_curve_inputs,
    seed_curve_from_history,
    source_temperature,
)
from tests.conftest import load_fixture

FIXTURES = Path(__file__).parents[1] / "fixtures"
HOUR = 3600.0


def _flow_set(ambient, room_set, slope=1.0, offset=10.0, flow_max=None, flow_min=None):
    value = room_set + offset + slope * (room_set - ambient)
    if flow_max is not None:
        value = min(value, flow_max)
    if flow_min is not None:
        value = max(value, flow_min)
    return value


def _feed(curve, ambients, hours_each=6, room_set=21.0, surplus=0.0, source_above=None, pump=True, **shape):
    """Hourly samples for each outdoor temperature; the flow sits `surplus` above its set point."""
    for ambient in ambients:
        flow_set = _flow_set(ambient, room_set, **shape)
        source = None if source_above is None else flow_set + source_above
        for _ in range(hours_each):
            curve.add_sample(HOUR, ambient, room_set, flow_set, flow_set + surplus, source, pump)


WINTER = [-8, -6, -4, -2, 0, 2, 4, 6, 8, 10, 12, 14]


# --- curve ---------------------------------------------------------------


def test_curve_is_recovered_from_the_set_points():
    curve = CurveHealth()
    _feed(curve, WINTER, room_set=21.0)
    _feed(curve, WINTER, room_set=17.0)

    assert curve.curve_status == CURVE_DETERMINED
    assert curve.slope == pytest.approx(1.0, abs=0.01)
    assert curve.offset == pytest.approx(10.0, abs=0.1)
    assert curve.scatter == pytest.approx(0.0, abs=0.05)
    assert curve.flow_at(0) == pytest.approx(17 + 10 + 17, abs=0.3)  # for the last room set seen
    low, high = curve.outdoor_range
    assert low <= -6 and high >= 12


def test_other_slopes_and_offsets_are_recovered_too():
    curve = CurveHealth()
    _feed(curve, WINTER, slope=0.6, offset=4.0)
    assert (curve.slope, curve.offset) == (pytest.approx(0.6, abs=0.01), pytest.approx(4.0, abs=0.2))


def test_curve_keeps_learning_without_enough_data():
    short = CurveHealth()
    _feed(short, WINTER, hours_each=1)  # 12 h in total
    assert short.curve_status == CURVE_LEARNING
    assert short.slope is None and short.offset is None and short.flow_at(0) is None

    narrow = CurveHealth()
    _feed(narrow, [4, 5, 6, 7], hours_each=12)  # 48 h, but only 3 K of weather
    assert narrow.curve_status == CURVE_LEARNING

    few_bins = CurveHealth()
    _feed(few_bins, [-8, 0, 8], hours_each=12)  # wide, but three points only
    assert few_bins.curve_status == CURVE_LEARNING


@pytest.mark.parametrize(
    "shape",
    [{"flow_max": 50.0}, {"flow_min": 45.0}, {"flow_max": 45.0, "flow_min": 45.0}],
    ids=["clipped at max", "clipped at min", "constant"],
)
def test_clipped_curve_is_not_reported(shape):
    curve = CurveHealth()
    _feed(curve, WINTER, **shape)
    assert curve.curve_status == CURVE_UNDETERMINABLE
    assert curve.slope is None


@pytest.mark.parametrize("shape", [{"flow_max": 58.0}, {"flow_min": 40.0}], ids=["max", "min"])
def test_a_curve_cut_off_only_at_the_edge_is_not_reported_either(shape):
    """Two of twelve weather classes clipped: the slope would read 4 % low."""
    curve = CurveHealth()
    _feed(curve, WINTER, **shape)
    assert curve.curve_status == CURVE_UNDETERMINABLE


def test_a_limit_outside_the_weather_seen_does_not_disturb():
    curve = CurveHealth()
    _feed(curve, WINTER, flow_max=60.0, flow_min=38.0)
    assert curve.curve_status == CURVE_DETERMINED
    assert curve.slope == pytest.approx(1.0, abs=0.01)


def test_samples_outside_heating_are_ignored():
    curve = CurveHealth()
    _feed(curve, WINTER, room_set=12.0)  # frost protection level
    assert curve.heating_hours == 0
    for pump in (False, 0, "false", "0", {"val": "false"}, {"val": 0}):
        assert curve.add_sample(HOUR, 0, 21, 52, 52, None, pump) is False
    assert curve.add_sample(HOUR, 0, 21, 18, 18, None, True) is False  # flow set below 20
    assert curve.add_sample(HOUR, 30, 24, 22, 22, None, True) is False  # cooling: flow set below room set
    assert curve.add_sample(HOUR, None, 21, 52, 52, None, True) is False
    assert curve.heating_hours == 0


@pytest.mark.parametrize(
    "pump", [True, 1, "1", "true", "True", {"val": "true"}, {"val": 1}, {"val": "1"}, None, -32768, {"val": 32767}]
)
def test_every_pump_shape_of_the_api_counts(pump):
    curve = CurveHealth()
    assert curve.add_sample(HOUR, 0, 21, 52, 52, None, pump) is True


def test_a_changed_curve_takes_over():
    curve = CurveHealth()
    _feed(curve, WINTER, hours_each=30)
    for _ in range(7):  # six weeks of heating with a steeper curve
        _feed(curve, WINTER, hours_each=12, slope=1.4)
    assert curve.curve_status == CURVE_DETERMINED
    assert curve.slope == pytest.approx(1.4, abs=0.05)


def test_update_reads_the_api_shape_and_weights_by_time():
    def hk(flow_set, pump="true"):
        return {
            "L_flowtemp_set": {"val": str(int(flow_set * 10)), "factor": 0.1},
            "L_flowtemp_act": {"val": str(int(flow_set * 10) + 50), "factor": 0.1},
            "L_roomtemp_set": {"val": "210", "factor": 0.1},
            "L_pump": {"val": pump},
        }

    curve = CurveHealth()
    curve.update(hk(52), 0.0, None, 0.0)
    assert curve.heating_hours == 0  # first poll has no duration yet
    curve.update(hk(52), 0.0, None, 30.0)
    assert curve.heating_hours == pytest.approx(30 / 3600)
    curve.update(hk(52), 0.0, None, 30.0 + 7200)  # a polling gap is capped
    assert curve.heating_hours == pytest.approx(330 / 3600, rel=0.01)


def test_state_survives_a_restart():
    curve = CurveHealth()
    _feed(curve, WINTER, surplus=6.0, source_above=10.0)
    curve.history_checked = True
    restored = CurveHealth(curve.as_dict())
    assert restored.curve_status == CURVE_DETERMINED
    assert restored.slope == pytest.approx(curve.slope)
    assert restored.circuit_type == curve.circuit_type == "unmixed"
    assert restored.flow_surplus == pytest.approx(curve.flow_surplus)
    assert restored.history_checked is True
    assert restored.flow_at(0) == pytest.approx(curve.flow_at(0))


# --- circuit type and surplus ---------------------------------------------


def test_flow_following_a_hot_source_is_unmixed():
    curve = CurveHealth()
    _feed(curve, [0, 2], hours_each=6, surplus=9.0, source_above=10.0)  # 12 hot hours
    assert curve.circuit_type == "unknown"
    _feed(curve, [0, 2], hours_each=7, surplus=9.0, source_above=10.0)  # the hours fade, so a few more
    assert curve.circuit_type == "unmixed"
    assert curve.circuit_type_source == "learned"
    assert curve.hot_source_hours == pytest.approx(25, abs=1)
    assert curve.surplus_with_hot_source == pytest.approx(9.0, abs=0.1)


def test_flow_held_at_its_set_point_below_a_hot_source_is_mixed():
    curve = CurveHealth()
    _feed(curve, WINTER, surplus=0.5, source_above=15.0)
    assert curve.circuit_type == "mixed"


def test_circuit_type_stays_unknown_when_the_evidence_is_unclear():
    between = CurveHealth()
    _feed(between, WINTER, surplus=3.5, source_above=15.0)
    assert between.circuit_type == "unknown"

    never_hot = CurveHealth()
    _feed(never_hot, WINTER, surplus=1.0, source_above=3.0)  # source close to the set point
    assert never_hot.circuit_type == "unknown"
    assert never_hot.hot_source_hours == 0

    no_source = CurveHealth()
    _feed(no_source, WINTER, surplus=6.0)
    assert no_source.circuit_type == "unknown"
    assert no_source.circuit_type_source is None


def test_flow_far_below_its_set_point_is_not_a_mixer():
    """A stopped pump or a fault under a hot buffer must not read as "mixed"."""
    curve = CurveHealth()
    _feed(curve, WINTER, surplus=-12.0, source_above=10.0)
    assert curve.circuit_type == "unknown"


def test_configuration_values_follow_the_response():
    curve = CurveHealth()
    hk = {
        "L_flowtemp_set": {"val": 520, "factor": 0.1},
        "L_flowtemp_act": {"val": 520, "factor": 0.1},
        "L_roomtemp_set": {"val": 210, "factor": 0.1},
        "L_cfg_mixer": {"val": "1", "format": "0:direkt|1:gemischt"},
        "L_cfg_curve_slope": {"val": "12", "factor": "0.1"},
    }
    curve.update(hk, 0.0, None, 0.0)
    assert (curve.circuit_type, curve.configured_slope) == ("mixed", pytest.approx(1.2))
    del hk["L_cfg_mixer"], hk["L_cfg_curve_slope"]
    curve.update(hk, 0.0, None, 30.0)
    assert (curve.circuit_type, curve.circuit_type_source, curve.configured_slope) == ("unknown", None, None)


@pytest.mark.parametrize(("raw", "expected"), [(1, "mixed"), (0, "unmixed")])
def test_configured_mixer_decides_at_once(raw, expected):
    curve = CurveHealth()
    hk = {
        "L_flowtemp_set": {"val": 520, "factor": 0.1},
        "L_flowtemp_act": {"val": 600, "factor": 0.1},
        "L_roomtemp_set": {"val": 210, "factor": 0.1},
        "L_pump": {"val": 1},
        "L_cfg_mixer": {"val": raw, "format": "0:direkt|1:gemischt"},
        "L_cfg_curve_slope": {"val": 12, "factor": 0.1},
    }
    curve.update(hk, 0.0, 70.0, 0.0)
    assert (curve.circuit_type, curve.circuit_type_source) == (expected, "config")
    assert curve.configured_slope == pytest.approx(1.2)


def test_flow_surplus_needs_a_day_of_heating():
    curve = CurveHealth()
    _feed(curve, [0], hours_each=23, surplus=5.2)
    assert curve.flow_surplus is None
    _feed(curve, [0], hours_each=2, surplus=5.2)
    assert curve.flow_surplus == pytest.approx(5.2, abs=0.05)


def _temp(value):
    return {"val": str(int(value * 10)), "factor": 0.1, "unit": "°C"}


def test_source_is_the_coolest_buffer_when_there_is_one():
    data = {
        "pu1": {"L_tpo_act": _temp(50)},
        "pu2": {"L_tpo_act": _temp(62)},
        "pe1": {"L_temp_act": _temp(75)},
        "wp1": {"L_temp_flow_is": _temp(40)},
    }
    assert source_temperature(data) == pytest.approx(50)
    assert source_temperature({"pu1": {"L_tpo_act": _temp(50)}, "pe1": {"L_temp_act": _temp(75)}}) == pytest.approx(50)


def test_source_without_a_buffer_is_the_coolest_generator():
    assert source_temperature({"pe1": {"L_temp_act": _temp(70)}}) == pytest.approx(70)
    assert source_temperature(
        {"pe1": {"L_temp_act": _temp(70)}, "wp1": {"L_temp_flow_is": _temp(38)}}
    ) == pytest.approx(38)
    assert source_temperature({"hk1": {}, "system": {}}) is None


def test_source_ignores_bare_values_and_a_buffer_without_reading():
    assert source_temperature({"pu1": {"L_tpo_act": 713}, "pe1": {"L_temp_act": _temp(70)}}) is None
    assert source_temperature({"pe1": {"L_temp_act": 650}}) is None


# --- wiring into Diagnosis -------------------------------------------------


def _has_metadata_everywhere(data):
    ambient = (data.get("system") or {}).get("L_ambient")
    return isinstance(ambient, dict)


def test_every_fixture_runs_and_bare_value_firmware_learns_nothing():
    bare = []
    for path in sorted(glob.glob(str(FIXTURES / "*.json"))):
        data = load_fixture(Path(path).name)
        diagnosis = Diagnosis(language="en")
        diagnosis.update(data, 0.0, "t0")
        diagnosis.update(data, 30.0, "t1")
        Diagnosis(diagnosis.as_dict(), "en")  # what was stored loads again
        if not _has_metadata_everywhere(data):
            bare.append(Path(path).name)
            assert diagnosis.curves == {}, path
        else:
            circuits = {name for name in data if re.fullmatch(r"hk\d+", name)}
            assert set(diagnosis.curves) == circuits, path  # every circuit of modern firmware is followed
    assert "api_response_base_srqu.json" in bare and "api_response_green_kn.json" in bare


def test_fixture_with_configuration_values():
    data = load_fixture("api_response_v402b_jsonprops.json")
    diagnosis = Diagnosis(language="en")
    diagnosis.update(data, 0.0, "t0")
    curve = diagnosis.curves["hk1"]
    assert (curve.circuit_type, curve.circuit_type_source) == ("mixed", "config")
    assert curve.configured_slope == pytest.approx(1.0)


def test_component_order_in_the_response_does_not_matter():
    data = load_fixture("api_response_ext_zx.json")
    assert has_curve_inputs(data["hk1"], data["system"])
    reordered = {key: data[key] for key in reversed(list(data))}
    first, second = Diagnosis(language="en"), Diagnosis(language="en")
    for now in (0.0, 30.0, 60.0):
        first.update(data, now, "t")
        second.update(reordered, now, "t")
    assert first.as_dict()["curves"] == second.as_dict()["curves"]
    assert first.curves["hk1"].heating_hours > 0


def test_stored_state_from_before_the_feature_loads():
    old = Diagnosis(language="en").as_dict()
    del old["curves"]
    assert Diagnosis(old, "en").curves == {}


def test_curve_inputs_need_metadata():
    hk = {"L_flowtemp_set": _temp(50), "L_flowtemp_act": _temp(50), "L_roomtemp_set": _temp(21)}
    system = {"L_ambient": _temp(3)}
    assert has_curve_inputs(hk, system)
    assert not has_curve_inputs(dict(hk, L_flowtemp_set=500), system)
    assert not has_curve_inputs({k: v for k, v in hk.items() if k != "L_roomtemp_set"}, system)
    assert not has_curve_inputs(hk, {"L_ambient": 30})
    assert not has_curve_inputs(hk, None)


# --- seeding from the recorder's hourly statistics ---------------------------


def _history(flow_max=None):
    rows = {key: [] for key in ("ambient", "room_set", "flow_set", "flow_act", "source")}
    with open(FIXTURES / "history_hk_unmixed_2025_26.csv", newline="") as handle:
        for line in csv.DictReader(handle):
            from datetime import datetime, timezone

            start = datetime.strptime(line["hour_start_utc"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).timestamp()
            flow_set = float(line["flow_set"])
            rows["ambient"].append((start, float(line["ambient"])))
            rows["room_set"].append((start, float(line["room_set"])))
            rows["flow_set"].append((start, min(flow_set, flow_max) if flow_max else flow_set))
            rows["flow_act"].append((start, float(line["flow_act"])))
            if line["buffer_top"]:
                rows["source"].append((start, float(line["buffer_top"])))
    return rows


def test_a_real_heating_season_gives_the_curve_of_the_controller():
    """Unmixed circuit; the controller shows heating curve 1.0, mixer "direkt"."""
    curve = CurveHealth()
    used = seed_curve_from_history(curve, _history())

    assert used > 2000
    assert curve.curve_status == CURVE_DETERMINED
    assert curve.slope == pytest.approx(1.0, abs=0.03)
    assert curve.offset == pytest.approx(10.0, abs=0.3)
    assert curve.circuit_type == "unmixed"
    assert 4 <= curve.flow_surplus <= 7


def test_the_same_season_with_a_clipped_set_point_is_not_reported():
    curve = CurveHealth()
    seed_curve_from_history(curve, _history(flow_max=50.0))
    assert curve.curve_status == CURVE_UNDETERMINABLE


def test_hours_next_to_a_gap_or_a_set_point_change_are_skipped():
    def rows(room_sets, starts=None):
        starts = starts or [i * HOUR for i in range(len(room_sets))]
        return {
            "ambient": [(t, 0.0) for t in starts],
            "room_set": list(zip(starts, room_sets)),
            "flow_set": [(t, _flow_set(0.0, r)) for t, r in zip(starts, room_sets)],
            "flow_act": [(t, _flow_set(0.0, r)) for t, r in zip(starts, room_sets)],
        }

    assert seed_curve_from_history(CurveHealth(), rows([21, 21, 21, 21, 21])) == 3  # the two ends lack a neighbour
    assert seed_curve_from_history(CurveHealth(), rows([21, 21, 21, 17, 17, 17])) == 2
    gap = [0, HOUR, 2 * HOUR, 5 * HOUR, 6 * HOUR, 7 * HOUR]
    assert seed_curve_from_history(CurveHealth(), rows([21] * 6, gap)) == 2
    assert seed_curve_from_history(CurveHealth(), {"ambient": [], "room_set": [], "flow_set": [], "flow_act": []}) == 0
