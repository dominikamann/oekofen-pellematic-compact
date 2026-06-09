"""Repairs platform for Ökofen Pellematic Compact.

Surfaces a fixable issue when binary sensors are still registered under the
``sensor.*`` domain (legacy from versions that registered them on the wrong
platform). The fix flow lets the user confirm, deletes the orphan registry
entries, and reloads the config entry so ``binary_sensor.py`` recreates them
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

_LOGGER = logging.getLogger(__name__)


class FixLegacyBinarySensorsFlow(RepairsFlow):
    """Delete orphan sensor.* entries and reload the entry."""

    def __init__(self, entry_id: str, entity_ids: list[str]) -> None:
        self._entry_id = entry_id
        self._entity_ids = entity_ids

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            entity_reg = er.async_get(self.hass)
            removed = 0
            for entity_id in self._entity_ids:
                ent = entity_reg.async_get(entity_id)
                if ent is None or ent.config_entry_id != self._entry_id:
                    continue
                entity_reg.async_remove(entity_id)
                removed += 1
            _LOGGER.info(
                "Repairs: removed %d orphan sensor.* entries; reloading entry %s",
                removed, self._entry_id,
            )
            await self.hass.config_entries.async_reload(self._entry_id)
            return self.async_create_entry(data={})

        # Reuse the placeholders set on the issue (entity_list).
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
    entity_ids = (data or {}).get("entity_ids", [])
    return FixLegacyBinarySensorsFlow(entry_id, entity_ids)
