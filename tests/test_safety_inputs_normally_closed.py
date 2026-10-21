"""L_not / L_stb are normally closed: a healthy boiler reports 1 (issue #197).

Every fixture comes from a running installation without an emergency stop or
a tripped safety thermostat, so both entities must come out as "OK".
"""

import glob
import os

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.oekofen_pellematic_compact.dynamic_discovery import discover_all_entities
from custom_components.oekofen_pellematic_compact.sensor import PellematicBinarySensor
from tests.conftest import load_fixture

FIXTURES = sorted(
    os.path.basename(p)
    for p in glob.glob(os.path.join(os.path.dirname(__file__), "fixtures", "*.json"))
)


class _FakeHub:
    def __init__(self, data):
        self.data = data


@pytest.mark.parametrize("fixture", FIXTURES)
def test_safety_inputs_report_no_problem_on_healthy_boilers(fixture):
    data = load_fixture(fixture)
    definitions = [
        d for d in discover_all_entities(data)["binary_sensors"]
        if d["key"] in ("L_not", "L_stb")
    ]
    # Bare-value firmware (no format) keeps them as plain sensors
    expected = sum(
        isinstance(component.get(key), dict)
        for component in data.values() if isinstance(component, dict)
        for key in ("L_not", "L_stb")
    )
    assert len(definitions) == expected
    for definition in definitions:
        assert definition["inverted"] is True
        assert definition["device_class"] == BinarySensorDeviceClass.PROBLEM
        sensor = PellematicBinarySensor.__new__(PellematicBinarySensor)
        sensor._hub = _FakeHub(data)
        sensor._prefix = definition["component"]
        sensor._key = definition["key"]
        sensor._inverted = definition["inverted"]
        assert sensor.is_on is False, f"{fixture}: {definition['component']}.{definition['key']}"


def test_other_binary_sensors_are_not_inverted():
    data = load_fixture("api_response_4hk_jba.json")
    others = [
        d for d in discover_all_entities(data)["binary_sensors"]
        if d["key"] not in ("L_not", "L_stb")
    ]
    assert others
    assert all(d["inverted"] is False for d in others)
