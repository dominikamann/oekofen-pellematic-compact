"""Regression: the Repairs issue must never flag an entity that discovery
would recreate under ``sensor.*``.

Whenever it does, the user is stuck in a loop: fix → entity deleted → discovery
recreates the identical ``sensor.*`` → flagged again. Checked across every real
fixture so a future firmware quirk cannot reintroduce it.
"""

from pathlib import Path

import pytest

from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
)
from custom_components.oekofen_pellematic_compact.migration import (
    _looks_like_legacy_binary_sensor,
)
from tests.conftest import load_fixture

FIXTURES = sorted(Path(__file__).parent.parent.joinpath("fixtures").glob("*.json"))


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_discovered_sensors_are_never_flagged_as_orphans(fixture):
    api_data = load_fixture(fixture.name)
    discovered = discover_all_entities(api_data)

    looping = []
    for sensor_def in discovered["sensors"]:
        # The entity_id discovery produces for this definition.
        object_id = f"{sensor_def['component']}_{sensor_def['key']}".lower()
        entity_id = f"sensor.pellematic_{object_id}"
        if _looks_like_legacy_binary_sensor(entity_id, api_data):
            looping.append(entity_id)

    assert not looping, (
        f"{fixture.name}: these entities are created as sensor.* by discovery "
        f"but flagged as binary-sensor orphans by the Repairs heuristic, which "
        f"loops the repair forever: {looping}"
    )


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_discovered_binary_sensors_are_still_flagged(fixture):
    """The API-aware check must not blunt the heuristic: entities discovery
    puts under binary_sensor.* must still be recognised when they linger as
    orphan sensor.* entries."""
    api_data = load_fixture(fixture.name)
    discovered = discover_all_entities(api_data)

    missed = []
    for sensor_def in discovered["binary_sensors"]:
        object_id = f"{sensor_def['component']}_{sensor_def['key']}".lower()
        entity_id = f"sensor.pellematic_{object_id}"
        if not _looks_like_legacy_binary_sensor(entity_id, api_data):
            missed.append(entity_id)

    assert not missed, (
        f"{fixture.name}: real binary sensors no longer detected as orphans: {missed}"
    )
