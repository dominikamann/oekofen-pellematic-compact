"""Demo platform that offers a fake select entity."""

from __future__ import annotations
import logging
from typing import Any, Optional, Dict

from homeassistant.components.select import SelectEntity

from .const import (
    DOMAIN,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    get_api_value,
)
from .dynamic_discovery import discover_all_entities

from homeassistant.const import (
    CONF_NAME,
)
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

# Boolean spellings old firmware uses instead of 0/1 (e.g. ww1.heat_once).
_BOOLEAN_OPTION_VALUES = {"false": "0", "true": "1"}


def _options_carry_value_prefix(options) -> bool:
    """True when the options were built from "value:label" pairs.

    `parse_select_options` also accepts a `format` without any colon
    ("Aus|Auto|Ein"), and `is_select` creates a select for it. Those options
    carry no value, so the API value can only be a position in the list.
    No known firmware sends that shape -- none of the test fixtures contains
    one -- but silently reporting `unknown` forever would be worse than the
    positional guess it used to make.
    """
    return any(
        option.split("_", 1)[0].lstrip("-").isdigit() for option in options or ()
    )


def _api_value_as_option_prefix(value) -> Optional[str]:
    """Normalize an API value to the prefix used in the option list.

    Handles the shapes real responses use for the same field: 1, "1", 1.0
    and "true". Returns None when the value carries no selection.
    """
    if value is None or isinstance(value, bool):
        return "1" if value is True else ("0" if value is False else None)

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.lower() in _BOOLEAN_OPTION_VALUES:
            return _BOOLEAN_OPTION_VALUES[text.lower()]
        try:
            value = float(text)
        except ValueError:
            return text

    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return str(value)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform using dynamic discovery."""
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    _LOGGER.debug("Setup entry %s %s", hub_name, hub)
    
    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
    }
    
    def create_select_entities(data: Dict[str, Any]) -> list:
        """Factory function to create select entities from discovery data."""
        entities = []
        discovered = discover_all_entities(data, hass.config.language)
        
        _LOGGER.info("Dynamically discovered %d select entities", len(discovered['selects']))
        
        # Create select entities with error handling
        for select_def in discovered['selects']:
            try:
                select = PellematicSelect(
                    hub_name=hub_name,
                    hub=hub,
                    device_info=device_info,
                    select_definition=select_def,
                )
                select._entity_id_key = f"{select_def['component']}_{select_def['key']}"
                entities.append(select)
            except Exception as e:
                _LOGGER.error("Failed to create select %s_%s: %s", 
                            select_def['component'], select_def['key'], e)
        
        return entities
    
    # Use common setup logic with retry mechanism
    from . import setup_platform_with_retry
    await setup_platform_with_retry(
        hass, hub, hub_name, device_info, "select",
        create_select_entities, async_add_entities
    )


class PellematicSelect(SelectEntity):
    """Representation of a select entity."""
    
    #_attr_has_entity_name = True
    #_attr_name = None
    #_attr_should_poll = False

    def __init__(
        self,
        hub_name,
        hub,
        device_info,
        select_definition,
    ) -> None:
        """Initialize the select from dynamic definition."""
        self._platform_name = hub_name
        self._hub = hub
        self._prefix = select_definition['component']
        self._key = select_definition['key']
        self._name = f"{self._platform_name} {select_definition['name']}"
        self._attr_unique_id = f"{self._platform_name.lower()}_{self._prefix}_{self._key}"
        # Use component_key for entity_id instead of long human-readable name
        self._attr_object_id = f"{self._prefix}_{self._key}".lower()
        self._attr_current_option = None
        self._attr_options = select_definition['options']
        self._device_info = device_info
        self._attr_translation_key = None
        
        _LOGGER.debug(
            "Adding dynamic PellematicSelect: %s, %s, options: %s",
            self._name,
            self._attr_unique_id,
            self._attr_options,
        )

    @callback
    def _api_data_updated(self):
        self._update_state()
        self.async_write_ha_state()        


    async def async_added_to_hass(self):
        """Register callbacks."""
        self._hub.async_add_pellematic_sensor(self._api_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_pellematic_sensor(self._api_data_updated)

    async def async_select_option(self, option) -> None:
        """Update the current selected option."""
        try:
            # Guard: reject unknown options before sending to the boiler.
            # An unrecognised value can configure a register (e.g. sensor_on/off)
            # to reference a physical sensor that does not exist, creating an
            # unacknowledgeable fault that requires a full factory reset to clear.
            if option not in self._attr_options:
                _LOGGER.error(
                    "Blocked write for %s: option '%s' is not in the valid option "
                    "list %s. Write rejected to protect boiler controller state.",
                    self.entity_id, option, self._attr_options,
                )
                return

            # Options are stored as "<index>_<label>" (e.g. "0_ecs", "10_buffer").
            # Extract only the numeric index prefix to send to the API.
            # Using option[:1] was wrong for multi-digit indices (>= 10).
            option_value = option.split("_", 1)[0]

            # Send the new option value to the API
            await self.hass.async_add_executor_job(
                self._hub.send_pellematic_data,
                option_value,
                self._prefix,
                self._key
            )
            # Only update state if send was successful
            self._attr_current_option = option
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error(
                "Failed to set option '%s' for %s: %s",
                option,
                self.entity_id,
                err,
            )
            # Re-raise to let Home Assistant handle it properly
            raise

    def _update_current_option(self):
        """Return the option the API value stands for, or None.

        Options are "<api value>_<label>", so the value is matched against
        each option's prefix -- it is NOT a position in the list. Indexing
        into the list made `autocomfort` = -1 (feature unavailable) show the
        last option, and it silently shifted every option after a gap in a
        format string like "0:Off|2:On|10:Buffer". This mirrors
        async_select_option(), which has always sent the prefix.
        """
        try:
            raw_data = self._hub.data[self._prefix][self._key.replace("#2", "")]
        except (KeyError, TypeError):
            return None

        wanted = _api_value_as_option_prefix(get_api_value(raw_data))
        if wanted is None:
            return None

        options = self._attr_options or ()

        if not _options_carry_value_prefix(options):
            # Valueless options: fall back to a position, but never let a
            # negative value wrap around to the end of the list.
            try:
                position = int(wanted)
            except ValueError:
                return None
            return options[position] if 0 <= position < len(options) else None

        for option in options:
            if option.split("_", 1)[0] == wanted:
                return option

        # A value outside the declared options means "not available" (or a
        # firmware we do not know); reporting nothing beats reporting a
        # neighbouring option as if it were the truth.
        _LOGGER.debug(
            "%s.%s: API value %r matches none of the options %s",
            self._prefix, self._key, wanted, options,
        )
        return None

    @callback
    def _update_state(self):
        self._attr_current_option = self._update_current_option()
        
    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

    @property
    def state(self):
        """Return the entity state."""
        return self._attr_current_option

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return False
    
    @property
    def device_info(self) -> Optional[dict[str, Any]]:
        return self._device_info

    @property
    def options(self) -> list[str]:
        """Return a set of selectable options."""
        return self._attr_options

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""                
        return self._attr_current_option

