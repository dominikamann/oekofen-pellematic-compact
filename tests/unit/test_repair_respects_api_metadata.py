"""Regression: the Repairs heuristic must not flag pump fields that the API
reports as modulation percentages (PR #190 follow-up).

`L_pump` means two different things depending on the component:

* ``hk`` / ``ww`` / ``circ`` → ``format: "0:Aus|1:Ein"`` → a real binary sensor
* ``sk`` / ``pu``           → ``unit: "%"``, no format → a speed-modulation
  sensor, which discovery correctly creates under ``sensor.*``

The purely name-based suffix heuristic matched both, so a solar pump was
flagged as an orphan, deleted by the Repairs flow, recreated by discovery as
the same ``%`` sensor, and flagged again — an endless repair loop.
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

# Minimal API shape covering both meanings of L_pump.
API_DATA = {
    "sk1": {"L_pump": {"val": 0, "unit": "%", "text": "Pumpe", "format": None}},
    "pu1": {"L_pump": {"val": 0, "unit": "%", "text": "Pumpe", "format": None}},
    "circ1": {"L_pump": {"val": 0, "unit": None, "text": "Pumpe", "format": "0:Aus|1:Ein"}},
    "hk1": {"L_pump": {"val": 0, "unit": None, "text": "Pumpe", "format": "0:Aus|1:Ein"}},
}


@pytest.mark.parametrize(
    "entity_id,expected",
    [
        # Modulation pumps (unit %, no format) — must NOT be flagged
        ("sensor.pellematic_sk1_l_pump", False),
        ("sensor.pellematic_pu1_l_pump", False),
        # ...including the pre-4.0 translated ID the user actually reported
        ("sensor.pellematic_solar_collector_1_pompe", False),
        # Genuine on/off pumps — must still be flagged
        ("sensor.pellematic_circ1_l_pump", True),
        ("sensor.pellematic_hk1_l_pump", True),
    ],
)
def test_heuristic_consults_api_metadata(entity_id, expected):
    assert _looks_like_legacy_binary_sensor(entity_id, API_DATA) is expected


def test_heuristic_falls_back_to_suffix_match_without_api_data():
    """Old firmware returns bare values with no metadata; without API data the
    heuristic must keep its previous name-based behaviour."""
    assert _looks_like_legacy_binary_sensor("sensor.pellematic_sk1_l_pump") is True
    assert _looks_like_legacy_binary_sensor("sensor.pellematic_pe1_l_temp_act") is False


def test_bare_value_firmware_is_never_flagged():
    """Old firmware (<= v3.10d) returns bare values with no `format`, so
    discovery can only ever create sensors. Flagging those would loop the
    repair forever, so a resolved-but-metadata-less field must not be flagged.
    """
    bare = {"sk1": {"L_pump": 0}, "circ1": {"L_pump": 0}}
    assert _looks_like_legacy_binary_sensor("sensor.pellematic_sk1_l_pump", bare) is False
    assert _looks_like_legacy_binary_sensor("sensor.pellematic_circ1_l_pump", bare) is False


def test_unresolvable_entity_keeps_name_based_verdict():
    """A legacy ID we cannot map to any component in the current API response
    (e.g. hardware since removed) falls back to the name heuristic."""
    assert (
        _looks_like_legacy_binary_sensor(
            "sensor.pellematic_hot_water_9_pompe", {"sk1": {"L_pump": {"val": 0}}}
        )
        is True
    )


async def test_refresh_does_not_flag_modulation_pump(hass):
    """End-to-end: with API data available, a solar modulation pump raises no
    Repairs issue, so the fix/recreate/flag loop cannot start."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "Pellematic"})
    config_entry.add_to_hass(hass)

    entity_reg = er.async_get(hass)
    entity_reg.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="pellematic_sk1_L_pump",
        config_entry=config_entry,
        suggested_object_id="pellematic_sk1_l_pump",
    )

    class _Hub:
        data = API_DATA

    hass.data.setdefault(DOMAIN, {})["Pellematic"] = {"hub": _Hub()}

    with patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as ir_create, patch(
        "homeassistant.helpers.issue_registry.async_delete_issue"
    ) as ir_delete:
        count = await async_refresh_legacy_binary_sensor_repair_issue(hass, config_entry)

    assert count == 0
    ir_create.assert_not_called()
    ir_delete.assert_called_once()


async def test_fix_flow_does_not_delete_modulation_pump(hass):
    """The Repairs flow re-applies the heuristic on submit — it must use the
    same API-aware verdict, otherwise it deletes a healthy sensor."""
    from custom_components.oekofen_pellematic_compact.repairs import (
        FixLegacyBinarySensorsFlow,
    )

    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "Pellematic"})
    config_entry.add_to_hass(hass)

    entity_reg = er.async_get(hass)
    entity_reg.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="pellematic_sk1_L_pump",
        config_entry=config_entry,
        suggested_object_id="pellematic_sk1_l_pump",
    )
    entity_reg.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="pellematic_circ1_L_pump",
        config_entry=config_entry,
        suggested_object_id="pellematic_circ1_l_pump",
    )

    class _Hub:
        data = API_DATA

    hass.data.setdefault(DOMAIN, {})["Pellematic"] = {"hub": _Hub()}

    flow = FixLegacyBinarySensorsFlow(entry_id=config_entry.entry_id)
    flow.hass = hass

    with patch.object(hass.config_entries, "async_schedule_reload"):
        await flow.async_step_confirm(user_input={})

    # The modulation pump survives; the genuine on/off pump is removed.
    assert entity_reg.async_get("sensor.pellematic_sk1_l_pump") is not None
    assert entity_reg.async_get("sensor.pellematic_circ1_l_pump") is None
