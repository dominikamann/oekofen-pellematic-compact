"""Heating-curve seeding from the recorder's hourly statistics, in a running Home Assistant."""

import asyncio
import copy
import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.oekofen_pellematic_compact.const import (
    CONF_API_SUFFIX,
    CONF_CHARSET,
    CONF_OLD_FIRMWARE,
    DOMAIN,
)
from tests.conftest import load_fixture
from tests.unit.test_diagnosis_entities import FETCH, _poll, _setup

STATISTICS = "homeassistant.components.recorder.statistics.statistics_during_period"
OUTDOOR = [a for a in (-8, -6, -4, -2, 0, 2, 4, 6, 8, 10, 12, 14) for _ in range(6)]
FLOW_SET = [21 + 10 + (21 - a) for a in OUTDOOR]  # curve 1.0, offset 10, room set 21


def _data(fixture="api_response_ext_zx.json"):
    data = copy.deepcopy(load_fixture(fixture))
    data["error"] = {}
    return data


def _monitor(hass):
    return hass.data[DOMAIN]["Pellematic"]["diagnosis"]


def _stored(hass_storage, entry):
    curves = hass_storage[f"{DOMAIN}.diagnosis.{entry.entry_id}"]["data"]["curves"]
    return {name: curve["history_checked"] for name, curve in curves.items()}


async def _import(hass, statistic_id, values):
    from homeassistant.components.recorder.models import StatisticMeanType
    from homeassistant.components.recorder.statistics import async_import_statistics

    hour = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    async_import_statistics(
        hass,
        {
            "has_mean": True, "mean_type": StatisticMeanType.ARITHMETIC, "has_sum": False, "name": None,
            "source": "recorder", "statistic_id": statistic_id, "unit_class": "temperature",
            "unit_of_measurement": "°C",
        },
        [
            {"start": hour - timedelta(hours=len(values) - i), "mean": v, "min": v, "max": v}
            for i, v in enumerate(values)
        ],
    )


async def _import_history(hass, sources):
    """Three days of an unmixed circuit: the flow sits 6 K above its set point, the sources 10 K."""
    from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done

    registry = er.async_get(hass)

    def entity_id(component, key):
        found = registry.async_get_entity_id("sensor", DOMAIN, f"pellematic_{component}_{key}")
        assert found, (component, key)
        return found

    await _import(hass, entity_id("system", "L_ambient"), OUTDOOR)
    await _import(hass, entity_id("hk1", "L_roomtemp_set"), [21.0] * len(OUTDOOR))
    await _import(hass, entity_id("hk1", "L_flowtemp_set"), FLOW_SET)
    await _import(hass, entity_id("hk1", "L_flowtemp_act"), [f + 6 for f in FLOW_SET])
    for component, key, above in sources:
        await _import(hass, entity_id(component, key), [f + above for f in FLOW_SET])
    await async_wait_recording_done(hass)


