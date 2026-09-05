"""Repairs platform for Ökofen Pellematic Compact.

Surfaces a fixable issue when binary sensors are still registered under the
``sensor.*`` domain (legacy from versions that registered them on the wrong
platform). The fix flow lets the user confirm; it then deletes the orphan
registry entries and schedules a reload so ``binary_sensor.py`` recreates them
under the right domain.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .migration import _looks_like_legacy_binary_sensor, get_api_data_for_entry

_LOGGER = logging.getLogger(__name__)


class FixLegacyBinarySensorsFlow(RepairsFlow):
    """Delete orphan sensor.* entries and schedule a reload."""

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if not self._entry_id:
            # Issue data was lost (e.g. clicked Fix in the narrow window after
            # restart but before async_setup_entry re-populated the issue data).
            return self.async_abort(reason="missing_data")
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            # Look up orphans fresh from the registry on submit. Avoids stale
            # data captured at issue-creation time (the orphan list can shift
            # between sessions) and re-applies the same heuristic the issue was
            # raised from, so we never delete something the heuristic wouldn't
            # currently flag.
            entity_reg = er.async_get(self.hass)
            registry_entries = er.async_entries_for_config_entry(
                entity_reg, self._entry_id
            )
            # Same API-aware verdict the issue was raised from — without it the
            # flow would delete healthy modulation-pump sensors that discovery
            # then recreates, looping the repair forever.
            config_entry = self.hass.config_entries.async_get_entry(self._entry_id)
            api_data = (
                get_api_data_for_entry(self.hass, config_entry)
                if config_entry
                else None
            )
            orphans = [
                ent
                for ent in registry_entries
                if ent.domain == "sensor"
                and _looks_like_legacy_binary_sensor(ent.entity_id, api_data)
            ]

            for ent in orphans:
                entity_reg.async_remove(ent.entity_id)

            _LOGGER.info(
                "Repairs: removed %d orphan sensor.* entries; scheduling reload of %s",
                len(orphans), self._entry_id,
            )
            # Scheduled (not awaited) reload — releases the flow immediately
            # and cancels any in-flight setup-retry timer to avoid races.
            self.hass.config_entries.async_schedule_reload(self._entry_id)
            return self.async_create_entry(data={})

        issue_reg = ir.async_get(self.hass)
        placeholders = None
        if issue := issue_reg.async_get_issue(self.handler, self.issue_id):
            placeholders = issue.translation_placeholders

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders=placeholders,
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Entry point HA calls when the user clicks 'Fix' on the Repairs issue."""
    entry_id = (data or {}).get("entry_id", "")
    return FixLegacyBinarySensorsFlow(entry_id)
