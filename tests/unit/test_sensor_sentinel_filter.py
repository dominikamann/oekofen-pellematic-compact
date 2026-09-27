"""Tests for `_sanitize_oekofen_value` (issue #193).

The old filter dropped anything within 2 of `min`/`max` whenever the raw range
was larger than 1000. That is right for the int16 sentinels (-32768 … 32767)
but wrong for every key with a *genuine* large range — above all times, which
the API delivers in milliseconds (`factor` 1/60000), so a perfectly normal
"120 min" sits exactly at `max` 7200000 and vanished as `unknown`.
"""

from __future__ import annotations

import pytest

from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
)
from custom_components.oekofen_pellematic_compact.sensor import (
    PellematicSensor,
    _sanitize_oekofen_value,
)

MINUTE_FACTOR = 1.6667e-05


class _StubHub:
    def __init__(self, data):
        self.data = data


# ---------------------------------------------------------------- real values


@pytest.mark.parametrize(
    "raw,expected",
    [
        # The three keys from the report, firmware V4.02b.
        (
            {"val": 3600000, "unit": "min", "factor": MINUTE_FACTOR,
             "min": 60000, "max": 3600000, "text": "Min Stillstandszeit"},
            3600000,
        ),
        (
            {"val": 0, "unit": "min", "factor": MINUTE_FACTOR,
             "min": 0, "max": 14400000.0, "text": "Sperrzeit Neustart"},
            0,
        ),
        (
            {"val": 7200000, "unit": "min", "factor": MINUTE_FACTOR,
             "min": 0, "max": 7200000, "text": "UW Nachlaufzeit"},
            7200000,
        ),
        # Reference value from the report that already worked — must stay.
        (
            {"val": 600000, "unit": "min", "factor": MINUTE_FACTOR,
             "min": 60000, "max": 1800000, "text": "Min Laufzeit"},
            600000,
        ),
        # Percentages at both ends of a small range (never filtered before).
        ({"val": 0, "unit": "%", "factor": 1, "min": 0, "max": 100}, 0),
        ({"val": 100, "unit": "%", "factor": 1, "min": 0, "max": 100}, 100),
        # A setting slightly outside its advertised range is real user data:
        # hk1.solarheat_off_tmp = 81.0 °C with max 80.0 °C (three fixtures).
        ({"val": 810, "unit": "°C", "factor": 0.1, "min": 300, "max": 800}, 810),
        # ...as is an unconfigured 0 below `min` (pu1.ext_mintemp_on).
        ({"val": 0, "unit": "°C", "factor": 0.1, "min": 80, "max": 900}, 0),
    ],
)
def test_legitimate_values_survive(raw, expected):
    assert _sanitize_oekofen_value(raw, raw["val"]) == expected


def test_value_at_max_reaches_the_entity_state():
    """End-to-end: the sensor state is the scaled reading, not `unknown`."""
    api_data = {
        "pe1": {
            "pe_info": "pellematic data",
            "L_cfg_uw_runon": {
                "val": 7200000, "unit": "min", "factor": MINUTE_FACTOR,
                "min": 0, "max": 7200000, "text": "UW Nachlaufzeit",
            },
        }
    }
    definition = next(
        d
        for d in discover_all_entities(api_data)["sensors"]
        if d["key"] == "L_cfg_uw_runon"
    )
    sensor = PellematicSensor(
        hub_name="Pellematic",
        hub=_StubHub(api_data),
        device_info={},
        sensor_definition=definition,
    )
    assert sensor.state == pytest.approx(120.0, abs=0.01)


# ------------------------------------------------------------------ sentinels