@pytest.mark.parametrize(
    ("fixture", "sources"),
    [
        ("api_response_ext_zx.json", [("pu1", "L_tpo_act", 10)]),
        # Two buffers: the cooler one decides, and it is still hot.
        ("api_response_fren.json", [("pu1", "L_tpo_act", 30), ("pu2", "L_tpo_act", 10)]),
        # Boiler, heat pump and buffer: only the buffer is the source.
        ("api_response_base_csta.json", [("pu1", "L_tpo_act", 10)]),
    ],
)
async def test_curve_is_seeded_once_from_the_statistics(
    recorder_mock, hass, hass_storage, enable_custom_integrations, fixture, sources
):
    data = _data(fixture)
    entry = await _setup(hass, data)  # first start registers the entities; there is no history yet
    await hass.async_block_till_done(wait_background_tasks=True)
    assert _monitor(hass).diagnosis.curves["hk1"].history_checked is True
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # A later installation of the feature: entities and statistics exist, the curve state does not.
    hass_storage[f"{DOMAIN}.diagnosis.{entry.entry_id}"]["data"].pop("curves")
    await _import_history(hass, sources)
    with patch(FETCH, return_value=data):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)

    curve = _monitor(hass).diagnosis.curves["hk1"]
    assert curve.curve_status == "determined"
    assert curve.slope == pytest.approx(1.0, abs=0.01)
    assert curve.offset == pytest.approx(10.0, abs=0.1)
    assert curve.circuit_type == "unmixed"
    assert curve.flow_surplus == pytest.approx(6.0, abs=0.1)
    assert float(hass.states.get("sensor.pellematic_hk1_heating_curve_slope").state) == pytest.approx(1.0, abs=0.01)
    assert hass.states.get("sensor.pellematic_hk1_circuit_type").state == "unmixed"
    hours = curve.heating_hours

    # The next start must not replay the same weeks on top.
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    with patch(FETCH, return_value=data):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert _monitor(hass).diagnosis.curves["hk1"].heating_hours == pytest.approx(hours, abs=0.5)
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_unload_while_reading_does_not_mark_the_history_as_read(
    recorder_mock, hass, hass_storage, enable_custom_integrations
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "host": "http://192.0.2.1:4321/pw/all", "name": "Pellematic", CONF_CHARSET: "utf-8",
            CONF_API_SUFFIX: "?", CONF_OLD_FIRMWARE: False,
            "migration_notification_shown": True, "entity_id_warning_shown": True,
        },
    )
    entry.add_to_hass(hass)

    def slow(*args, **kwargs):
        time.sleep(0.5)
        return {}

    with patch(FETCH, return_value=_data()), patch(STATISTICS, slow):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await asyncio.sleep(0.05)
        assert not _monitor(hass)._curve_history_task.done()
        assert await hass.config_entries.async_unload(entry.entry_id)
        await asyncio.sleep(0.7)
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
        await hass.async_block_till_done(wait_background_tasks=True)
    assert _stored(hass_storage, entry) == {"hk1": False, "hk2": False}


async def test_circuits_that_appear_after_setup_are_seeded_too(
    recorder_mock, hass, hass_storage, enable_custom_integrations
):
    """The boiler was unreachable while Home Assistant started."""
    data = _data()
    entry = await _setup(hass, data)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    hass_storage[f"{DOMAIN}.diagnosis.{entry.entry_id}"]["data"].pop("curves")
    await _import_history(hass, [("pu1", "L_tpo_act", 10)])

    with patch(FETCH, side_effect=OSError("down")):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    monitor = _monitor(hass)
    assert monitor.diagnosis.curves == {}

    await _poll(hass, data)
    await hass.async_block_till_done(wait_background_tasks=True)
    curve = monitor.diagnosis.curves["hk1"]
    assert curve.history_checked is True
    assert curve.curve_status == "determined"
    assert curve.slope == pytest.approx(1.0, abs=0.01)
    with patch(FETCH, return_value=data):
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=61))  # let the setup retry finish
        await hass.async_block_till_done(wait_background_tasks=True)
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_seeding_reads_the_room_temperature_too(recorder_mock, hass, hass_storage, enable_custom_integrations):
    """A circuit with a room sensor: controller at slope 1.2, room influence 5."""
    from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done

    data = _data()
    entry = await _setup(hass, data)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    hass_storage[f"{DOMAIN}.diagnosis.{entry.entry_id}"]["data"].pop("curves")

    registry = er.async_get(hass)
    deviations = [[-0.6, 0.8, -0.4, 0.5, 0.1, -0.2, 0.3][i % 7] for i in range(len(OUTDOOR))]
    series = {
        ("system", "L_ambient"): OUTDOOR,
        ("hk1", "L_roomtemp_set"): [21.0] * len(OUTDOOR),
        ("hk1", "L_roomtemp_act"): [21.0 - d for d in deviations],
        ("hk1", "L_flowtemp_set"): [21 + 3 + 1.2 * (21 - a) + 5 * d for a, d in zip(OUTDOOR, deviations)],
    }
    series[("hk1", "L_flowtemp_act")] = series[("hk1", "L_flowtemp_set")]
    for (component, key), values in series.items():
        await _import(hass, registry.async_get_entity_id("sensor", DOMAIN, f"pellematic_{component}_{key}"), values)
    await async_wait_recording_done(hass)

    with patch(FETCH, return_value=data):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    curve = _monitor(hass).diagnosis.curves["hk1"]
    assert curve.curve_status == "determined"
    assert curve.slope == pytest.approx(1.2, abs=0.03)
    assert curve.room_influence == pytest.approx(5.0, abs=0.3)
    state = hass.states.get("sensor.pellematic_hk1_heating_curve_slope")
    assert state.attributes["room_influence"] == pytest.approx(5.0, abs=0.3)
    assert await hass.config_entries.async_unload(entry.entry_id)
