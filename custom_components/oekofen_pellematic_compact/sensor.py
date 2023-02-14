"""The Ökofen Pellematic Compact integration."""

import logging
from typing import Optional, Dict, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from .const import (
    CONF_NUM_OF_HEATING_CIRCUIT,
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
    PE1_SENSOR_TYPES,
    PU1_SENSOR_TYPES,
    WW1_BINARY_SENSOR_TYPES,
    WW1_SENSOR_TYPES,
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
    cirulator = entry.data[CONF_CIRCULATOR]

    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
    }

    entities = []

    for sensor_info in SYSTEM_SENSOR_TYPES.values():
        sensor = PellematicSensor(
            hub_name,
            hub,
            device_info,
            "system",
            sensor_info[0],
            sensor_info[1],
            sensor_info[2],
            sensor_info[3],
        )
        entities.append(sensor)

    for sensor_info in SYSTEM_BINARY_SENSOR_TYPES.values():
        sensor = PellematicBinarySensor(
            hub_name,
            hub,
            device_info,
            "system",
            sensor_info[0],
            sensor_info[1],
            sensor_info[2],
            sensor_info[3],
        )
        entities.append(sensor)

    i = 1
    while i <= num_heating_circuit:
        for sensor_info in HK_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name,
                hub,
                device_info,
                ("hk" + str(i)),
                sensor_info[0].format(" " + str(i)),
                sensor_info[1],
                sensor_info[2],
                sensor_info[3],
            )
            entities.append(sensor)

        for sensor_info in HK_BINARY_SENSOR_TYPES.values():
            sensor = PellematicBinarySensor(
                hub_name,
                hub,
                device_info,
                ("hk" + str(i)),
                sensor_info[0].format(" " + str(i)),
                sensor_info[1],
                sensor_info[2],
                sensor_info[3],
            )
            entities.append(sensor)
        i += 1
        
    if cirulator is True:
        for sensor_info in CIRC1_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name,
                hub,
                device_info,
                "circ1",
                sensor_info[0],
                sensor_info[1],
                sensor_info[2],
                sensor_info[3],
            )
            entities.append(sensor)

    if solar_circuit is True:
        for sensor_info in SK1_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name,
                hub,
                device_info,
                "sk1",
                sensor_info[0],
                sensor_info[1],
                sensor_info[2],
                sensor_info[3],
            )
            entities.append(sensor)

        for sensor_info in SK1_BINARY_SENSOR_TYPES.values():
            sensor = PellematicBinarySensor(
                hub_name,
                hub,
                device_info,
                "sk1",
                sensor_info[0],
                sensor_info[1],
                sensor_info[2],
                sensor_info[3],
            )
            entities.append(sensor)

        for sensor_info in SE1_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name,
                hub,
                device_info,
                "se1",
                sensor_info[0],
                sensor_info[1],
                sensor_info[2],
                sensor_info[3],
            )
            entities.append(sensor)

    for sensor_info in PE1_SENSOR_TYPES.values():
        sensor = PellematicSensor(
            hub_name,
            hub,
            device_info,
            "pe1",
            sensor_info[0],
            sensor_info[1],
            sensor_info[2],
            sensor_info[3],
        )
        entities.append(sensor)

    for sensor_info in PU1_SENSOR_TYPES.values():
        sensor = PellematicSensor(
            hub_name,
            hub,
            device_info,
            "pu1",
            sensor_info[0],
            sensor_info[1],
            sensor_info[2],
            sensor_info[3],
        )
        entities.append(sensor)

    for sensor_info in WW1_SENSOR_TYPES.values():
        sensor = PellematicSensor(
            hub_name,
            hub,
            device_info,
            "ww1",
            sensor_info[0],
            sensor_info[1],
            sensor_info[2],
            sensor_info[3],
        )
        entities.append(sensor)

    for sensor_info in WW1_BINARY_SENSOR_TYPES.values():
        sensor = PellematicBinarySensor(
            hub_name,
            hub,
            device_info,
            "ww1",
            sensor_info[0],
            sensor_info[1],
            sensor_info[2],
            sensor_info[3],
        )
        entities.append(sensor)

    for sensor_info in PU1_BINARY_SENSOR_TYPES.values():
        sensor = PellematicBinarySensor(
            hub_name,
            hub,
            device_info,
            "pu1",
            sensor_info[0],
            sensor_info[1],
            sensor_info[2],
            sensor_info[3],
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
