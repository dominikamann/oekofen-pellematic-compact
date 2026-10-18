"""Full setup against real fixtures: diagnosis entities, events and button."""

import copy

import pytest
from unittest.mock import patch

from homeassistant.helpers import entity_registry as er
from datetime import timedelta

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

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
    quiet = copy.deepcopy(data)
    quiet["error"] = {}
    entry = await _setup(hass, quiet)

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

    assert hass.states.get("sensor.pellematic_last_message").state == "No messages"
    runtime = hass.states.get("sensor.pellematic_pe1_burner_runtime_per_start")
    assert runtime.state != "unknown" and runtime.attributes["basis"] == "lifetime"
    assert hass.states.get("sensor.pellematic_diagnosis").attributes.get("friendly_name")

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


async def test_diagnosis_is_persisted_while_polling(hass, hass_storage, enable_custom_integrations):
    """The store must be written during operation, not only at shutdown."""
    data = load_fixture("api_response_ext_zx.json")
    entry = await _setup(hass, data)
    await _poll(hass, data)  # a new boiler message triggers a save
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
    await hass.async_block_till_done()
    stored = hass_storage[f"{DOMAIN}.diagnosis.{entry.entry_id}"]["data"]
    assert stored["messages"]["count"] == 1
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_baseline_from_recorder_history(recorder_mock, hass, enable_custom_integrations):
    """A new installation on a fouled boiler warns at once from the recorder statistics."""
    from homeassistant.components.recorder.models import StatisticMeanType
    from homeassistant.components.recorder.statistics import async_import_statistics
    from pytest_homeassistant_custom_component.components.recorder.common import (
        async_wait_recording_done,
    )

    data = copy.deepcopy(load_fixture("api_response_ext_zx.json"))
    data["error"] = {}
    entry = await _setup(hass, data)
    registry = er.async_get(hass)
    fan_id = registry.async_get_entity_id("sensor", DOMAIN, "pellematic_pe1_L_fluegas")
    modulation_id = registry.async_get_entity_id("sensor", DOMAIN, "pellematic_pe1_L_modulation")
    assert await hass.config_entries.async_unload(entry.entry_id)

    hour = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    fans = [41.0] * 40 + [60.0] * 3  # clean for weeks, fouled in the last hours
    for statistic_id, values in ((fan_id, fans), (modulation_id, [100.0] * len(fans))):
        async_import_statistics(
            hass,
            {
                "has_mean": True,
                "mean_type": StatisticMeanType.ARITHMETIC,
                "has_sum": False,
                "name": None,
                "source": "recorder",
                "statistic_id": statistic_id,
                "unit_class": None,
                "unit_of_measurement": "%",
            },
            [
                {"start": hour - timedelta(hours=len(values) - i), "mean": v, "min": v, "max": v}
                for i, v in enumerate(values)
            ],
        )
    await async_wait_recording_done(hass)

    with patch(FETCH, return_value=data):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)

    index = hass.states.get("sensor.pellematic_pe1_flue_gas_index")
    assert index.attributes["baseline_source"] == "history"
    assert index.attributes["baseline"] == 41.0
    assert float(index.state) == pytest.approx(146.3, abs=0.1)
    assert hass.states.get("sensor.pellematic_diagnosis").state == "cleaning_due"
    assert await hass.config_entries.async_unload(entry.entry_id)
