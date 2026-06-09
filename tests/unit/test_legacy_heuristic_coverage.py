"""Regression: every binary-sensor key real fixtures expose must be reachable
by the Repairs heuristic suffix list.

Without this, a future firmware that adds e.g. `L_alarm` with format
"0:Off|1:On" would discover correctly as a binary sensor but, for upgraded
users with orphan `sensor.foo_l_alarm` entries, the Repairs issue would never
list them — the heuristic wouldn't match.
"""

from pathlib import Path

import pytest

from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
)
from custom_components.oekofen_pellematic_compact.migration import (
    _LEGACY_BINARY_KEY_SUFFIXES,
)
from tests.conftest import load_fixture

FIXTURES = sorted(Path(__file__).parent.parent.joinpath("fixtures").glob("*.json"))


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_every_binary_key_has_a_heuristic_suffix(fixture):
    """For each binary sensor discovered from the fixture, assert that some
    suffix in _LEGACY_BINARY_KEY_SUFFIXES would match an entity_id whose
    object_id ends with that key.
    """
    api_data = load_fixture(fixture.name)
    discovered = discover_all_entities(api_data)

    suffixes_lower = tuple(s.lower() for s in _LEGACY_BINARY_KEY_SUFFIXES)
    unmatched = []
    for sensor_def in discovered["binary_sensors"]:
        # Simulate a legacy object_id ending with the discovered key.
        # Modern v4.x: "pe1_l_pump". Pre-4.0 translated: still ends with the
        # underscored key for the modern subset (translated suffixes covered
        # separately by the dedicated tests in test_legacy_binary_sensor_repair).
        key = sensor_def["key"].lower()
        object_id = f"prefix_{key}"
        if not any(object_id.endswith(s) for s in suffixes_lower):
            unmatched.append(sensor_def["key"])

    assert not unmatched, (
        f"{fixture.name}: discovered binary keys not covered by heuristic: "
        f"{unmatched}. Add the underscored form to _LEGACY_BINARY_KEY_SUFFIXES."
    )
