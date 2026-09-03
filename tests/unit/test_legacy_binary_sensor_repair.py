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
    "entity_id,expected",
    [
        # Modern v4.0+ orphans (entity_id ends with a known binary key)
        ("sensor.pellematic_circ1_l_pump", True),
        ("sensor.pellematic_pe1_l_ak", True),
        # Pre-4.0 translated IDs
        ("sensor.pellematic_hot_water_1_pompe", True),
        ("sensor.pellematic_pellematic_1_emergency_stop", True),
        # Regular sensors must NOT match
        ("sensor.pellematic_pe1_l_temp_act", False),
        ("sensor.pellematic_hk1_temp_heat", False),
        # Regression: _l_pump is a substring of _l_pump_release (temperature
        # setpoint, NOT a binary sensor). Suffix matching must skip this.
        ("sensor.pellematic_pu1_l_pump_release", False),
    ],
)
def test_heuristic_uses_suffix_match(entity_id, expected):
    assert _looks_like_legacy_binary_sensor(entity_id) is expected


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
    # data must only contain scalar values to comply with HA's typed contract
    # (dict[str, str|int|float|None]). entity_ids are looked up fresh in the
    # flow, not carried through data.
    assert kwargs["data"] == {"entry_id": config_entry.entry_id}
    assert kwargs["translation_placeholders"]["count"] == "1"
    assert "sensor.pellematic_circ1_l_pump" in kwargs["translation_placeholders"]["entity_list"]


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


async def test_fix_flow_removes_orphans_and_schedules_reload(hass):
    """The Repairs flow re-queries the registry, deletes orphans, and
    schedules a reload (does NOT await it)."""
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

    flow = FixLegacyBinarySensorsFlow(entry_id=config_entry.entry_id)
    flow.hass = hass

    with patch.object(
        hass.config_entries, "async_schedule_reload"
    ) as schedule_mock:
        result = await flow.async_step_confirm(user_input={})

    assert entity_reg.async_get("sensor.pellematic_circ1_l_pump") is None
    schedule_mock.assert_called_once_with(config_entry.entry_id)
    assert result["type"] == "create_entry"


async def test_fix_flow_ignores_foreign_entries(hass):
    """The flow filters by config_entry_id — entries belonging to other
    config entries must not be deleted."""
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

    flow = FixLegacyBinarySensorsFlow(entry_id=own_entry.entry_id)
    flow.hass = hass

    with patch.object(hass.config_entries, "async_schedule_reload"):
        await flow.async_step_confirm(user_input={})

    # Foreign entry must still exist (different config_entry_id)
    assert entity_reg.async_get("sensor.foreign_l_pump") is not None


async def test_fix_flow_aborts_when_entry_id_missing(hass):
    """If issue.data was lost (post-restart pre-setup race), abort cleanly
    instead of silently no-opping then declaring success."""
    from custom_components.oekofen_pellematic_compact.repairs import (
        FixLegacyBinarySensorsFlow,
    )

    flow = FixLegacyBinarySensorsFlow(entry_id="")
    flow.hass = hass

    result = await flow.async_step_init()
    assert result["type"] == "abort"
    assert result["reason"] == "missing_data"


async def test_migrate_entry_recovers_stranded_v3_entry(hass):
    """Users who installed the broken intermediate release have entry.version=3
    persisted with the obsolete PENDING flag. async_migrate_entry must reset
    them to the current CONFIG_VERSION and strip the stale flag, otherwise the
    migration loops every restart."""
    from custom_components.oekofen_pellematic_compact import (
        CONFIG_VERSION,
        async_migrate_entry,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Pellematic",
            "pending_binary_sensor_domain_migration": True,
            "host": "http://192.0.2.1:4321/pwd",
        },
        version=3,
    )
    entry.add_to_hass(hass)

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == CONFIG_VERSION
    assert "pending_binary_sensor_domain_migration" not in entry.data
    assert entry.data["name"] == "Pellematic"  # unrelated keys preserved


async def test_fix_flow_renders_form_on_first_call(hass):
    """The show-form branch must use self.handler / self.issue_id from HA
    to look up placeholders — exercising the path the previous test missed."""
    from homeassistant.helpers import issue_registry as ir

    from custom_components.oekofen_pellematic_compact.repairs import (
        FixLegacyBinarySensorsFlow,
    )

    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "Pellematic"})
    config_entry.add_to_hass(hass)

    issue_id = "legacy_binary_sensors_under_sensor_domain_test"
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="legacy_binary_sensors_under_sensor_domain",
        translation_placeholders={"count": "3", "entity_list": "- a\n- b\n- c"},
        data={"entry_id": config_entry.entry_id},
    )

    flow = FixLegacyBinarySensorsFlow(entry_id=config_entry.entry_id)
    flow.hass = hass
    flow.handler = DOMAIN
    flow.issue_id = issue_id

    result = await flow.async_step_confirm(user_input=None)

    assert result["type"] == "form"
    assert result["step_id"] == "confirm"
    assert result["description_placeholders"] == {
        "count": "3",
        "entity_list": "- a\n- b\n- c",
    }
