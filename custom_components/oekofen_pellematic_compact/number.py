"""Demo platform that offers a fake number entity."""

from __future__ import annotations
import logging

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode

from .const import (
    CONF_NUM_OF_HEATING_CIRCUIT,
    CONF_NUM_OF_HOT_WATER,
    HK_NUMBER_TYPES,
    WW_NUMBER_TYPES,
    DOMAIN,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
)

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
    """Set up the number platform."""
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]
    
    try:
        num_heating_circuit = entry.data[CONF_NUM_OF_HEATING_CIRCUIT]
    except:
        num_heating_circuit = 1
    try:
        num_hot_water = entry.data[CONF_NUM_OF_HOT_WATER]
    except:
        num_hot_water = 1

    _LOGGER.debug("Setup entry %s %s", hub_name, hub)
    
    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
    }
    
    entities = []
    
    
    for heating_cir_count in range(num_heating_circuit):

        for name, key, device_class, unit, tmin, tmax, tstep  in HK_NUMBER_TYPES.values():
            number = PellematicNumber(
                hub_name,
                hub,
                device_info,
                f"hk{heating_cir_count +1}",
                name.format(" " + str(heating_cir_count + 1)),
                key,
                device_class=device_class,
                mode=NumberMode.SLIDER,
                native_min_value=tmin,
                native_max_value=tmax,
                native_step=tstep,
                native_unit_of_measurement=unit
            )
            entities.append(number)    
    for hot_water_count in range(num_hot_water):
        for name, key, device_class, unit, tmin, tmax, tstep in WW_NUMBER_TYPES.values():
            number = PellematicNumber(
                hub_name,
                hub,
                device_info,
                f"ww{hot_water_count +1}",
                name.format(" " + str(hot_water_count + 1)),
                key,
                device_class=device_class,
                mode=NumberMode.SLIDER,
                native_min_value=tmin,
                native_max_value=tmax,
                native_step=tstep,
                native_unit_of_measurement=unit
            )
            entities.append(number)
    
    _LOGGER.debug("Entities added : %i", len(entities))
    
    async_add_entities(entities)


class PellematicNumber(NumberEntity):
    """Representation of a number entity."""
    
    #_attr_has_entity_name = True
    #_attr_name = None
    #_attr_should_poll = False

    def __init__(
        self,
        platform_name,
        hub,
        device_info,
        prefix,
        name,
        key,
        *,
        device_class: NumberDeviceClass | None = None,
        mode: NumberMode = NumberMode.AUTO,
        native_min_value: float | None = None,
        native_max_value: float | None = None,
        native_step: float | None = None,
        native_unit_of_measurement: str | None = None,
    ) -> None:
        """Initialize the number."""
        self._platform_name = platform_name
        self._hub = hub        
        self._prefix = prefix
        self._key = key
        self._name = f"{self._platform_name} {name}"
        self._attr_unique_id = f"{self._platform_name.lower()}_{self._prefix}_{self._key}"
        self._device_info = device_info
        self._attr_assumed_state = False
        self._state = None
        self._attr_device_class = device_class
        self._attr_mode = mode
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_native_min_value = native_min_value
        self._attr_native_max_value = native_max_value
        self._attr_native_step = native_step
        self._attr_native_value = None
        
        _LOGGER.debug(
            "Adding a PellematicNumber : %s, %s, %s, %s, %s, %s, %s, %s, %s",
            str(self._platform_name),
            str(self._hub),
            str(self._prefix),
            str(self._key),
            str(self._name),
            str(self._attr_unique_id),
            str(self._attr_native_value),
            str(self._attr_mode),
            str(self._device_info),
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
        self._attr_native_value = value
        if self._attr_device_class == NumberDeviceClass.TEMPERATURE:
                value = int(value * 10)
        await self.hass.async_add_executor_job(
            self._hub.send_pellematic_data,
            value,
            self._prefix,
            self._key
        )
        self.async_write_ha_state()

    def _update_native_value(self):
        try:
            current_value = self._hub.data[self._prefix][self._key]
            if self._attr_device_class == NumberDeviceClass.TEMPERATURE:
                return int(current_value) / 10
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
    def native_step(self) -> float | None:
        """Return the increment/decrement step."""
        return self._attr_native_step

    @property
    def mode(self) -> NumberMode:
        """Return the mode of the entity."""
        return self._attr_mode


    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of the entity, if any."""
        return self._attr_native_unit_of_measurement

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the number."""
        return self._attr_native_value
