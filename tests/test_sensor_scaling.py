"""Regression tests for sensor state computation.

Ensures non-numeric API values (e.g. heating-schedule strings like
'00:00-00:00' or '07:00-10:00' that ship with factor=1 in newer firmware)
do not trigger the 'could not be scaled' warning or the 'An error occurred'
error on every poll.
"""
import logging
from pathlib import Path

import pytest

from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
)
from custom_components.oekofen_pellematic_compact.sensor import PellematicSensor

from .conftest import load_fixture


FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_NAMES = sorted(f.name for f in FIXTURES_DIR.glob("api_response_*.json"))


class _StubHub:
    """Minimal hub stub exposing only .data, which is what sensors read."""

    def __init__(self, data):
        self.data = data


def _build_sensors(api_data):
    """Build PellematicSensor instances for every discovered sensor definition."""
    discovered = discover_all_entities(api_data)
    hub = _StubHub(api_data)
    sensors = []
    for sensor_def in discovered["sensors"]:
        sensor = PellematicSensor(
            hub_name="Pellematic",
            hub=hub,
            device_info={},
            sensor_definition=sensor_def,
        )
        sensors.append(sensor)
    return sensors


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_no_scaling_warnings_for_fixture(fixture_name, caplog):
    """Reading .state on every discovered sensor must not log scaling warnings."""
    api_data = load_fixture(fixture_name)

    with caplog.at_level(
        logging.WARNING,
        logger="custom_components.oekofen_pellematic_compact.sensor",
    ):
        for sensor in _build_sensors(api_data):
            _ = sensor.state

    offenders = [
        r
        for r in caplog.records
        if "could not be scaled" in r.getMessage()
        or "An error occurred" in r.getMessage()
    ]
    assert not offenders, (
        f"{fixture_name}: unexpected sensor warnings/errors: "
        + "; ".join(r.getMessage() for r in offenders)
    )


def test_greenmode_timeblock_passes_through_as_string():
    """Time-range strings must be returned as-is, not scaled, not warned about."""
    api_data = load_fixture("api_response_greenmode.json")
    sensors_by_uid = {s._attr_unique_id: s for s in _build_sensors(api_data)}

    # ww1 has real schedule values; hk1 has all-zero ones.
    assert sensors_by_uid["pellematic_ww1_L_green_1_timeblock"].state == "07:00-10:00"
    assert sensors_by_uid["pellematic_hk1_L_green_1_timeblock"].state == "00:00-00:00"


def test_numeric_scaling_still_works():
    """Sanity check: numeric values with factor are still scaled."""
    api_data = load_fixture("api_response_greenmode.json")
    sensors_by_uid = {s._attr_unique_id: s for s in _build_sensors(api_data)}

    # L_ambient = {"val":236, "factor":0.1} -> 23.6 °C
    assert sensors_by_uid["pellematic_system_L_ambient"].state == pytest.approx(23.6)
