"""The Ökofen Pellematic Compact integration."""

import logging
import numbers
from typing import Optional, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from .const import (
    DOMAIN,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
)
from .dynamic_discovery import discover_all_entities

from homeassistant.const import (
    CONF_NAME,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfMass,
    UnitOfTime,
    UnitOfVolumeFlowRate,
    UnitOfPressure
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

def _sanitize_oekofen_value(raw_data: dict, value: Any) -> Any:
    # Drop clearly invalid/sentinel values coming from the Ökofen JSON API
    if value is None:
        return None

    # Common HA string states
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("unknown", "unavailable", "none", ""):
            return None
        # try parsing numeric string
        try:
            value = float(value) if ("." in value or "e" in v) else int(value)
        except Exception:
            # keep non-numeric strings for text sensors
            return value

    # Filter sentinel/overflow values close to min/max (e.g. 32765, 32767, -32768)
    if isinstance(value, numbers.Number):
        min_v = raw_data.get("min")
        max_v = raw_data.get("max")
        if isinstance(max_v, numbers.Number) and value >= (max_v - 2):
            return None
        if isinstance(min_v, numbers.Number) and value <= (min_v + 2):
            return None

    return value

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup entry using dynamic discovery"""
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
            _LOGGER.debug("No API data available yet for sensor discovery")
            return False
        
        try:
            discovered = discover_all_entities(data)
            
            _LOGGER.info("Dynamically discovered %d sensors, %d binary sensors", 
                         len(discovered['sensors']), len(discovered['binary_sensors']))

            # Create sensor entities with error handling
            for sensor_def in discovered['sensors']:
                entity_id = f"{sensor_def['component']}_{sensor_def['key']}"
                if entity_id in added_entity_ids:
                    continue
                    
                try:
                    sensor = PellematicSensor(
                        hub_name=hub_name,
                        hub=hub,
                        device_info=device_info,
                        sensor_definition=sensor_def,
                    )
                    entities.append(sensor)
                    added_entity_ids.add(entity_id)
                except Exception as e:
                    _LOGGER.error("Failed to create sensor %s: %s", entity_id, e)

            # Create binary sensor entities with error handling
            for sensor_def in discovered['binary_sensors']:
                entity_id = f"{sensor_def['component']}_{sensor_def['key']}"
                if entity_id in added_entity_ids:
                    continue
                    
                try:
                    sensor = PellematicBinarySensor(
                        hub_name=hub_name,
                        hub=hub,
                        device_info=device_info,
                        sensor_definition=sensor_def,
                    )
                    entities.append(sensor)
                    added_entity_ids.add(entity_id)
                except Exception as e:
                    _LOGGER.error("Failed to create binary sensor %s: %s", entity_id, e)

            # Add legacy error sensors (not in API metadata)
            for error_count in range(1, 6):
                entity_id = f"error_error_{error_count}"
                if entity_id in added_entity_ids:
                    continue
                    
                try:
                    sensor = PellematicSensor(
                        hub_name=hub_name,
                        hub=hub,
                        device_info=device_info,
                        sensor_definition={
                            'component': 'error',
                            'key': f'error_{error_count}',
                            'name': f'Error {error_count}',
                            'unit': None,
                            'icon': 'mdi:alert-circle',
                            'device_class': None,
                        }
                    )
                    entities.append(sensor)
                    added_entity_ids.add(entity_id)
                except Exception as e:
                    _LOGGER.error("Failed to create error sensor %d: %s", error_count, e)

            if entities:
                _LOGGER.debug("Adding %i new sensor entities", len(entities))
                async_add_entities(entities)
                return True
            else:
                _LOGGER.debug("No new sensor entities to add")
                return False
                
        except Exception as e:
            _LOGGER.error("Error during sensor discovery: %s", e)
            return False
    
    # Try initial setup
    success = await setup_entities_from_data()
    
    if not success:
        _LOGGER.warning(
            "Initial sensor setup incomplete. Will retry every 60 seconds until successful. "
            "You can also manually trigger rediscovery using the 'oekofen_pellematic_compact.rediscover_components' service."
        )
        
        # Set up retry mechanism - try again every 60 seconds until successful
        async def retry_setup(now):
            """Retry entity setup periodically."""
            success = await setup_entities_from_data()
            if success:
                _LOGGER.info("Sensor entity setup completed successfully after retry")
                # Cancel further retries
                if hasattr(retry_setup, 'cancel'):
                    retry_setup.cancel()
        
        # Track the interval so we can cancel it later
        retry_setup.cancel = async_track_time_interval(
            hass, retry_setup, timedelta(seconds=60)
        )

    return True


class PellematicBinarySensor(BinarySensorEntity):
    """Representation of a binary sensor entity."""

    def __init__(
        self,
        hub_name,
        hub,
        device_info,
        sensor_definition,
    ) -> None:
        """Initialize the binary sensor from dynamic definition."""
        self._platform_name = hub_name
        self._hub = hub
        self._prefix = sensor_definition['component']
        self._key = sensor_definition['key']
        self._name = f"{self._platform_name} {sensor_definition['name']}"
        self._attr_unique_id = (
            f"{self._platform_name.lower()}_{self._prefix}_{self._key}"
        )
        # Use component_key for entity_id instead of long human-readable name
        self._attr_object_id = f"{self._prefix}_{self._key}"
        self._unit_of_measurement = sensor_definition.get('unit')
        self._icon = sensor_definition.get('icon')
        self._device_info = device_info
        
        # Set device class from definition, default to POWER
        device_class = sensor_definition.get('device_class')
        if device_class:
            self._attr_device_class = device_class
        else:
            self._attr_device_class = BinarySensorDeviceClass.POWER
            if self._icon == "mdi:usb-flash-drive":
                self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

        _LOGGER.debug(
            "Adding dynamic PellematicBinarySensor: %s, %s",
            self._name, self._attr_unique_id,
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
            if (current_value is True or str(current_value).lower() == 'true'):
                current_value = True
            elif (current_value is False or str(current_value).lower() == 'false'):
                current_value = False
        except:
            pass

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
            if (current_value is True or str(current_value).lower() == 'true'):
                current_value = True
            elif (current_value is False or str(current_value).lower() == 'false'):
                current_value = False
        except:
            pass

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
        hub_name,
        hub,
        device_info,
        sensor_definition,
    ) -> None:
        """Initialize the sensor from dynamic definition."""
        self._platform_name = hub_name
        self._hub = hub
        self._prefix = sensor_definition['component']
        self._key = sensor_definition['key']
        self._name = f"{self._platform_name} {sensor_definition['name']}"
        self._attr_unique_id = (
            f"{self._platform_name.lower()}_{self._prefix}_{self._key}"
        )
        # Use component_key for entity_id instead of long human-readable name
        self._attr_object_id = f"{self._prefix}_{self._key}"
        self._unit_of_measurement = sensor_definition.get('unit')
        self._icon = sensor_definition.get('icon')
        self._device_info = device_info
        self._state = None
        
        # Set device class and state class from definition
        device_class = sensor_definition.get('device_class')
        if device_class:
            self._attr_device_class = device_class
            
            # Set appropriate state class based on device class
            if device_class in (SensorDeviceClass.TEMPERATURE, SensorDeviceClass.PRESSURE, 
                               SensorDeviceClass.POWER, SensorDeviceClass.VOLUME_FLOW_RATE,
                               SensorDeviceClass.WEIGHT, SensorDeviceClass.POWER_FACTOR):
                self._attr_state_class = SensorStateClass.MEASUREMENT
            elif device_class in (SensorDeviceClass.ENERGY, SensorDeviceClass.DURATION):
                # Energy should be total_increasing, but duration depends on the key
                if device_class == SensorDeviceClass.ENERGY:
                    self._attr_state_class = SensorStateClass.TOTAL_INCREASING
                else:
                    # For duration, hours are total_increasing, others are measurement
                    if self._unit_of_measurement == UnitOfTime.HOURS:
                        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
                    else:
                        self._attr_state_class = SensorStateClass.MEASUREMENT
        
        # Some keys need special handling for state class
        if self._key.replace("#2", "") in (
            'L_state', 'mode_auto', 'oekomode', 'L_wireless_name', 'L_wireless_id',
            'L_jaz_all', 'L_jaz_heat', 'L_jaz_cool', 'L_az_all', 'L_az_heat', 
            'L_az_cool', 'L_COP',
        ):
            self._attr_state_class = SensorStateClass.MEASUREMENT
        
        _LOGGER.debug(
            "Adding dynamic PellematicSensor: %s, %s, %s, %s",
            self._name, self._attr_unique_id, self._unit_of_measurement, self._icon,
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
            
            raw_data = None
            try:
                raw_data = self._hub.data[self._prefix][self._key.replace("#2", "")]
            except KeyError as e:
                # Not found so ok
                self._state = current_value
                return 
                
            try:
                current_value = raw_data["val"]
            except:
                 current_value = raw_data

            try:
                current_value = _sanitize_oekofen_value(raw_data, current_value)
                if current_value is None:
                    self._state = None
                    return
            except:
                pass
                
            multiply_success = False
            factor = None
            try:
                factor = raw_data["factor"]
                if factor is not None:
                    try:
                        result = float(current_value) * float(factor)
                        if result.is_integer():
                            current_value = int(result)
                        else:
                            current_value = result
                            
                        multiply_success = True
                    except ValueError:
                        _LOGGER.warning("Value %s could not be scaled with factor %s", current_value, factor)
            except:
                pass
        
            if factor is None or not multiply_success:
                # Der gesamte else-Block, den du hattest
                if hasattr(self, "_attr_device_class") and self._attr_device_class == SensorDeviceClass.TEMPERATURE:
                    current_value = int(current_value) / 10
                if self._unit_of_measurement == UnitOfVolumeFlowRate.LITERS_PER_MINUTE:
                    current_value = int(current_value) * 60
                if self._unit_of_measurement == UnitOfPower.KILO_WATT:
                    current_value = int(current_value) / 10                         
                if self._unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR:
                    if self._prefix.lower().startswith("se"):
                        current_value = int(current_value) / 10
                    else:
                        current_value = int(current_value) / 10000
                if hasattr(self, "_attr_device_class") and self._attr_device_class == SensorDeviceClass.POWER_FACTOR:
                    if (current_value is True or str(current_value).lower() == 'true'):
                        current_value = 100
                    elif (current_value is False or str(current_value).lower() == 'false'):
                        current_value = 0
                    if (self._key.replace("#2", "") == 'L_wireless_hum'):
                        current_value = int(current_value) / 10  
        except Exception as e:
            _LOGGER.error("An error occurred: %s", e)
        
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
            
            raw_data = None
            try:
                raw_data = self._hub.data[self._prefix][self._key.replace("#2", "")]
            except KeyError as e:
                return None
            
            try:
                current_value = raw_data["val"]
            except:
                 current_value = raw_data

            try:
                current_value = _sanitize_oekofen_value(raw_data, current_value)
                if current_value is None:
                    return None
            except:
                pass
        
            multiply_success = False
            factor = None
            try:
                factor = raw_data["factor"]
                if factor is not None:
                    try:
                        result = float(current_value) * float(factor)
                        if result.is_integer():
                            current_value = int(result)
                        else:
                            current_value = result
                            
                        multiply_success = True
                    except ValueError:
                        _LOGGER.warning("Value %s could not be scaled with factor %s", current_value, factor)
            except:
                pass
        
            if factor is None or not multiply_success:
                # Der gesamte else-Block, den du hattest
                if hasattr(self, "_attr_device_class") and self._attr_device_class == SensorDeviceClass.TEMPERATURE:
                    current_value = int(current_value) / 10
                if self._unit_of_measurement == UnitOfVolumeFlowRate.LITERS_PER_MINUTE:
                    current_value = int(current_value) * 60
                if self._unit_of_measurement == UnitOfPower.KILO_WATT:
                    current_value = int(current_value) / 10                         
                if self._unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR:
                    if self._prefix.lower().startswith("se"):
                        current_value = int(current_value) / 10
                    else:
                        current_value = int(current_value) / 10000
                if hasattr(self, "_attr_device_class") and self._attr_device_class == SensorDeviceClass.POWER_FACTOR:
                    if (current_value is True or str(current_value).lower() == 'true'):
                        current_value = 100
                    elif (current_value is False or str(current_value).lower() == 'false'):
                        current_value = 0
                    if (self._key.replace("#2", "") == 'L_wireless_hum'):
                        current_value = int(current_value) / 10  
                        
        except Exception as e:
            _LOGGER.error("An error occurred: %s", e)
        
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
