"""The Ökofen Pellematic Compact integration."""

import logging
import numbers
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
    CONF_NUM_OF_HEAT_PUMPS,
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
    WP_SENSOR_TYPES,
    WP_DATA_SENSOR_TYPES,
    DEFAULT_NUM_OF_HEAT_PUMPS,
    DEFAULT_NUM_OF_HOT_WATER,
    DEFAULT_NUM_OF_PELLEMATIC_HEATER,
    DEFAULT_NUM_OF_SMART_PV_SE,
    DEFAULT_NUM_OF_SMART_PV_SK,
    WIRELESS_SENSOR_TYPES,
    CONF_NUM_OF_WIRELESS_SENSORS,
    DEFAULT_NUM_OF_WIRELESS_SENSORS,
    CONF_NUM_OF_BUFFER_STORAGE,
    DEFAULT_NUM_OF_BUFFER_STORAGE,
)

from homeassistant.const import (
    CONF_NAME,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfMass,
    UnitOfTime,
    UnitOfVolumeFlowRate,
    UnitOfPressure,
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

HIGH_PRECISION_KEYS = {
    "L_cop",
    "L_jaz_all",
    "L_jaz_heat",
    "L_jaz_cool",
    "L_az_all",
    "L_az_heat",
    "L_az_cool",
}


def _final_round(value, unit, device_class, key=None):
    if value is None:
        return None

    try:
        v = float(value)
    except (TypeError, ValueError):
        return value

    # COP / JAZ / AZ - 3 Nachkommastellen
    if key in HIGH_PRECISION_KEYS:
        return round(v, 3)

    # Laufzeit (h) - 2 Nachkommastellen
    if unit == UnitOfTime.HOURS:
        return round(v, 2)

    # Temperaturen - 1 Nachkommastelle
    if device_class == SensorDeviceClass.TEMPERATURE:
        return round(v, 1)

    # Durchfluss - 2 Nachkommastellen
    if unit == UnitOfVolumeFlowRate.LITERS_PER_MINUTE:
        return round(v, 2)

    # Leistung:
    # - W -> ganze Zahl
    # - kW -> 3 Nachkommastellen (oder 2, wenn du lieber willst)
    if unit == UnitOfPower.WATT:
        return int(round(v, 0))
    
    if unit == UnitOfPower.KILO_WATT:
        return round(v, 3)   # oder round(v, 2)


    # Prozent - ganze Zahl
    if unit == PERCENTAGE:
        return int(round(v, 0))

    # Default
    # (für z.B. "steps" oder "rps" => Zahl ohne Nachkommastellen)
    return int(round(v, 0))


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
        num_hot_water = DEFAULT_NUM_OF_HOT_WATER
    try:
        num_pellematic_heater = entry.data[CONF_NUM_OF_PELLEMATIC_HEATER]
    except:
        num_pellematic_heater = DEFAULT_NUM_OF_PELLEMATIC_HEATER
    try:
        num_smart_pv_se = entry.data[CONF_NUM_OF_SMART_PV_SE]
    except:
        num_smart_pv_se = DEFAULT_NUM_OF_SMART_PV_SE
    try:
        num_smart_pv_sk = entry.data[CONF_NUM_OF_SMART_PV_SK]
    except:
        num_smart_pv_sk = DEFAULT_NUM_OF_SMART_PV_SK
    try:
        num_heat_pumps = entry.data[CONF_NUM_OF_HEAT_PUMPS]
    except:
        num_heat_pumps = DEFAULT_NUM_OF_HEAT_PUMPS
    try:
        num_wireless_sensors = entry.data[CONF_NUM_OF_WIRELESS_SENSORS]
    except:
        num_wireless_sensors = DEFAULT_NUM_OF_WIRELESS_SENSORS
    try:
        num_buffer_storage = entry.data[CONF_NUM_OF_BUFFER_STORAGE]
    except:
        num_buffer_storage = DEFAULT_NUM_OF_BUFFER_STORAGE

    _LOGGER.debug("Setup entry %s %s", hub_name, hub)

    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
    }

    entities = []

    for name, key, unit, icon in SYSTEM_SENSOR_TYPES.values():
        entities.append(PellematicSensor(hub_name, hub, device_info, "system", name, key, unit, icon))

    for name, key, unit, icon in SYSTEM_BINARY_SENSOR_TYPES.values():
        entities.append(PellematicBinarySensor(hub_name, hub, device_info, "system", name, key, unit, icon))

    for idx in range(num_wireless_sensors):
        for name, key, unit, icon in WIRELESS_SENSOR_TYPES.values():
            entities.append(
                PellematicSensor(
                    hub_name,
                    hub,
                    device_info,
                    f"wireless{idx + 1}",
                    name.format(" " + str(idx + 1)),
                    key,
                    unit,
                    icon,
                )
            )

    for heating_cir_count in range(num_heating_circuit):
        for name, key, unit, icon in HK_SENSOR_TYPES.values():
            entities.append(
                PellematicSensor(
                    hub_name,
                    hub,
                    device_info,
                    f"hk{heating_cir_count + 1}",
                    name.format(" " + str(heating_cir_count + 1)),
                    key,
                    unit,
                    icon,
                )
            )

        for name, key, unit, icon in HK_BINARY_SENSOR_TYPES.values():
            entities.append(
                PellematicBinarySensor(
                    hub_name,
                    hub,
                    device_info,
                    f"hk{heating_cir_count + 1}",
                    name.format(" " + str(heating_cir_count + 1)),
                    key,
                    unit,
                    icon,
                )
            )

    if stirling is True:
        for name, key, unit, icon in STIRLING_SENSOR_TYPES.values():
            entities.append(PellematicSensor(hub_name, hub, device_info, "stirling", name, key, unit, icon))

    if smart_pv is True:
        for name, key, unit, icon in POWER_SENSOR_TYPES.values():
            entities.append(PellematicSensor(hub_name, hub, device_info, "power", name, key, unit, icon))

    if cirulator is True:
        for name, key, unit, icon in CIRC1_SENSOR_TYPES.values():
            entities.append(PellematicSensor(hub_name, hub, device_info, "circ1", name, key, unit, icon))

    if solar_circuit is True:
        for sk_count in range(num_smart_pv_sk):
            for name, key, unit, icon in SK1_SENSOR_TYPES.values():
                entities.append(
                    PellematicSensor(
                        hub_name,
                        hub,
                        device_info,
                        f"sk{sk_count + 1}",
                        name.format("" if sk_count == 0 else " " + str(sk_count + 1)),
                        key,
                        unit,
                        icon,
                    )
                )

            for name, key, unit, icon in SK1_BINARY_SENSOR_TYPES.values():
                entities.append(
                    PellematicBinarySensor(
                        hub_name,
                        hub,
                        device_info,
                        f"sk{sk_count + 1}",
                        name.format("" if sk_count == 0 else " " + str(sk_count + 1)),
                        key,
                        unit,
                        icon,
                    )
                )

        for se_count in range(num_smart_pv_se):
            for name, key, unit, icon in SE1_SENSOR_TYPES.values():
                entities.append(
                    PellematicSensor(
                        hub_name,
                        hub,
                        device_info,
                        f"se{se_count + 1}",
                        name.format("" if se_count == 0 else " " + str(se_count + 1)),
                        key,
                        unit,
                        icon,
                    )
                )

    for pe_count in range(num_pellematic_heater):
        for name, key, unit, icon in PE_SENSOR_TYPES.values():
            entities.append(
                PellematicSensor(
                    hub_name,
                    hub,
                    device_info,
                    f"pe{pe_count + 1}",
                    name.format(" " + str(pe_count + 1)),
                    key,
                    unit,
                    icon,
                )
            )

    for pu_count in range(num_buffer_storage):
        for name, key, unit, icon in PU1_SENSOR_TYPES.values():
            entities.append(
                PellematicSensor(
                    hub_name,
                    hub,
                    device_info,
                    f"pu{pu_count + 1}",
                    name.format("" if pu_count == 0 else " " + str(pu_count + 1)),
                    key,
                    unit,
                    icon,
                )
            )

        for name, key, unit, icon in PU1_BINARY_SENSOR_TYPES.values():
            entities.append(
                PellematicBinarySensor(
                    hub_name,
                    hub,
                    device_info,
                    f"pu{pu_count + 1}",
                    name.format("" if pu_count == 0 else " " + str(pu_count + 1)),
                    key,
                    unit,
                    icon,
                )
            )

    for hot_water_count in range(num_hot_water):
        for name, key, unit, icon in WW_SENSOR_TYPES.values():
            entities.append(
                PellematicSensor(
                    hub_name,
                    hub,
                    device_info,
                    f"ww{hot_water_count + 1}",
                    name.format(" " + str(hot_water_count + 1)),
                    key,
                    unit,
                    icon,
                )
            )

        for name, key, unit, icon in WW_BINARY_SENSOR_TYPES.values():
            entities.append(
                PellematicBinarySensor(
                    hub_name,
                    hub,
                    device_info,
                    f"ww{hot_water_count + 1}",
                    name.format(" " + str(hot_water_count + 1)),
                    key,
                    unit,
                    icon,
                )
            )

    for error_count in range(1, 6):
        entities.append(
            PellematicSensor(
                hub_name,
                hub,
                device_info,
                "error",
                f"Error {error_count}",
                f"error_{error_count}",
                None,
                "mdi:alert-circle",
            )
        )

    for heatpump_count in range(num_heat_pumps):
        for name, key, unit, icon in WP_SENSOR_TYPES.values():
            entities.append(
                PellematicSensor(
                    hub_name,
                    hub,
                    device_info,
                    f"wp{heatpump_count + 1}",
                    name.format(" " + str(heatpump_count + 1)),
                    key,
                    unit,
                    icon,
                )
            )
        for name, key, unit, icon in WP_DATA_SENSOR_TYPES.values():
            entities.append(
                PellematicSensor(
                    hub_name,
                    hub,
                    device_info,
                    f"wp_data{heatpump_count + 1}",
                    name.format(" " + str(heatpump_count + 1)),
                    key,
                    unit,
                    icon,
                )
            )

    _LOGGER.debug("Entities added : %i", len(entities))
    async_add_entities(entities)
    return True


