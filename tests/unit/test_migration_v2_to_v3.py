"""Tests for the V2→V3 binary-sensor domain migration."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from custom_components.oekofen_pellematic_compact.migration import (
    _looks_like_legacy_binary_sensor,
    async_migrate_binary_sensor_domain,
    async_refresh_legacy_binary_sensor_repair_issue,
)


@pytest.mark.parametrize(
    "unique_id,entity_id,expected",
    [
        # Pre-4.0 French/German translated IDs
        ("pellematic_hot_water_1_pompe", "sensor.pellematic_hot_water_1_pompe", True),
        (
            "pellematic_pellematic_1_chaud_ex_ak",
            "sensor.pellematic_pellematic_1_chaud_ex_ak",
            True,
        ),
        (
            "pellematic_pellematic_1_emergency_stop",
            "sensor.pellematic_pellematic_1_emergency_stop",
            True,
        ),
        # Should not match: regular temperature / setpoint sensors
        (
            "pellematic_pe1_l_temp_act",
            "sensor.pellematic_pe1_l_temp_act",
            False,
        ),
        (
            "pellematic_hk1_temp_heat",
            "sensor.pellematic_hk1_temp_heat",
            False,
        ),
        # Regression: _l_pump is a substring of _l_pump_release (a numeric
        # temperature setpoint, NOT a binary sensor). Suffix matching must
        # ignore this case to avoid telling the user to delete a valid sensor.
        (
            "pellematic_pu1_L_pump_release",
            "sensor.pellematic_pu1_l_pump_release",
            False,
        ),
    ],
)
def test_legacy_detection_heuristic(unique_id, entity_id, expected):
    assert _looks_like_legacy_binary_sensor(unique_id, entity_id) is expected


class _FakeEntity:
    def __init__(self, entity_id, unique_id, domain):
        self.entity_id = entity_id
        self.unique_id = unique_id
        self.domain = domain


class _FakeRegistry:
    def __init__(self, entries):
        self._entries = list(entries)
        self._by_id = {e.entity_id: e for e in entries}
        self.renamed: list[tuple[str, str]] = []

    def async_get(self, entity_id):
        return self._by_id.get(entity_id)

    def async_update_entity(self, entity_id, new_entity_id):
        self.renamed.append((entity_id, new_entity_id))
        ent = self._by_id.pop(entity_id)
        ent.entity_id = new_entity_id
        ent.domain = new_entity_id.split(".", 1)[0]
        self._by_id[new_entity_id] = ent


@pytest.mark.asyncio
async def test_migration_renames_matching_unique_ids():
    """Modern entities (unique_id matches current discovery) get renamed."""
    api_data = {
        "circ1": {
            "L_pump": {"val": 0, "format": "0:Aus|1:Ein", "text": "Pumpe"},
            "L_ret_temp": {
                "val": 377,
                "unit": "°C",
                "factor": 0.1,
                "min": "-32768",
                "max": "32767",
                "text": "Rücklauf",
            },
        }
    }

    entries = [
        _FakeEntity(
            entity_id="sensor.pellematic_circ1_l_pump",
            unique_id="pellematic_circ1_L_pump",
            domain="sensor",
        ),
        # Regular sensor — must stay
        _FakeEntity(
            entity_id="sensor.pellematic_circ1_l_ret_temp",
            unique_id="pellematic_circ1_L_ret_temp",
            domain="sensor",
        ),
    ]
    registry = _FakeRegistry(entries)

    hub = SimpleNamespace(data=api_data)
    entry = SimpleNamespace(
        entry_id="abc",
        data={"name": "Pellematic"},
    )
    hass = SimpleNamespace(
        data={"oekofen_pellematic_compact": {"Pellematic": {"hub": hub}}}
    )

    with patch(
        "custom_components.oekofen_pellematic_compact.migration.er.async_get",
        return_value=registry,
    ), patch(
        "custom_components.oekofen_pellematic_compact.migration.er.async_entries_for_config_entry",
        return_value=entries,
    ):
        renamed, legacy = await async_migrate_binary_sensor_domain(hass, entry)

    assert renamed == 1
    assert registry.renamed == [
        ("sensor.pellematic_circ1_l_pump", "binary_sensor.pellematic_circ1_l_pump")
    ]
    assert legacy == []


@pytest.mark.asyncio
async def test_migration_flags_legacy_for_repair():
    """Pre-4.0 translated IDs aren't auto-renamed; they end up in legacy list."""
    api_data = {
        "ww1": {
            "L_pump": {"val": 0, "format": "0:Aus|1:Ein", "text": "Pumpe"},
        }
    }

    # Legacy entity_id from a v3.x install — unique_id no longer matches current discovery
    entries = [
        _FakeEntity(
            entity_id="sensor.pellematic_hot_water_1_pompe",
            unique_id="pellematic_hot_water_1_pompe",
            domain="sensor",
        ),
    ]
    registry = _FakeRegistry(entries)

    hub = SimpleNamespace(data=api_data)
    entry = SimpleNamespace(entry_id="abc", data={"name": "Pellematic"})
    hass = SimpleNamespace(
        data={"oekofen_pellematic_compact": {"Pellematic": {"hub": hub}}}
    )

    with patch(
        "custom_components.oekofen_pellematic_compact.migration.er.async_get",
        return_value=registry,
    ), patch(
        "custom_components.oekofen_pellematic_compact.migration.er.async_entries_for_config_entry",
        return_value=entries,
    ):
        renamed, legacy = await async_migrate_binary_sensor_domain(hass, entry)

    assert renamed == 0
    assert legacy == ["sensor.pellematic_hot_water_1_pompe"]


