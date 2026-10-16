"""Full setup against real fixtures: diagnosis entities, events and button."""

import copy
from unittest.mock import patch

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.oekofen_pellematic_compact.const import (
    CONF_API_SUFFIX,
    CONF_CHARSET,
    CONF_OLD_FIRMWARE,
    DOMAIN,
)
from custom_components.oekofen_pellematic_compact.diagnosis import EVENT_FINDING, EVENT_MESSAGE
from tests.conftest import load_fixture

FETCH = "custom_components.oekofen_pellematic_compact.fetch_data"


async def _setup(hass, data):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "host": "http://192.0.2.1:4321/pw/all",
            "name": "Pellematic",
            CONF_CHARSET: "utf-8",
            CONF_API_SUFFIX: "?",
            CONF_OLD_FIRMWARE: False,
            "migration_notification_shown": True,
            "entity_id_warning_shown": True,
        },
    )
    entry.add_to_hass(hass)
    with patch(FETCH, return_value=data):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _poll(hass, data):
    hub = hass.data[DOMAIN]["Pellematic"]["hub"]
    with patch(FETCH, return_value=data):
        await hub.async_refresh_api_data()
        await hass.async_block_till_done()


def _entity_ids(hass, entry):
    registry = er.async_get(hass)
    return {e.entity_id for e in er.async_entries_for_config_entry(registry, entry.entry_id)}


async def test_pellet_installation(hass, enable_custom_integrations):
    data = load_fixture("api_response_ext_zx.json")
    entry = await _setup(hass, data)

    ids = _entity_ids(hass, entry)
    for entity_id in (
        "sensor.pellematic_diagnosis",
        "binary_sensor.pellematic_diagnosis_problem",
        "sensor.pellematic_last_message",
        "sensor.pellematic_message_count",
        "sensor.pellematic_pe1_flue_gas_index",
        "sensor.pellematic_pe1_ignition_time",
        "sensor.pellematic_pe1_burner_starts_per_day",
        "sensor.pellematic_pe1_burner_runtime_per_start",
        "sensor.pellematic_pe1_full_load_hours_since_maintenance",
        "button.pellematic_pe1_maintenance_done",
    ):
        assert entity_id in ids, entity_id
    assert not any("compressor" in i for i in ids)

    messages, findings = [], []
    hass.bus.async_listen(EVENT_MESSAGE, messages.append)
    hass.bus.async_listen(EVENT_FINDING, findings.append)
    await _poll(hass, data)

    diagnosis = hass.states.get("sensor.pellematic_diagnosis")
    assert diagnosis.state == "warning"
    assert diagnosis.attributes["friendly_name"] == "Pellematic Diagnosis"
    assert diagnosis.attributes["summary"] == "Boiler message: PE 1 Pellets Warnung"
    assert diagnosis.attributes["findings"][0]["code"] == "boiler_message"
    assert hass.states.get("binary_sensor.pellematic_diagnosis_problem").state == "on"
    last = hass.states.get("sensor.pellematic_last_message")
    assert last.state == "PE 1 Pellets Warnung"
    assert last.attributes["code"] == 5054
    assert hass.states.get("sensor.pellematic_message_count").state == "1"
    assert [e.data["code"] for e in messages] == [5054]
    assert [(e.data["code"], e.data["active"]) for e in findings] == [("boiler_message", True)]

    await _poll(hass, data)  # same message again: nothing new
    assert len(messages) == 1 and len(findings) == 1

    cleared = copy.deepcopy(data)
    cleared["error"] = {}
    await _poll(hass, cleared)
    assert [(e.data["code"], e.data["active"]) for e in findings][-1] == ("boiler_message", False)
    assert hass.states.get("binary_sensor.pellematic_diagnosis_problem").state == "off"

    monitor = hass.data[DOMAIN]["Pellematic"]["diagnosis"]
    monitor.diagnosis.heater("pe1").full_load_seconds = 1900 * 3600
    await _poll(hass, cleared)
    assert hass.states.get("sensor.pellematic_diagnosis").state == "maintenance_due"
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.pellematic_pe1_maintenance_done"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.pellematic_pe1_full_load_hours_since_maintenance").state == "0.0"
    assert hass.states.get("sensor.pellematic_diagnosis").state in ("ok", "learning")

    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_heat_pump_installation(hass, enable_custom_integrations):
    entry = await _setup(hass, load_fixture("api_response_base_csta.json"))
    ids = _entity_ids(hass, entry)
    assert "sensor.pellematic_wp1_compressor_starts_per_day" in ids
    assert "sensor.pellematic_wp1_compressor_runtime_per_cycle" in ids
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_flue_gas_index_needs_the_key(hass, enable_custom_integrations):
    data = copy.deepcopy(load_fixture("api_response_ext_zx.json"))
    del data["pe1"]["L_fluegas"]
    entry = await _setup(hass, data)
    ids = _entity_ids(hass, entry)
    assert "sensor.pellematic_diagnosis" in ids
    assert "sensor.pellematic_pe1_flue_gas_index" not in ids
    assert await hass.config_entries.async_unload(entry.entry_id)
