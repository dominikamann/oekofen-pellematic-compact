"""Regression: translated legacy IDs must be resolved to their real API key
(issue #192).

Pre-4.0 entity IDs embedded the slugified *display text*, not the raw API key.
On a French installation ``pu1.L_pump_release`` ("T démarrage pompe") became

    sensor.chaudiere_buffer_storage_1_t_demarrage_pompe

which ends in the translated suffix ``_pompe`` although the datapoint is a
``°C`` temperature. The repair flagged it, deleted it, discovery recreated the
identical ``sensor.*``, and the issue came back on every reload.

The API-aware check introduced for the modulation pumps did not catch this
because it only accepted IDs of the shape ``{component_slug}{suffix}`` — here
the text words ``t_demarrage`` sit in between, so resolution bailed out and
the name-only verdict (True) won.
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
from tests.conftest import load_fixture

FIXTURE = "api_response_fr_404b.json"


@pytest.fixture(name="api_data")
def api_data_fixture():
    return load_fixture(FIXTURE)


@pytest.mark.parametrize(
    "entity_id,expected",
    [
        # The exact ID from the report (English component slug + French text).
        ("sensor.chaudiere_buffer_storage_1_t_demarrage_pompe", False),
        # Same datapoint with the French component slug, and with the raw key.
        ("sensor.chaudiere_ballon_tampon_1_t_demarrage_pompe", False),
        ("sensor.chaudiere_pu1_l_pump_release", False),
        # pu1.L_pump is a modulation percentage ("Vit Rot") — still no orphan.
        ("sensor.chaudiere_pu1_l_pump", False),
        # hk1.L_pump is a genuine on/off pump ("Chf Pompe") — must stay flagged
        # via both the raw key and the translated text.
        ("sensor.chaudiere_hk1_l_pump", True),
        ("sensor.chaudiere_hk1_chf_pompe", True),
        ("sensor.chaudiere_heating_circuit_1_chf_pompe", True),
        # Other genuine binary sensors of this firmware.
        ("sensor.chaudiere_pe1_l_stb", True),
        ("sensor.chaudiere_system_l_usb_stick", True),
    ],
)
def test_translated_id_resolves_to_its_api_key(api_data, entity_id, expected):
    assert _looks_like_legacy_binary_sensor(entity_id, api_data) is expected


async def test_refresh_does_not_flag_translated_temperature(hass, api_data):
    """End-to-end: the reported entity raises no Repairs issue, so the
    fix/recreate/flag loop cannot start."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={"name": "Chaudiere"})
    config_entry.add_to_hass(hass)

    entity_reg = er.async_get(hass)
    entity_reg.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="chaudiere_pu1_L_pump_release",
        config_entry=config_entry,
        suggested_object_id="chaudiere_buffer_storage_1_t_demarrage_pompe",
    )

    class _Hub:
        data = api_data

    hass.data.setdefault(DOMAIN, {})["Chaudiere"] = {"hub": _Hub()}

    with patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as ir_create, patch(
        "homeassistant.helpers.issue_registry.async_delete_issue"
    ) as ir_delete:
        count = await async_refresh_legacy_binary_sensor_repair_issue(
            hass, config_entry
        )

    assert count == 0
    ir_create.assert_not_called()
    ir_delete.assert_called_once()


@pytest.mark.parametrize(
    "entity_id",
    [
        # Writable two-option fields: `is_binary_sensor()` says True, but
        # discovery creates *selects* for them because they have no `L_` prefix.
        # Reporting them as binary-sensor orphans would delete a working select.
        "sensor.chaudiere_ww1_heat_once",
        "sensor.chaudiere_ecs_1_charge_ecs",          # ww1.heat_once, FR text
        "sensor.chaudiere_ww1_use_boiler_heat",
        "sensor.chaudiere_hk1_time_prg",
        "sensor.chaudiere_weather_oekomode",
        "sensor.chaudiere_hk1_mode_auto",
        # Plain temperatures/counters of the same fixture.
        "sensor.chaudiere_pe1_l_temp_act",
        "sensor.chaudiere_pe1_l_storage_fill",
    ],
)
def test_writable_and_plain_fields_are_never_flagged(api_data, entity_id):
    assert _looks_like_legacy_binary_sensor(entity_id, api_data) is False


def test_translated_text_outside_the_suffix_list_is_still_detected():
    """Resolving via the API also *widens* detection: a genuine `L_` binary key
    whose localized text nobody added to _LEGACY_BINARY_KEY_SUFFIXES used to be
    invisible to the repair, leaving the orphan sensor.* entry forever."""
    api_data = load_fixture("api_response_base_csta.json")

    # pe1.L_br, German text "Brennerkontakt" — no matching suffix in the list.
    assert (
        _looks_like_legacy_binary_sensor(
            "sensor.pellematic_pellematic_1_brennerkontakt", api_data
        )
        is True
    )
    # system.L_usb_stick, text "Usb Stick erkannt".
    assert (
        _looks_like_legacy_binary_sensor(
            "sensor.pellematic_system_usb_stick_erkannt", api_data
        )
        is True
    )
    # ...while a plain sensor of the same fixture stays untouched.
    assert (
        _looks_like_legacy_binary_sensor(
            "sensor.pellematic_pe1_l_temp_act", api_data
        )
        is False
    )