@pytest.mark.parametrize(
    "raw",
    [
        # int16 markers on an int16 range (pe1.L_ext_temp, L_pellets_today).
        {"val": -32768, "unit": "°C", "factor": 0.1, "min": -32768, "max": 32767},
        {"val": 32765, "unit": "kg", "factor": 1, "min": -32768, "max": 32767},
        {"val": 32767, "factor": 1, "min": -32768, "max": 32767},
        # Old firmware ships min/max as strings — used to disable the filter.
        {"val": "-32768", "unit": "°C", "factor": 0.1, "min": "-32768", "max": "32767"},
        {"val": "32765", "unit": "kg", "factor": 1, "min": "-32768", "max": "32767"},
        # No metadata at all (us310, with_sk_dash fixtures).
        {"val": -32768, "unit": "°C", "factor": 0.1},
        # Sentinel on a key with a small genuine range (pu2.ext_mintemp_on).
        {"val": 32766, "unit": "°C", "factor": 0.1, "min": 80, "max": 900},
        # Magnitudes off the scale entirely (pe1.L_storage_max = 304366 kg).
        {"val": 304366, "unit": "kg", "factor": 1, "min": 150, "max": 30000},
    ],
)
def test_sentinels_and_impossible_values_are_dropped(raw):
    assert _sanitize_oekofen_value(raw, raw["val"]) is None


def test_int16_band_is_a_real_reading_when_the_range_allows_it():
    """A ms-based time may legitimately hold a number inside the sentinel band
    — its range reaches far beyond int16, so it is not a marker."""
    raw = {"val": 32766, "unit": "min", "factor": MINUTE_FACTOR,
           "min": 0, "max": 14400000}
    assert _sanitize_oekofen_value(raw, raw["val"]) == 32766


# ------------------------------------------------------------- strings, misc.


@pytest.mark.parametrize("value", ["unknown", "unavailable", "none", "", "  "])
def test_placeholder_strings_are_dropped(value):
    assert _sanitize_oekofen_value({"val": value}, value) is None


def test_non_numeric_strings_pass_through():
    raw = {"val": "00:00-06:00", "factor": 1}
    assert _sanitize_oekofen_value(raw, raw["val"]) == "00:00-06:00"


# ------------------------------------------------------- number platform, too


def _build_number(api_data, component, key):
    from custom_components.oekofen_pellematic_compact.number import PellematicNumber

    definition = next(
        d
        for d in discover_all_entities(api_data)["numbers"]
        if d["key"] == key and d["component"] == component
    )
    return PellematicNumber(
        hub_name="Pellematic",
        hub=_StubHub(api_data),
        device_info={},
        number_definition=definition,
    )


def test_number_entity_drops_sentinel_instead_of_showing_it():
    """Writable fields carry sentinels as well: pu2.ext_mintemp_on = 32766 was
    displayed as 3276.6 °C on a number whose own range is 8…90 °C (fixtures
    api_response_fren / api_response_mg)."""
    api_data = {
        "pu2": {
            "pu_info": "accu data",
            "ext_mintemp_on": {
                "val": 32766, "unit": "°C", "factor": 0.1, "min": 80, "max": 900,
                "text": "BT Tmin charge",
            },
        }
    }
    number = _build_number(api_data, "pu2", "ext_mintemp_on")
    number._update_state()
    assert number.native_value is None


def test_number_entity_keeps_value_at_its_limit():
    """The counterpart: a setting sitting exactly at its max must still show."""
    api_data = {
        "pu1": {
            "pu_info": "accu data",
            "ext_mintemp_on": {
                "val": 900, "unit": "°C", "factor": 0.1, "min": 80, "max": 900,
                "text": "BT Tmin charge",
            },
        }
    }
    number = _build_number(api_data, "pu1", "ext_mintemp_on")
    number._update_state()
    assert number.native_value == pytest.approx(90.0)


def test_bare_value_firmware_has_no_metadata_dict():
    """Firmware <= v3.10d delivers the value itself instead of a dict. Both
    platforms hand that straight to the sanitizer, so it must not assume a dict
    — the number platform would otherwise turn every reading into `unknown`."""
    assert _sanitize_oekofen_value(580, 580) == 580
    assert _sanitize_oekofen_value("580", "580") == 580
    # A sentinel is still recognised without any metadata.
    assert _sanitize_oekofen_value(-32768, -32768) is None
