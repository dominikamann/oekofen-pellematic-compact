"""The Ökofen Pellematic Compact integration."""

import logging
from typing import Optional, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from .const import (
    CONF_NUM_OF_HEATING_CIRCUIT,
    CONF_NUM_OF_HOT_WATER,
    CONF_NUM_OF_PELLEMATIC_HEATER,
    CONF_NUM_OF_SMART_PV_SE,
    CONF_NUM_OF_SMART_PV_SK,
    CONF_SOLAR_CIRCUIT,
    CONF_CIRCULATOR,
    CONF_SMART_PV,
    CONF_STIRLING,
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
    POWER_SENSOR_TYPES,
    STIRLING_SENSOR_TYPES,
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
    UnitOfPower,
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
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup entry"""

    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]
    num_heating_circuit = entry.data[CONF_NUM_OF_HEATING_CIRCUIT]
    solar_circuit = entry.data[CONF_SOLAR_CIRCUIT]
    cirulator = False
    smart_pv = False
    stirling = False

    # For already existing users it could be that the keys does not exists
    try:
        stirling = entry.data[CONF_STIRLING]
    except:
        stirling = False
    try:
        smart_pv = entry.data[CONF_SMART_PV]
    except:
        smart_pv = False
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
    try:
        num_smart_pv_se = entry.data[CONF_NUM_OF_SMART_PV_SE]
    except:
        num_smart_pv_se = 1
    try:
        num_smart_pv_sk = entry.data[CONF_NUM_OF_SMART_PV_SK]
    except:
        num_smart_pv_sk = 1       
            
    _LOGGER.debug("Setup entry %s %s", hub_name, hub)

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
                name.format(" " + str(heating_cir_count + 1)),
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
                name.format(" " + str(heating_cir_count + 1)),
                key,
                unit,
                icon,
            )
            entities.append(sensor)
    
    if stirling is True:
        for name, key, unit, icon in STIRLING_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name,
                hub,
                device_info,
                "stirling",
                name,
                key,
                unit,
                icon,
            )
            entities.append(sensor)

    if smart_pv is True:
        for name, key, unit, icon in POWER_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name,
                hub,
                device_info,
                "power",
                name,
                key,
                unit,
                icon,
            )
            entities.append(sensor)

    if cirulator is True:
        for name, key, unit, icon in CIRC1_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name,
                hub,
                device_info,
                "circ1",
                name,
                key,
                unit,
                icon,
            )
            entities.append(sensor)

    if solar_circuit is True:
        
        for sk_count in range(num_smart_pv_sk):
            for name, key, unit, icon in SK1_SENSOR_TYPES.values():
                sensor = PellematicSensor(
                    hub_name,
                    hub,
                    device_info,
                    f"sk{sk_count+1}",
                    name.format(" " + str(sk_count + 1)),
                    key,
                    unit,
                    icon,
                )
                entities.append(sensor)

            for name, key, unit, icon in SK1_BINARY_SENSOR_TYPES.values():
                sensor = PellematicBinarySensor(
                    hub_name,
                    hub,
                    device_info,
                    f"sk{sk_count+1}",
                    name.format(" " + str(sk_count + 1)),
                    key,
                    unit,
                    icon,
                )
                entities.append(sensor)

        for se_count in range(num_smart_pv_se):
            for name, key, unit, icon in SE1_SENSOR_TYPES.values():
                sensor = PellematicSensor(
                    hub_name,
                    hub,
                    device_info,
                    f"se{se_count+1}",
                    name.format(" " + str(se_count + 1)),
                    key,
                    unit,
                    icon,
                )
                entities.append(sensor)

    for pe_count in range(num_pellematic_heater):
        for name, key, unit, icon in PE_SENSOR_TYPES.values():
            sensor = PellematicSensor(
                hub_name,
                hub,
                device_info,
                f"pe{pe_count+1}",
                name.format(" " + str(pe_count + 1)),
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
                name.format(" " + str(hot_water_count + 1)),
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
                name.format(" " + str(hot_water_count + 1)),
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

    _LOGGER.debug("Entities added : %i", len(entities))

    async_add_entities(entities)

    return True


class PellematicBinarySensor(BinarySensorEntity):
    """Representation of a binary sensor entity."""

    def __init__(
        self,
        platform_name,
        hub,
        device_info,
        prefix,
        name,
        key,
        unit,
        icon,
    ) -> None:
        """Initialize the sensor."""
        self._platform_name = platform_name
        self._hub = hub
        self._prefix = prefix
        self._key = key
        self._name = f"{self._platform_name} {name}"
        self._attr_unique_id = (
            f"{self._platform_name.lower()}_{self._prefix}_{self._key}"
        )
        self._unit_of_measurement = unit
        self._icon = icon
        self._device_info = device_info
        self._attr_device_class = BinarySensorDeviceClass.POWER
        if icon == "mdi:usb-flash-drive":
            self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

        _LOGGER.debug(
            "Adding a PellematicBinarySensor : %s, %s, %s, %s, %s, %s, %s, %s, %s, %s",
            str(self._platform_name),
            str(self._hub),
            str(self._prefix),
            str(self._key),
            str(self._name),
            str(self._attr_unique_id),
            str(self._unit_of_measurement),
            str(self._icon),
            str(self._device_info),
            str(self._attr_device_class),
        )

    @callback
    def _api_data_updated(self):
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        current_value = None
        try:
            current_value = self._hub.data[self._prefix][self._key.replace("#2", "")]["val"]
        except:
            try:
                current_value = self._hub.data[self._prefix][self._key.replace("#2", "")]
            except:
                pass
        
        if current_value == 'true':
            current_value = True
        elif current_value == 'false':
            current_value = False

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
            current_value = self._hub.data[self._prefix][self._key.replace("#2", "")]["val"]
        except:
            try:
                current_value = self._hub.data[self._prefix][self._key.replace("#2", "")]
            except:
                self._attr_is_on = current_value
        self._attr_is_on = current_value

    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

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
    def device_info(self) -> Optional[dict[str, Any]]:
        return self._device_info


class PellematicSensor(SensorEntity):
    """Representation of an Pellematic sensor."""

    def __init__(
        self,
        platform_name,
        hub,
        device_info,
        prefix,
        name,
        key,
        unit,
        icon,
    ) -> None:
        """Initialize the sensor."""
        self._platform_name = platform_name
        self._hub = hub
        self._prefix = prefix
        self._key = key
        self._name = f"{self._platform_name} {name}"
        self._attr_unique_id = (
            f"{self._platform_name.lower()}_{self._prefix}_{self._key}"
        )
        self._unit_of_measurement = unit
        self._icon = icon
        self._device_info = device_info
        self._state = None
        if self._unit_of_measurement == UnitOfPower.KILO_WATT:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.POWER
        if self._unit_of_measurement == UnitOfPower.WATT:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.POWER
        if self._unit_of_measurement == UnitOfEnergy.WATT_HOUR:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_device_class = SensorDeviceClass.ENERGY
        if self._unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_device_class = SensorDeviceClass.ENERGY
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

        _LOGGER.debug(
            "Adding a PellematicSensor : %s, %s, %s, %s, %s, %s, %s, %s, %s",
            str(self._platform_name),
            str(self._hub),
            str(self._prefix),
            str(self._key),
            str(self._name),
            str(self._attr_unique_id),
            str(self._unit_of_measurement),
            str(self._icon),
            str(self._device_info),
        )

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
            current_value = self._hub.data[self._prefix][self._key.replace("#2", "")]["val"]
            if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
                current_value = int(current_value) / 10
            if self._attr_device_class == UnitOfPower.KILO_WATT:
                current_value = int(current_value) / 10                         
            if self._unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR:
                # SE1 need / 10 but POWER need / 10000
                if self._prefix == "se1":
                    current_value = int(current_value) / 10
                else:
                    current_value = int(current_value) / 10000
            if self._attr_device_class == SensorDeviceClass.POWER_FACTOR:
                if current_value == 'true':
                    current_value = 100
                elif current_value == 'false':
                    current_value = 0
        except:
            try:
                current_value = self._hub.data[self._prefix][self._key.replace("#2", "")]
                if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
                    current_value = int(current_value) / 10
                if self._attr_device_class == UnitOfPower.KILO_WATT:
                    current_value = int(current_value) / 10     
                if self._unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR:
                    # SE1 need / 10 but POWER need / 10000
                    if self._prefix == "se1":
                        current_value = int(current_value) / 10
                    else:
                        current_value = int(current_value) / 10000
                if self._attr_device_class == SensorDeviceClass.POWER_FACTOR:
                    if current_value == 'true':
                        current_value = 100
                    elif current_value == 'false':
                        current_value = 0
            except:
                self._state = current_value
        self._state = current_value

    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

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
            current_value = self._hub.data[self._prefix][self._key.replace("#2", "")]["val"]
            if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
                current_value = int(current_value) / 10
            if self._attr_device_class == UnitOfPower.KILO_WATT:
                current_value = int(current_value) / 10                         
            if self._unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR:
                # SE1 need / 10 but POWER need / 10000
                if self._prefix == "se1":
                    current_value = int(current_value) / 10
                else:
                    current_value = int(current_value) / 10000
            if self._attr_device_class == SensorDeviceClass.POWER_FACTOR:
                if current_value == 'true':
                    current_value = 100
                elif current_value == 'false':
                    current_value = 0
        except:
            try:
                current_value = self._hub.data[self._prefix][self._key.replace("#2", "")]
                if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
                    current_value = int(current_value) / 10
                if self._attr_device_class == UnitOfPower.KILO_WATT:
                    current_value = int(current_value) / 10     
                if self._unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR:
                    # SE1 need / 10 but POWER need / 10000
                    if self._prefix == "se1":
                        current_value = int(current_value) / 10
                    else:
                        current_value = int(current_value) / 10000
                if self._attr_device_class == SensorDeviceClass.POWER_FACTOR:
                    if current_value == 'true':
                        current_value = 100
                    elif current_value == 'false':
                        current_value = 0
            except:
                pass
        return current_value

    @property
    def extra_state_attributes(self):
        return None

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return False

    @property
    def device_info(self) -> Optional[dict[str, Any]]:
        return self._device_info
