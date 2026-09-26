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
from homeassistant.util import slugify

from custom_components.oekofen_pellematic_compact.migration import (
    _component_slugs,
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


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_legacy_translated_ids_of_sensors_are_never_flagged(fixture):
    """Same loop guard for pre-4.0 entity IDs, which embedded the *localized*
    display text instead of the raw API key (issue #192).

    ``pu1.L_pump_release`` with the French text "T démarrage pompe" became
    ``sensor.<hub>_buffer_storage_1_t_demarrage_pompe`` — an ID ending in the
    translated suffix ``_pompe`` although the datapoint is a temperature. Every
    component-name language is tried because the component slug and the text
    can come from different languages in real installs.
    """
    api_data = load_fixture(fixture.name)
    discovered = discover_all_entities(api_data)

    looping = []
    for sensor_def in discovered["sensors"]:
        component = sensor_def["component"]
        key = sensor_def["key"]
        raw = api_data.get(component, {}).get(key)
        text = raw.get("text") if isinstance(raw, dict) else None
        if not text:
            continue
        for slug in _component_slugs(component):
            entity_id = f"sensor.pellematic_{slug}_{slugify(text)}"
            if _looks_like_legacy_binary_sensor(entity_id, api_data):
                looping.append(f"{entity_id} ({component}.{key})")

    assert not looping, (
        f"{fixture.name}: legacy translated IDs of plain sensors are flagged as "
        f"binary-sensor orphans, which loops the repair forever: {looping}"
    )


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_heuristic_matches_discovery_for_every_legacy_id_shape(fixture):
    """Full cross-check: for every datapoint of every fixture, build every
    legacy ID shape it could have had — raw key or slugified display text,
    combined with the component slug in each supported language — and require
    the heuristic verdict to equal discovery's own classification.

    ``True`` for something discovery makes a ``sensor``/``select``/``number``
    loops the repair; ``False`` for a real binary sensor leaves the orphan
    invisible forever. Both directions are asserted here.
    """
    api_data = load_fixture(fixture.name)
    discovered = discover_all_entities(api_data)
    binary_keys = {
        (entity["component"], entity["key"]) for entity in discovered["binary_sensors"]
    }

    false_positives, missed = [], []
    for platform in ("sensors", "selects", "numbers", "binary_sensors"):
        for entity in discovered[platform]:
            component, key = entity["component"], entity["key"]
            raw = api_data.get(component, {}).get(key)
            text = raw.get("text") if isinstance(raw, dict) else None
            tails = [key.lower()] + ([slugify(text)] if text else [])
            for slug in sorted(_component_slugs(component)):
                for tail in tails:
                    entity_id = f"sensor.pellematic_{slug}_{tail}"
                    flagged = _looks_like_legacy_binary_sensor(entity_id, api_data)
                    is_binary = (component, key) in binary_keys
                    if flagged and not is_binary:
                        false_positives.append(
                            f"{entity_id} -> {component}.{key} ({platform})"
                        )
                    elif is_binary and not flagged:
                        missed.append(f"{entity_id} -> {component}.{key}")

    assert not false_positives, (
        f"{fixture.name}: flagged as binary-sensor orphans although discovery "
        f"creates them under another platform (endless repair loop): "
        f"{false_positives[:10]}"
    )
    assert not missed, (
        f"{fixture.name}: real binary sensors the repair would never list: "
        f"{missed[:10]}"
    )
