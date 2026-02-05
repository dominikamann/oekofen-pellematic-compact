"""Demo platform that offers a fake number entity."""

from __future__ import annotations
import logging
from typing import Any, Optional, Dict

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode

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
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    _LOGGER.debug("Setup entry %s %s", hub_name, hub)
    
    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
    }
    
    def create_number_entities(data: Dict[str, Any]) -> list:
        """Factory function to create number entities from discovery data."""
        entities = []
        discovered = discover_all_entities(data)
        
        _LOGGER.info("Dynamically discovered %d number entities", len(discovered['numbers']))
        
        # Create number entities with error handling
        for number_def in discovered['numbers']:
            try:
                number = PellematicNumber(
                    hub_name=hub_name,
                    hub=hub,
                    device_info=device_info,
                    number_definition=number_def,
                )
                number._entity_id_key = f"{number_def['component']}_{number_def['key']}"
                entities.append(number)
            except Exception as e:
                _LOGGER.error("Failed to create number %s_%s: %s", 
                            number_def['component'], number_def['key'], e)
        
        return entities
    
    # Use common setup logic with retry mechanism
    from . import setup_platform_with_retry
    await setup_platform_with_retry(
        hass, hub, hub_name, device_info, "number",
        create_number_entities, async_add_entities
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
        # Store conversion factor - ensure it's a float, not a string
        factor_value = number_definition.get('factor', 1)
        self._factor = float(factor_value) if not isinstance(factor_value, (int, float)) else factor_value
        
        _LOGGER.debug(
            "Adding dynamic PellematicNumber: %s, %s, min=%s, max=%s, step=%s, factor=%s",
            self._name,
            self._attr_unique_id,
            self._attr_native_min_value,
            self._attr_native_max_value,
            self._attr_native_step,
            self._factor,
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
            # Apply factor to convert display value to API value
            # Example: User sets 58.0°C, factor is 0.1, send 580 to API
            send_value = int(value / self._factor) if self._factor != 1 else int(value)
            
            _LOGGER.debug(
                "Setting %s: display_value=%s, factor=%s, api_value=%s",
                self.entity_id, value, self._factor, send_value
            )
            
            # Send the new value to the API
            await self.hass.async_add_executor_job(
                self._hub.send_pellematic_data,
                send_value,
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
            api_value = get_api_value(raw_data)
            
            # Convert API value to float first (handles both string and numeric types)
            numeric_value = float(api_value) if not isinstance(api_value, (int, float)) else api_value
            
            # Apply factor to convert API value to display value
            # Example: API sends 580, factor is 0.1, display 58.0°C
            if self._factor != 1:
                display_value = float(numeric_value) * self._factor
            else:
                display_value = numeric_value
            
            # Return as int if it's a whole number, otherwise as float
            if isinstance(display_value, float) and display_value.is_integer():
                return int(display_value)
            return display_value
        except Exception as e:
            _LOGGER.debug("Error updating value for %s: %s", self.entity_id, e)
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

