"""Tests for PellematicBinarySensor.is_on.

Reproduces issue #187: L_pump always shows "on" because firmware returns
the string "false"/"true" and Python's bool("false") is True.
"""

import pytest

from custom_components.oekofen_pellematic_compact.sensor import PellematicBinarySensor


class _FakeHub:
    def __init__(self, data):
        self.data = data


def _make_sensor(component, key, hub_data):
    sensor = PellematicBinarySensor.__new__(PellematicBinarySensor)
    sensor._hub = _FakeHub(hub_data)
    sensor._prefix = component
    sensor._key = key
    return sensor


@pytest.mark.parametrize(
    "raw_value,expected",
    [
        # Modern firmware: dict with numeric val
        ({"val": 1, "format": "0:Aus|1:Ein"}, True),
        ({"val": 0, "format": "0:Aus|1:Ein"}, False),
        # Modern firmware: dict with string val (some installs)
        ({"val": "true", "format": "0:Aus|1:Ein"}, True),
        ({"val": "false", "format": "0:Aus|1:Ein"}, False),
        ({"val": "1", "format": "0:Aus|1:Ein"}, True),
        ({"val": "0", "format": "0:Aus|1:Ein"}, False),
        # Old/bare-value firmware (issue #187)
        ("true", True),
        ("false", False),
        ("1", True),
        ("0", False),
    ],
)
def test_is_on_handles_true_false_strings(raw_value, expected):
    hub_data = {"circ1": {"L_pump": raw_value}}
    sensor = _make_sensor("circ1", "L_pump", hub_data)
    assert sensor.is_on is expected


def test_is_on_returns_none_when_missing():
    sensor = _make_sensor("circ1", "L_pump", {"circ1": {}})
    assert sensor.is_on is None
