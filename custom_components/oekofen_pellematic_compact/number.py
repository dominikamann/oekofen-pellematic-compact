"""Demo platform that offers a fake number entity."""

from __future__ import annotations
import logging
from typing import Any, Optional

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode

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
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform using dynamic discovery."""
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
            _LOGGER.debug("No API data available yet for number discovery")
            return False
        
        try:
            discovered = discover_all_entities(data)
            
            _LOGGER.info("Dynamically discovered %d number entities", len(discovered['numbers']))
            
            # Create number entities with error handling
            for number_def in discovered['numbers']:
                entity_id = f"{number_def['component']}_{number_def['key']}"
                if entity_id in added_entity_ids:
                    continue
                    
                try:
                    number = PellematicNumber(
                        hub_name=hub_name,
                        hub=hub,
                        device_info=device_info,
                        number_definition=number_def,
                    )
                    entities.append(number)
                    added_entity_ids.add(entity_id)
                except Exception as e:
                    _LOGGER.error("Failed to create number %s: %s", entity_id, e)
            
            if entities:
                _LOGGER.debug("Adding %i new number entities", len(entities))
                async_add_entities(entities)
                return True
            else:
                _LOGGER.debug("No new number entities to add")
                return False
                
        except Exception as e:
            _LOGGER.error("Error during number discovery: %s", e)
            return False
    
    # Try initial setup
    success = await setup_entities_from_data()
    
    if not success:
        _LOGGER.warning(
            "Initial number setup incomplete. Will retry every 60 seconds until successful. "
            "You can also manually trigger rediscovery using the 'oekofen_pellematic_compact.rediscover_components' service."
        )
        
        # Set up retry mechanism - try again every 60 seconds until successful
        async def retry_setup(now):
            """Retry entity setup periodically."""
            success = await setup_entities_from_data()
            if success:
                _LOGGER.info("Number entity setup completed successfully after retry")
                # Cancel further retries
                if hasattr(retry_setup, 'cancel'):
                    retry_setup.cancel()
        
        # Track the interval so we can cancel it later
        retry_setup.cancel = async_track_time_interval(
            hass, retry_setup, timedelta(seconds=60)
        )


class PellematicNumber(NumberEntity):
    """Representation of a number entity."""
    
    #_attr_has_entity_name = True
    #_attr_name = None
    #_attr_should_poll = False

    def __init__(
        self,
        hub_name,
        hub,
        device_info,
        number_definition,
    ) -> None:
        """Initialize the number from dynamic definition."""
        self._platform_name = hub_name
        self._hub = hub
        self._prefix = number_definition['component']
        self._key = number_definition['key']
        self._name = f"{self._platform_name} {number_definition['name']}"
        self._attr_unique_id = f"{self._platform_name.lower()}_{self._prefix}_{self._key}"
        # Use component_key for entity_id instead of long human-readable name
        self._attr_object_id = f"{self._prefix}_{self._key}"
        self._device_info = device_info
        self._attr_assumed_state = False
        self._state = None
        self._attr_device_class = number_definition.get('device_class')
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_unit_of_measurement = number_definition.get('unit')
        self._attr_native_min_value = number_definition.get('min', 0)
        self._attr_native_max_value = number_definition.get('max', 100)
        self._attr_native_step = number_definition.get('step', 0.5)
        self._attr_native_value = None
        
        _LOGGER.debug(
            "Adding dynamic PellematicNumber: %s, %s, min=%s, max=%s, step=%s",
            self._name,
            self._attr_unique_id,
            self._attr_native_min_value,
            self._attr_native_max_value,
            self._attr_native_step,
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

    async def async_set_native_value(self, value) -> None:
        """Update the native value."""
        try:
            # Prepare the value for sending
            send_value = value
            if self._attr_device_class == NumberDeviceClass.TEMPERATURE:
                send_value = int(value * 10)
            
            # Send the new value to the API
            await self.hass.async_add_executor_job(
                self._hub.send_pellematic_data,
                int(send_value),
                self._prefix,
                self._key
            )
            # Only update state if send was successful
            self._attr_native_value = value
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error(
                "Failed to set value '%s' for %s: %s",
                value,
                self.entity_id,
                err,
            )
            # Re-raise to let Home Assistant handle it properly
            raise

    def _update_native_value(self):
        try:
            raw_data = self._hub.data[self._prefix][self._key.replace("#2", "")]
            current_value = raw_data["val"]
            if self._attr_device_class == NumberDeviceClass.TEMPERATURE:
                return int(current_value) / 10
            if isinstance(current_value, float) and current_value.is_integer():
                return int(current_value)
            return float(current_value)
        except:
            return None

    @callback
    def _update_state(self):
        self._attr_native_value = self._update_native_value()
        
    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

    @property
    def state(self) -> float | None:
        """Return the entity state."""
        return self._attr_native_value

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return False
    
    @property
    def device_info(self) -> Optional[dict[str, Any]]:
        return self._device_info
        
    @property
    def device_class(self) -> NumberDeviceClass | None:
        """Return the class of this entity."""
        return self._attr_device_class

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return self._attr_native_min_value

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return self._attr_native_max_value
        
    @property
    def native_step(self) -> int | float | None:
        """Return the increment/decrement step."""
        step = self._attr_native_step
        if isinstance(step, float) and step.is_integer():
            return int(step)
        return step
        
    @property
    def mode(self) -> NumberMode:
        """Return the mode of the entity."""
        return self._attr_mode

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of the entity, if any."""
        return self._attr_native_unit_of_measurement

    @property
    def native_value(self) -> int | float | None:
        """Return the value reported by the number."""
        value = self._attr_native_value
        if isinstance(value, float) and value is not None and value.is_integer():
            # Nur wenn der Wert ein Float ist und ganzzahlig, dann als int zurückgeben
            return int(value)
        return value

