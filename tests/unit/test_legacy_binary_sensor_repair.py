"""Tests for the binary-sensor-domain Repairs flow (issue #186).

Uses the real Home Assistant entity_registry so the same-domain rename rule
is enforced — the original auto-migration approach silently failed because
a fake registry didn't reject cross-domain renames.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.oekofen_pellematic_compact.const import DOMAIN
from custom_components.oekofen_pellematic_compact.migration import (
    _looks_like_legacy_binary_sensor,
    async_refresh_legacy_binary_sensor_repair_issue,
)


@pytest.mark.parametrize(
    "unique_id,entity_id,expected",
    [
        # Modern v4.0+ orphans (entity_id ends with a known binary key)
        ("pellematic_circ1_L_pump", "sensor.pellematic_circ1_l_pump", True),
        ("pellematic_pe1_L_ak", "sensor.pellematic_pe1_l_ak", True),
        # Pre-4.0 translated IDs
        ("pellematic_hot_water_1_pompe", "sensor.pellematic_hot_water_1_pompe", True),
        (
            "pellematic_pellematic_1_emergency_stop",
            "sensor.pellematic_pellematic_1_emergency_stop",
            True,
        ),
        # Regular sensors must NOT match
        ("pellematic_pe1_l_temp_act", "sensor.pellematic_pe1_l_temp_act", False),
        ("pellematic_hk1_temp_heat", "sensor.pellematic_hk1_temp_heat", False),
        # Regression: _l_pump is a substring of _l_pump_release (temperature
        # setpoint, NOT a binary sensor). Suffix matching must skip this.
        (
            "pellematic_pu1_L_pump_release",
            "sensor.pellematic_pu1_l_pump_release",
            False,
        ),
    ],
)
def test_heuristic_uses_suffix_match(unique_id, entity_id, expected):
    assert _looks_like_legacy_binary_sensor(unique_id, entity_id) is expected


async def test_refresh_creates_fixable_issue_when_orphans_present(hass):
    """A sensor.* entry that looks like a binary sensor produces a fixable issue."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "Pellematic"})
    config_entry.add_to_hass(hass)

    entity_reg = er.async_get(hass)
    entity_reg.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="pellematic_circ1_L_pump",
        config_entry=config_entry,
        suggested_object_id="pellematic_circ1_l_pump",
    )

    with patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as ir_create, patch(
        "homeassistant.helpers.issue_registry.async_delete_issue"
    ) as ir_delete:
        count = await async_refresh_legacy_binary_sensor_repair_issue(hass, config_entry)

    assert count == 1
    ir_create.assert_called_once()
    ir_delete.assert_not_called()

    _, kwargs = ir_create.call_args
    assert kwargs["is_fixable"] is True
    assert kwargs["data"]["entry_id"] == config_entry.entry_id
    assert "sensor.pellematic_circ1_l_pump" in kwargs["data"]["entity_ids"]


async def test_refresh_deletes_issue_when_no_orphans_left(hass):
    """Once orphan sensor.* entries are gone, the Repairs issue auto-clears."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "Pellematic"})
    config_entry.add_to_hass(hass)

    entity_reg = er.async_get(hass)
    entity_reg.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="pellematic_pe1_L_temp_act",
        config_entry=config_entry,
        suggested_object_id="pellematic_pe1_l_temp_act",
    )

    with patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as ir_create, patch(
        "homeassistant.helpers.issue_registry.async_delete_issue"
    ) as ir_delete:
        count = await async_refresh_legacy_binary_sensor_repair_issue(hass, config_entry)

    assert count == 0
    ir_create.assert_not_called()
    ir_delete.assert_called_once()


async def test_fix_flow_removes_entries_and_reloads(hass):
    """The Repairs flow deletes the orphan entries and reloads the config entry."""
    from custom_components.oekofen_pellematic_compact.repairs import (
        FixLegacyBinarySensorsFlow,
    )

    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "Pellematic"})
    config_entry.add_to_hass(hass)

    entity_reg = er.async_get(hass)
    entity_reg.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="pellematic_circ1_L_pump",
        config_entry=config_entry,
        suggested_object_id="pellematic_circ1_l_pump",
    )
    assert entity_reg.async_get("sensor.pellematic_circ1_l_pump") is not None

    flow = FixLegacyBinarySensorsFlow(
        entry_id=config_entry.entry_id,
        entity_ids=["sensor.pellematic_circ1_l_pump"],
    )
    flow.hass = hass

    with patch.object(
        hass.config_entries, "async_reload", return_value=True
    ) as reload_mock:
        result = await flow.async_step_confirm(user_input={})

    assert entity_reg.async_get("sensor.pellematic_circ1_l_pump") is None
    reload_mock.assert_called_once_with(config_entry.entry_id)
    assert result["type"] == "create_entry"


async def test_fix_flow_ignores_foreign_entries(hass):
    """The flow must NOT delete entries belonging to other config entries."""
    from custom_components.oekofen_pellematic_compact.repairs import (
        FixLegacyBinarySensorsFlow,
    )

    own_entry = MockConfigEntry(domain=DOMAIN, data={"name": "Pellematic"})
    own_entry.add_to_hass(hass)
    foreign_entry = MockConfigEntry(domain="some_other_integration", data={})
    foreign_entry.add_to_hass(hass)

    entity_reg = er.async_get(hass)
    entity_reg.async_get_or_create(
        domain="sensor",
        platform="some_other_integration",
        unique_id="foreign_l_pump",
        config_entry=foreign_entry,
        suggested_object_id="foreign_l_pump",
    )

    flow = FixLegacyBinarySensorsFlow(
        entry_id=own_entry.entry_id,
        entity_ids=["sensor.foreign_l_pump"],
    )
    flow.hass = hass

    with patch.object(hass.config_entries, "async_reload", return_value=True):
        await flow.async_step_confirm(user_input={})

    # Foreign entry must still exist
    assert entity_reg.async_get("sensor.foreign_l_pump") is not None
