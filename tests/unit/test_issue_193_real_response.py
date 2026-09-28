"""Regression test for issue #193 against the reporter's real API response.

`api_response_v402b_jsonprops.json` is the anonymized `/all?` output of the
installation from the report (Touch V4.02b) — the only response we have that
exposes the `L_cfg_*` keys. They are not stock firmware: they come from the
`json.properties` file on a USB stick described in discussion #194, which makes
the Touch publish ~90 extra read-only keys. Its times are delivered in
milliseconds (`factor` 1/60000), so a perfectly normal "120 min" sits exactly at
`max` 7200000 and used to be blanked as `unknown` by the old "within 2 of
min/max" rule.

The synthetic cases live in `test_sensor_sentinel_filter.py`; this file pins the
behavior to the untouched response, so a future change to the sanitizer has to
prove itself against real firmware data.
"""

from __future__ import annotations

import pytest

from tests.conftest import load_fixture
from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
)
from custom_components.oekofen_pellematic_compact.sensor import (
    PellematicSensor,
    _sanitize_oekofen_value,
)

FIXTURE = "api_response_v402b_jsonprops.json"


class _StubHub:
    def __init__(self, data):
        self.data = data


@pytest.fixture(name="api_data")
def api_data_fixture():
    return load_fixture(FIXTURE)


def _sensor(api_data, component, key):
    definition = next(
        d
        for d in discover_all_entities(api_data)["sensors"]
        if d["component"] == component and d["key"] == key
    )
    return PellematicSensor(
        hub_name="Pellematic",
        hub=_StubHub(api_data),
        device_info={},
        sensor_definition=definition,
    )


@pytest.mark.parametrize(
    "key,expected_minutes",
    [
        # The three keys from the report, plus the reference key that worked.
        ("L_cfg_min_standstill", 60.0),   # val 3600000 == max
        ("L_cfg_restart_lock", 0.0),      # val 0 == min
        ("L_cfg_uw_runon", 120.0),        # val 7200000 == max
        ("L_cfg_min_runtime", 10.0),      # val 600000, inside its range
    ],
)
def test_reported_keys_show_their_value(api_data, key, expected_minutes):
    sensor = _sensor(api_data, "pe1", key)
    assert sensor.state == pytest.approx(expected_minutes, abs=0.01)


def test_no_cfg_key_in_the_response_is_blanked(api_data):
    """All 85 `L_cfg_*` readings are genuine settings — none may be filtered."""
    blanked = [
        f"{component}.{key}"
        for component, block in api_data.items()
        if isinstance(block, dict)
        for key, raw in block.items()
        if key.startswith("L_cfg_")
        and isinstance(raw, dict)
        and _sanitize_oekofen_value(raw, raw["val"]) is None
    ]
    assert blanked == []


def test_only_the_genuine_sentinel_is_dropped(api_data):
    """Across the whole response exactly one numeric reading disappears:
    `pe1.L_ext_temp` = -32768, the "no external sensor" marker."""
    dropped = [
        f"{component}.{key}"
        for component, block in api_data.items()
        if isinstance(block, dict)
        for key, raw in block.items()
        if isinstance(raw, dict)
        and "val" in raw
        and isinstance(raw["val"], (int, float))
        and _sanitize_oekofen_value(raw, raw["val"]) is None
    ]
    assert dropped == ["pe1.L_ext_temp"]
