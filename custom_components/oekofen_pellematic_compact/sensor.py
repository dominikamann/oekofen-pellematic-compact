"""The Ökofen Pellematic Compact integration."""

import logging
from typing import Optional, Dict, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from .const import (
    CONF_NUM_OF_HEATING_CIRCUIT,
    CONF_NUM_OF_HOT_WATER,
    CONF_NUM_OF_PELLEMATIC_HEATER,
    CONF_SOLAR_CIRCUIT,
    CONF_CIRCULATOR,
    HK_BINARY_SENSOR_TYPES,
    PU1_BINARY_SENSOR_TYPES,
    SYSTEM_SENSOR_TYPES,
    SYSTEM_BINARY_SENSOR_TYPES,
    HK_SENSOR_TYPES,
    SE1_SENSOR_TYPES,
    SK1_BINARY_SENSOR_TYPES,
    SK1_SENSOR_TYPES,
    PE_SENSOR_TYPES,
    PU1_SENSOR_TYPES,
    WW_BINARY_SENSOR_TYPES,
    WW_SENSOR_TYPES,
    CIRC1_SENSOR_TYPES,
    DOMAIN,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
)

from homeassistant.const import (
    CONF_NAME,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfMass,
    UnitOfTime,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)

from homeassistant.core import callback
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup entry"""

    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]
    num_heating_circuit = entry.data[CONF_NUM_OF_HEATING_CIRCUIT]
    solar_circuit = entry.data[CONF_SOLAR_CIRCUIT]
    cirulator = False
    
    # For already existing users it could be that the keys does not exists
    try:
        cirulator = entry.data[CONF_CIRCULATOR]
    except:
        cirulator = False
    try:
        num_hot_water = entry.data[CONF_NUM_OF_HOT_WATER]
    except:
        num_hot_water = 1
    try:
        num_pellematic_heater = entry.data[CONF_NUM_OF_PELLEMATIC_HEATER]
    except:
        num_pellematic_heater = 1
        


    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
    }

    entities = []

    for name, key, unit, icon in SYSTEM_SENSOR_TYPES.values():
        sensor = PellematicSensor(
            hub_name, hub, device_info, "system", name, key, unit, icon
        )
        entities.append(sensor)

    for name, key, unit, icon in SYSTEM_BINARY_SENSOR_TYPES.values():
        sensor = PellematicBinarySensor(
            hub_name, hub, device_info, "system", name, key, unit, icon
        )
        entities.append(sensor)

    for heating_cir_count in range(num_heating_circuit):
        for name, key, unit, icon in HK_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name,
                hub,
                device_info,
                f"hk{heating_cir_count +1}",
                name.format(" " + str(heating_cir_count +1)),
                key,
                unit,
                icon,
            )
            entities.append(sensor)

        for name, key, unit, icon in HK_BINARY_SENSOR_TYPES.values():
            sensor = PellematicBinarySensor(
                hub_name,
                hub,
                device_info,
                f"hk{heating_cir_count +1}",
                name.format(" " + str(heating_cir_count +1)),
                key,
                unit,
                icon,
            )
            entities.append(sensor)

    if cirulator is True:
        for name, key, unit, icon in CIRC1_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name, hub, device_info, "circ1", name, key, unit, icon
            )
            entities.append(sensor)

    if solar_circuit is True:
        for name, key, unit, icon in SK1_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name, hub, device_info, "sk1", name, key, unit, icon
            )
            entities.append(sensor)

        for name, key, unit, icon in SK1_BINARY_SENSOR_TYPES.values():
            sensor = PellematicBinarySensor(
                hub_name, hub, device_info, "sk1", name, key, unit, icon
            )
            entities.append(sensor)

        for name, key, unit, icon in SE1_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name, hub, device_info, "se1", name, key, unit, icon
            )
            entities.append(sensor)

    for pe_count in range(num_pellematic_heater):
        for name, key, unit, icon in PE_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name,
                hub,
                device_info,
                f"pe{pe_count+1}",
                name.format(" " + str(pe_count+1)),
                key,
                unit,
                icon,
            )
            entities.append(sensor)
        
    for name, key, unit, icon in PU1_SENSOR_TYPES.values():
        sensor = PellematicSensor(
            hub_name,
            hub,
            device_info,
            "pu1",
            name,
            key,
            unit,
            icon,
        )
        entities.append(sensor)
        
    for name, key, unit, icon in PU1_BINARY_SENSOR_TYPES.values():
        sensor = PellematicBinarySensor(
            hub_name,
            hub,
            device_info,
            "pu1",
            name,
            key,
            unit,
            icon,
        )
        entities.append(sensor)


    for hot_water_count in range(num_hot_water):
        for name, key, unit, icon in WW_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name,
                hub,
                device_info,
                f"ww{hot_water_count+1}",
                name.format(" " + str(hot_water_count+1)),
                key,
                unit,
                icon,
            )
            entities.append(sensor)

        for name, key, unit, icon in WW_BINARY_SENSOR_TYPES.values():
            sensor = PellematicBinarySensor(
                hub_name,
                hub,
                device_info,
                f"ww{hot_water_count+1}",
                name.format(" " + str(hot_water_count+1)),
                key,
                unit,
                icon,
            )
            entities.append(sensor)

    for error_count in range(1, 6):
        sensor = PellematicSensor(
            hub_name,
            hub,
            device_info,
            "error",
            f"Error {error_count}",
            f"error_{error_count}",
            None,
            "mdi:alert-circle",
        )
        entities.append(sensor)

    async_add_entities(entities)

    return True


class PellematicBinarySensor(BinarySensorEntity):
    """Representation of a binary sensor entity."""

    def __init__(self, platform_name, hub, device_info, prefix, name, key, unit, icon):
        """Initialize the sensor."""
        self._platform_name = platform_name
        self._hub = hub
        self._prefix = prefix
        self._key = key
        self._name = name
        self._unit_of_measurement = unit
        self._icon = icon
        self._device_info = device_info
        self._attr_device_class = BinarySensorDeviceClass.POWER
        if icon == "mdi:usb-flash-drive":
            self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @callback
    def _api_data_updated(self):
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        current_value = None
        try:
            current_value = self._hub.data[self._prefix][self._key]
        except:
            return current_value
        return current_value

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._hub.async_add_pellematic_sensor(self._api_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_pellematic_sensor(self._api_data_updated)

    @callback
    def _api_data_updated(self):
        self.async_write_ha_state()

    @callback
    def _update_state(self):
        current_value = None
        try:
            current_value = self._hub.data[self._prefix][self._key]
        except:
            self._attr_is_on = current_value
        self._attr_is_on = current_value

    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

    @property
    def unique_id(self) -> Optional[str]:
        return f"{self._platform_name}_{self._prefix}_{self._key}"

    @property
    def icon(self):
        """Return the sensor icon."""
        return self._icon

    @property
    def extra_state_attributes(self):
        return None

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return False

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._device_info


class PellematicSensor(SensorEntity):
    """Representation of an Pellematic sensor."""

    def __init__(self, platform_name, hub, device_info, prefix, name, key, unit, icon):
        """Initialize the sensor."""
        self._platform_name = platform_name
        self._hub = hub
        self._prefix = prefix
        self._key = key
        self._name = name
        self._unit_of_measurement = unit
        self._icon = icon
        self._device_info = device_info
        if self._unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_last_reset = dt_util.utc_from_timestamp(0)
        if self._unit_of_measurement == UnitOfTemperature.CELSIUS:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if self._unit_of_measurement == UnitOfMass.KILOGRAMS:
            self._attr_device_class = SensorDeviceClass.WEIGHT
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if self.unit_of_measurement == PERCENTAGE:
            self._attr_device_class = SensorDeviceClass.POWER_FACTOR
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if self.unit_of_measurement == UnitOfTime.HOURS:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        if self.unit_of_measurement == UnitOfTime.MINUTES:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if self.unit_of_measurement == UnitOfTime.SECONDS:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if self.unit_of_measurement == UnitOfTime.MILLISECONDS:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = SensorStateClass.MEASUREMENT

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._hub.async_add_pellematic_sensor(self._api_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_pellematic_sensor(self._api_data_updated)

    @callback
    def _api_data_updated(self):
        self.async_write_ha_state()

    @callback
    def _update_state(self):
        current_value = None
        try:
            current_value = self._hub.data[self._prefix][self._key]
            if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
                current_value = int(current_value) / 10
        except:
            self._state = current_value
        self._state = current_value

    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

    @property
    def unique_id(self) -> Optional[str]:
        return f"{self._platform_name}_{self._prefix}_{self._key}"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the sensor icon."""
        return self._icon

    @property
    def state(self):
        """Return the state of the sensor."""
        current_value = None
        try:
            current_value = self._hub.data[self._prefix][self._key]
            if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
                current_value = int(current_value) / 10
        except:
            return current_value
        return current_value

    @property
    def extra_state_attributes(self):
        return None

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return False

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._device_info
