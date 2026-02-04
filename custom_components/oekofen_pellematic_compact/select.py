"""Demo platform that offers a fake select entity."""

from __future__ import annotations
import logging
from typing import Any, Optional

from homeassistant.components.select import SelectEntity

from .const import (
    DOMAIN,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
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

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform using dynamic discovery."""
    from datetime import timedelta
    from homeassistant.helpers.event import async_track_time_interval
    
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    _LOGGER.debug("Setup entry %s %s", hub_name, hub)
    
    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
    }
    
    # Track which entities have been added to avoid duplicates
    added_entity_ids = set()
    
    async def setup_entities_from_data():
        """Discover and add entities from current API data."""
        entities = []
        
        # Discover all entities dynamically from API data
        data = await hub.async_get_data()
        
        if not data:
            _LOGGER.debug("No API data available yet for select discovery")
            return False
        
        try:
            discovered = discover_all_entities(data)
            
            _LOGGER.info("Dynamically discovered %d select entities", len(discovered['selects']))
            
            # Create select entities with error handling
            for select_def in discovered['selects']:
                entity_id = f"{select_def['component']}_{select_def['key']}"
                if entity_id in added_entity_ids:
                    continue
                    
                try:
                    select = PellematicSelect(
                        hub_name=hub_name,
                        hub=hub,
                        device_info=device_info,
                        select_definition=select_def,
                    )
                    entities.append(select)
                    added_entity_ids.add(entity_id)
                except Exception as e:
                    _LOGGER.error("Failed to create select %s: %s", entity_id, e)
            
            if entities:
                _LOGGER.debug("Adding %i new select entities", len(entities))
                async_add_entities(entities)
                return True
            else:
                _LOGGER.debug("No new select entities to add")
                return False
                
        except Exception as e:
            _LOGGER.error("Error during select discovery: %s", e)
            return False
    
    # Try initial setup
    success = await setup_entities_from_data()
    
    if not success:
        _LOGGER.warning(
            "Initial select setup incomplete. Will retry every 60 seconds until successful. "
            "You can also manually trigger rediscovery using the 'oekofen_pellematic_compact.rediscover_components' service."
        )
        
        # Set up retry mechanism - try again every 60 seconds until successful
        async def retry_setup(now):
            """Retry entity setup periodically."""
            success = await setup_entities_from_data()
            if success:
                _LOGGER.info("Select entity setup completed successfully after retry")
                # Cancel further retries
                if hasattr(retry_setup, 'cancel'):
                    retry_setup.cancel()
        
        # Track the interval so we can cancel it later
        retry_setup.cancel = async_track_time_interval(
            hass, retry_setup, timedelta(seconds=60)
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
        self._attr_object_id = f"{self._prefix}_{self._key}"
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
            # Send the new option value to the API
            await self.hass.async_add_executor_job(
                self._hub.send_pellematic_data,
                option[:1],
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
        try:
            raw_data = self._hub.data[self._prefix][self._key.replace("#2", "")]
            current_value = raw_data["val"]
            return self._attr_options[int(current_value)]
        except:
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
        raise AttributeError

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""                
        return self._attr_current_option