class PellematicBinarySensor(BinarySensorEntity):
    """Representation of a binary sensor entity."""

    def __init__(self, platform_name, hub, device_info, prefix, name, key, unit, icon) -> None:
        self._platform_name = platform_name
        self._hub = hub
        self._prefix = prefix
        self._key = key
        self._name = f"{self._platform_name} {name}"
        self._attr_unique_id = f"{self._platform_name.lower()}_{self._prefix}_{self._key}"
        self._unit_of_measurement = unit
        self._icon = icon
        self._device_info = device_info
        self._attr_device_class = BinarySensorDeviceClass.POWER
        if icon == "mdi:usb-flash-drive":
            self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool:
        current_value = None
        try:
            current_value = self._hub.data[self._prefix][self._key.replace("#2", "")]["val"]
            if current_value is True or str(current_value).lower() == "true":
                current_value = True
            elif current_value is False or str(current_value).lower() == "false":
                current_value = False
        except:
            pass
        return current_value

    async def async_added_to_hass(self):
        self._hub.async_add_pellematic_sensor(self._api_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_pellematic_sensor(self._api_data_updated)

    @callback
    def _api_data_updated(self):
        self.async_write_ha_state()

    @property
    def name(self):
        return f"{self._name}"

    @property
    def icon(self):
        return self._icon

    @property
    def extra_state_attributes(self):
        return None

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def device_info(self) -> Optional[dict[str, Any]]:
        return self._device_info


class PellematicSensor(SensorEntity):
    """Representation of an Pellematic sensor."""

    def __init__(self, platform_name, hub, device_info, prefix, name, key, unit, icon) -> None:
        self._platform_name = platform_name
        self._hub = hub
        self._prefix = prefix
        self._key = key
        self._name = f"{self._platform_name} {name}"
        self._attr_unique_id = f"{self._platform_name.lower()}_{self._prefix}_{self._key}"
        self._unit_of_measurement = unit
        self._icon = icon
        self._device_info = device_info
        self._state = None
        self._attr_state_class = None
        self._attr_suggested_display_precision = None

        # Temperaturen (z.B. Overheat) - 1 Nachkommastelle
        if unit == UnitOfTemperature.CELSIUS:
            self._attr_suggested_display_precision = 1

        # Leistung in kW - 3 Nachkommastellen
        if unit == UnitOfPower.KILO_WATT:
            self._attr_suggested_display_precision = 3

        if self._unit_of_measurement == UnitOfVolumeFlowRate.LITERS_PER_MINUTE:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
        if self._unit_of_measurement == UnitOfPressure.BAR:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_device_class = SensorDeviceClass.PRESSURE
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

        if self._unit_of_measurement == "rps":
            self._attr_state_class = SensorStateClass.MEASUREMENT

        if self._key.replace("#2", "") in (
            "L_state",
            "mode_auto",
            "oekomode",
            "L_wireless_name",
            "L_wireless_id",
            "L_jaz_all",
            "L_jaz_heat",
            "L_jaz_cool",
            "L_az_all",
            "L_az_heat",
            "L_az_cool",
            "L_cop",
            "L_eev",
            "L_overheat_set",
            "L_overheat_is",
            "L_overheat",
        ):
            self._attr_state_class = SensorStateClass.MEASUREMENT

    async def async_added_to_hass(self):
        self._hub.async_add_pellematic_sensor(self._api_data_updated)
        self._update_state()

    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_pellematic_sensor(self._api_data_updated)

    @callback
    def _api_data_updated(self):
        self._update_state()
        self.async_write_ha_state()

    @callback
    def _update_state(self):
        current_value = None
        try:
            try:
                raw_data = self._hub.data[self._prefix][self._key.replace("#2", "")]
            except KeyError:
                self._state = None
                return

            try:
                current_value = raw_data["val"]
            except Exception:
                current_value = raw_data

            try:
                current_value = _sanitize_oekofen_value(raw_data, current_value)
                if current_value is None:
                    self._state = None
                    return
            except Exception:
                pass

            multiply_success = False
            factor = None
            try:
                factor = raw_data.get("factor")
                if factor is not None:
                    result = float(current_value) * float(factor)
                    current_value = int(result) if result.is_integer() else result
                    multiply_success = True
            except Exception:
                pass

            if factor is None or not multiply_success:
                if getattr(self, "_attr_device_class", None) == SensorDeviceClass.TEMPERATURE:
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
                if getattr(self, "_attr_device_class", None) == SensorDeviceClass.POWER_FACTOR:
                    if current_value is True or str(current_value).lower() == "true":
                        current_value = 100
                    elif current_value is False or str(current_value).lower() == "false":
                        current_value = 0
                    if self._key.replace("#2", "") == "L_wireless_hum":
                        current_value = int(current_value) / 10

        except Exception as e:
            _LOGGER.error("An error occurred: %s", e)

        # Fix scaling for overheat values (Ökofen liefert hier scheinbar 0.1x)
        if self._key.replace("#2", "") in ("L_overheat_set", "L_overheat_is", "L_overheat") and current_value is not None:
            try:
                current_value = float(current_value) * 10.0
                current_value = round(current_value, 1)
            except Exception:
                pass

        # Ökofen: L_uwp kommt als 0..1, soll aber 0..100 % sein
        if self._key.replace("#2", "") == "L_uwp" and current_value is not None:
            try:
                current_value = float(current_value) * 100.0
                current_value = round(current_value, 1)
            except Exception:
                pass

        self._state = _final_round(
            current_value,
            self._unit_of_measurement,
            getattr(self, "_attr_device_class", None),
            self._key.replace("#2", ""),
        )

    @property
    def name(self):
        return f"{self._name}"

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return None

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def device_info(self) -> Optional[dict[str, Any]]:
        return self._device_info
