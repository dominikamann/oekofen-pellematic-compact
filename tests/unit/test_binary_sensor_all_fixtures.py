"""Sanity-check is_on across every fixture.

Walks every discovered binary sensor in every fixture and asserts the
returned value is strictly True, False, or None — guarding against the
bool("false") == True regression from issue #187.
"""

from pathlib import Path

import pytest

from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
)
from custom_components.oekofen_pellematic_compact.sensor import PellematicBinarySensor
from tests.conftest import load_fixture

FIXTURES = sorted(Path(__file__).parent.parent.joinpath("fixtures").glob("*.json"))


class _FakeHub:
    def __init__(self, data):
        self.data = data


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_is_on_strictly_boolean_or_none(fixture):
    api_data = load_fixture(fixture.name)
    discovered = discover_all_entities(api_data)

    for definition in discovered["binary_sensors"]:
        sensor = PellematicBinarySensor.__new__(PellematicBinarySensor)
        sensor._hub = _FakeHub(api_data)
        sensor._prefix = definition["component"]
        sensor._key = definition["key"]

        value = sensor.is_on
        assert value is True or value is False or value is None, (
            f"{fixture.name}: {definition['component']}.{definition['key']} "
            f"returned {value!r} ({type(value).__name__})"
        )