@pytest.mark.asyncio
async def test_migration_noop_when_no_api_data():
    """Without API data we can't compute expected unique_ids, so we skip safely."""
    hub = SimpleNamespace(data=None)
    entry = SimpleNamespace(entry_id="abc", data={"name": "Pellematic"})
    hass = SimpleNamespace(
        data={"oekofen_pellematic_compact": {"Pellematic": {"hub": hub}}}
    )

    renamed, legacy = await async_migrate_binary_sensor_domain(hass, entry)
    assert renamed == 0
    assert legacy == []


@pytest.mark.asyncio
async def test_refresh_repair_issue_creates_when_legacy_present():
    """Refresh should create/update the Repairs issue when legacy entities exist."""
    entries = [
        _FakeEntity(
            entity_id="sensor.pellematic_hot_water_1_pompe",
            unique_id="pellematic_hot_water_1_pompe",
            domain="sensor",
        ),
    ]
    registry = _FakeRegistry(entries)

    entry = SimpleNamespace(entry_id="abc", data={"name": "Pellematic"})
    hass = SimpleNamespace(data={})

    with patch(
        "custom_components.oekofen_pellematic_compact.migration.er.async_get",
        return_value=registry,
    ), patch(
        "custom_components.oekofen_pellematic_compact.migration.er.async_entries_for_config_entry",
        return_value=entries,
    ), patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as ir_create, patch(
        "homeassistant.helpers.issue_registry.async_delete_issue"
    ) as ir_delete:
        count = await async_refresh_legacy_binary_sensor_repair_issue(hass, entry)

    assert count == 1
    ir_create.assert_called_once()
    ir_delete.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_repair_issue_deletes_when_no_legacy_left():
    """Once the user has cleaned up legacy entities, the issue must auto-clear."""
    # Only modern entity_ids — no legacy candidates
    entries = [
        _FakeEntity(
            entity_id="sensor.pellematic_pe1_l_temp_act",
            unique_id="pellematic_pe1_L_temp_act",
            domain="sensor",
        ),
    ]
    registry = _FakeRegistry(entries)

    entry = SimpleNamespace(entry_id="abc", data={"name": "Pellematic"})
    hass = SimpleNamespace(data={})

    with patch(
        "custom_components.oekofen_pellematic_compact.migration.er.async_get",
        return_value=registry,
    ), patch(
        "custom_components.oekofen_pellematic_compact.migration.er.async_entries_for_config_entry",
        return_value=entries,
    ), patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as ir_create, patch(
        "homeassistant.helpers.issue_registry.async_delete_issue"
    ) as ir_delete:
        count = await async_refresh_legacy_binary_sensor_repair_issue(hass, entry)

    assert count == 0
    ir_create.assert_not_called()
    ir_delete.assert_called_once()
