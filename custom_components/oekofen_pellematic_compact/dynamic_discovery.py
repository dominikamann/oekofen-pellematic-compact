"""Dynamic sensor discovery from API metadata."""

import logging
from typing import Any, Optional
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfMass,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfTime,
    UnitOfFrequency,
    PERCENTAGE,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number import NumberDeviceClass

_LOGGER = logging.getLogger(__name__)

# Component name translations for better entity names (international/English)
COMPONENT_NAMES = {
    "system": "System",
    "hk": "Heating Circuit",
    "autocomfort_hk": "Auto Comfort Heating Circuit",
    "pe": "Pellematic",
    "pu": "Buffer Storage",
    "ww": "Hot Water",
    "sk": "Solar Collector",
    "se": "Solar Gain",
    "wp": "Heat Pump",
    "wp_data": "Heat Pump Data",
    "circ": "Circulation",
    "weather": "Weather",
    "forecast": "Forecast",
    "power": "Smart PV",
    "stirling": "Stirling",
    "wireless": "Wireless Sensor",
    "thirdparty": "Third Party Sensor",
}

# Keys to ignore (metadata/info fields)
IGNORE_KEYS = {
    "system_info",
    "hk_info",
    "autocomfort_hk_info",
    "pe_info",
    "pu_info",
    "ww_info",
    "sk_info",
    "se_info",
    "wp_info",
    "wp_data_info",
    "circ_info",
    "weather_info",
    "forecast_info",
    "power_info",
    "stirling_info",
    "wireless_info",
    "thirdparty_info",
}


def extract_key_suffix(key: str) -> str:
    """Extract the meaningful part of a key for disambiguation.
    
    Examples:
        mode_off -> off
        mode_auto -> auto
        mode_dhw -> dhw
        temp_setback -> setback
        solarheat_mode_off -> solarheat off
    """
    # Handle special prefixes that need special treatment
    if key.startswith("solarheat_mode_"):
        suffix = key.replace("solarheat_mode_", "")
        return f"solarheat {suffix}"

    # Preserve ext_ prefix to keep external variants distinct
    if key.startswith("ext_"):
        return key
    
    # For other keys, extract the part after the first underscore
    parts = key.split("_")
    if len(parts) >= 2:
        # For keys like temp_setback, sensor_on, mode_auto
        return "_".join(parts[1:])
    
    return key


def is_binary_sensor(data: dict) -> bool:
    """Check if data represents a binary sensor."""
    if "format" not in data:
        return False
    
    format_str = data["format"]
    # Binary sensors have format like "0:Aus|1:Ein" or "0:Off|1:On"
    # Check if it's a simple two-option format
    if isinstance(format_str, str) and "|" in format_str:
        parts = format_str.split("|")
        if len(parts) == 2:
            # Check if both parts start with 0: or 1: (or false:/true:)
            return (parts[0].strip().startswith(("0:", "false:")) and 
                    parts[1].strip().startswith(("1:", "true:")))
    
    return False


def is_select(data: dict) -> bool:
    """Check if data represents a select entity."""
    if "format" not in data:
        return False
    
    format_str = data["format"]
    # Selects have format like "0:Aus|1:Auto|2:Ein"
    if isinstance(format_str, str) and "|" in format_str:
        parts = format_str.split("|")
        # More than 2 options means it's a select, not binary
        return len(parts) > 2
    
    return False


def is_number(data: dict) -> bool:
    """Check if data represents a number entity.
    
    Note: This function should only be called for writable entities (without L_ prefix).
    Read-only sensors with min/max values are filtered out earlier in the discovery logic.
    
    Old firmware (v3.24.0 and earlier) does not provide a 'writeable' flag.
    We detect writable number entities by the presence of min/max fields.
    This ensures backwards compatibility with older Ökofen firmware versions.
    """
    # Numbers have min and max values and are writable (no L_ prefix)
    return "min" in data and "max" in data


def is_read_only_statistic(key: str) -> bool:
    """Check if a key represents a read-only statistic/counter value.
    
    Even though these keys don't have L_ prefix, they are conceptually
    read-only (historical data, statistics, counters) and should not be
    writable number entities.
    
    Args:
        key: The key to check
        
    Returns:
        True if the key represents read-only statistics
    """
    key_lower = key.lower()
    
    # Historical/time-based statistics
    if any(word in key_lower for word in ['_yesterday', '_today', '_last_', '_prev_']):
        return True
    
    # Totals and accumulated values
    if any(word in key_lower for word in ['_total', '_consumed', '_consumption']):
        return True
    
    # Counters
    if any(word in key_lower for word in ['_runtime', '_starts', '_count', '_cycles']):
        return True
    
    # Storage fill is a calculated/measured value, not a setting
    if 'storage_fill' in key_lower:
        return True
    
    return False


def parse_select_options(format_str: str) -> list[str]:
    """Parse select options from format string.
    
    Example: "0:Aus|1:Auto|2:Ein" -> ["0_aus", "1_auto", "2_ein"]
    """
    if not format_str or "|" not in format_str:
        return []
    
    options = []
    for part in format_str.split("|"):
        if ":" in part:
            # Convert "0:Aus" to "0_aus"
            value, label = part.split(":", 1)
            option = f"{value.strip()}_{label.strip().lower().replace(' ', '_')}"
            options.append(option)
        else:
            options.append(part.strip().lower().replace(" ", "_"))
    
    return options


def infer_device_class(data: dict, key: str) -> Optional[str]:
    """Infer device class from unit and key name."""
    unit = data.get("unit", "")
    text = data.get("text", "").lower()
    key_lower = key.lower()
    
    # Fix common encoding issues where ° becomes ?
    unit_fixed = unit.replace('?C', '°C').replace('?c', '°C') if unit else ""
    
    # Temperature
    if unit_fixed in ("°C", "K"):
        return SensorDeviceClass.TEMPERATURE
    
    # Energy
    if unit == "kWh":
        return SensorDeviceClass.ENERGY
    
    # Power
    if unit in ("W", "kW"):
        return SensorDeviceClass.POWER
    
    # Weight/Mass
    if unit == "kg":
        return SensorDeviceClass.WEIGHT
    
    # Duration
    if unit in ("h", "min", "s", "zs"):
        return SensorDeviceClass.DURATION
    
    # Pressure
    if unit in ("EH", "Pa", "bar"):
        return SensorDeviceClass.PRESSURE
    
    # Voltage
    if unit == "V":
        return SensorDeviceClass.VOLTAGE
    
    # Current
    if unit == "A":
        return SensorDeviceClass.CURRENT
    
    # Frequency
    if unit in ("Hz", "rps"):
        return SensorDeviceClass.FREQUENCY
    
    # Try to infer from text/key
    if "temp" in text or "temp" in key_lower:
        return SensorDeviceClass.TEMPERATURE
    
    if "error" in text or "fehler" in text or "error" in key_lower:
        return SensorDeviceClass.ENUM
    
    return None


def infer_binary_device_class(data: dict, key: str) -> Optional[BinarySensorDeviceClass]:
    """Infer the correct BinarySensorDeviceClass from key name and context."""
    key_lower = key.lower()
    text = data.get("text", "").lower()

    # Pumps / motors that are running or stopped
    if any(word in key_lower for word in ("pump", "pumpe", "pummp")):
        return BinarySensorDeviceClass.RUNNING

    # Burner / ignition / fan running
    if any(word in key_lower for word in ("_br", "_ak")):
        return BinarySensorDeviceClass.RUNNING

    # Fault / emergency / safety trip condition
    if any(word in key_lower for word in ("_not", "_stb", "error", "fault", "stoer")):
        return BinarySensorDeviceClass.PROBLEM

    # USB / connectivity
    if "usb" in key_lower:
        return BinarySensorDeviceClass.CONNECTIVITY

    # Fall back based on translated label if available
    if any(word in text for word in ("pump", "pumpe")):
        return BinarySensorDeviceClass.RUNNING
    if any(word in text for word in ("fehler", "error", "fault", "stor")):
        return BinarySensorDeviceClass.PROBLEM

    return None


def infer_number_device_class(data: dict, key: str) -> Optional[str]:
    """Infer number device class."""
    unit = data.get("unit", "")
    
    if unit in ("°C", "K"):
        return NumberDeviceClass.TEMPERATURE
    
    return None


def infer_state_class(data: dict) -> Optional[str]:
    """Infer state class for sensor."""
    key_lower = data.get("text", "").lower()
    unit = data.get("unit", "")
    
    # Fix common encoding issues where ° becomes ?
    unit_fixed = unit.replace('?C', '°C').replace('?c', '°C') if unit else ""
    
    # Total/Counter sensors
    if any(word in key_lower for word in ["total", "gesamt", "counter", "starts", "runtime", "laufzeit"]):
        return SensorStateClass.TOTAL_INCREASING
    
    # Measurement sensors (temperature, power, energy, frequency, etc.)
    # All sensors with numeric units should have state_class for long-term statistics
    if unit_fixed:
        # These are typically measurement sensors
        if unit_fixed in ("°C", "K", "W", "kW", "kWh", "kg", "Pa", "bar", "EH", "V", "A", "Hz", "rps", "%", "h", "min", "s", "zs", "l/min", "km/h"):
            return SensorStateClass.MEASUREMENT
        # Most sensors with units are measurements
        return SensorStateClass.MEASUREMENT
    
    return None


def infer_icon(data: dict, key: str) -> str:
    """Infer icon from context."""
    text = data.get("text", "").lower()
    key_lower = key.lower()
    
    # Temperature
    if "temp" in text or "temp" in key_lower:
        return "mdi:thermometer"
    
    # Errors
    if "fehler" in text or "error" in text:
        return "mdi:alert-circle"
    
    # Pump
    if "pump" in text or "pumpe" in text:
        return "mdi:pump"
    
    # Solar
    if "solar" in text or "koll" in text:
        return "mdi:solar-power"
    
    # Power/Energy
    if any(word in text for word in ["power", "energie", "energy", "leistung"]):
        return "mdi:flash"
    
    # Water
    if "wasser" in text or "water" in text:
        return "mdi:water"
    
    # Fire/Flame
    if "flamm" in text or "flame" in text or "brenn" in text:
        return "mdi:fire"
    
    # USB
    if "usb" in text or "usb" in key_lower:
        return "mdi:usb-flash-drive"
    
    # Mode/State
    if "mode" in key_lower or "betrieb" in text:
        return "mdi:cog"
    
    # Default
    return "mdi:gauge"


def normalize_unit(unit: str) -> str:
    """Normalize unit to Home Assistant standard."""
    if not unit:
        return None
    
    # Fix common encoding issues where ° (degree symbol) becomes ?
    # This happens when UTF-8 data is misinterpreted as ISO-8859-1 or similar
    # Also normalize plain "C" to "°C" as some APIs send it without degree symbol
    unit_fixed = unit.replace('?C', '°C').replace('?c', '°C')
    if unit_fixed == "C":
        unit_fixed = "°C"
    
    # Normalize zs (Zehntel-Sekunden/tenth-seconds) to s (seconds) for consistency
    # The factor field in the data handles the 0.1 conversion
    if unit_fixed == "zs":
        unit_fixed = "s"
    
    # Map common units
    unit_map = {
        "Â°C": UnitOfTemperature.CELSIUS,
        "°C": UnitOfTemperature.CELSIUS,
        "C": UnitOfTemperature.CELSIUS,  # Some APIs send C without degree symbol
        "K": UnitOfTemperature.KELVIN,
        "%": PERCENTAGE,
        "kWh": UnitOfEnergy.KILO_WATT_HOUR,
        "W": UnitOfPower.WATT,
        "kW": UnitOfPower.KILO_WATT,
        "kg": UnitOfMass.KILOGRAMS,
        "h": UnitOfTime.HOURS,
        "min": UnitOfTime.MINUTES,
        "s": UnitOfTime.SECONDS,
        "Hz": UnitOfFrequency.HERTZ,
        "rps": "rps",  # Rotations per second
        "EH": "EH",  # Einheit (unit) for pressure measurements
        "l/min": "L/min",  # Liters per minute
        "km/h": "km/h",  # Kilometers per hour
    }
    
    return unit_map.get(unit_fixed, unit_fixed)


def get_component_display_name(component: str, index: int = 0) -> str:
    """Get human-readable component name.
    
    Args:
        component: Component key (e.g., "hk1", "pe2", "system")
        index: Numeric index extracted from component (e.g., 1 from "hk1")
        
    Returns:
        Localized component name (e.g., "Heizkreis 1", "Pellematic 2")
    """
    # Extract base component type (e.g., "hk" from "hk1")
    base = ''.join(c for c in component if not c.isdigit())
    
    # Get translated name
    display_name = COMPONENT_NAMES.get(base, base.upper())
    
    # Add index if present
    if index > 0:
        return f"{display_name} {index}"
    
    return display_name


def create_sensor_definition(
    component: str,
    key: str,
    data: dict,
    index: int = 0,
    keys_need_disambiguation: set = None
) -> dict:
    """Create sensor definition from API data.
    
    Args:
        component: Component name (e.g., "hk1", "pe1", "system")
        key: Sensor key (e.g., "L_temp_act")
        data: API data for this sensor
        index: Index for numbered components (for display name)
        keys_need_disambiguation: Set of keys that need disambiguation in this component
    
    Returns:
        Dictionary with sensor configuration
    """
    # Get base name from API or use key as fallback
    base_name = data.get("text", key)
    
    # Check if this key needs disambiguation by appending the key part
    if keys_need_disambiguation and key in keys_need_disambiguation:
        key_suffix = extract_key_suffix(key)
        base_name = f"{base_name} ({key_suffix})"
    
    # Add component prefix to name for clarity (except system-wide entities)
    if component == "system":
        name = base_name
    else:
        component_name = get_component_display_name(component, index)
        name = f"{component_name} {base_name}"
    
    return {
        "component": component,
        "key": key,
        "name": name,
        "unique_id": f"{component}_{key}",
        "unit": normalize_unit(data.get("unit")),
        "device_class": infer_device_class(data, key),
        "state_class": infer_state_class(data),
        "icon": infer_icon(data, key),
        "factor": data.get("factor", 1),
        "min_value": data.get("min"),
        "max_value": data.get("max"),
        "format": data.get("format"),
    }


def create_number_definition(
    component: str,
    key: str,
    data: dict,
    index: int = 0,
    keys_need_disambiguation: set = None
) -> dict:
    """Create number entity definition from API data."""
    definition = create_sensor_definition(component, key, data, index, keys_need_disambiguation)
    definition["device_class"] = infer_number_device_class(data, key)
    definition["step"] = 0.1 if definition["unit"] in (UnitOfTemperature.CELSIUS, UnitOfTemperature.KELVIN) else 1
    
    return definition


def create_select_definition(
    component: str,
    key: str,
    data: dict,
    index: int = 0,
    keys_need_disambiguation: set = None
) -> dict:
    """Create select entity definition from API data."""
    definition = create_sensor_definition(component, key, data, index, keys_need_disambiguation)
    definition["options"] = parse_select_options(data.get("format", ""))
    
    return definition


def discover_entities_from_component(
    component_key: str,
    component_data: dict
) -> dict:
    """Discover all entities from a single component.
    
    Args:
        component_key: Component identifier (e.g., "hk1", "pe1")
        component_data: API data for this component
    
    Returns:
        Dictionary with lists of discovered entities by type
    """
    entities = {
        "sensors": [],
        "binary_sensors": [],
        "selects": [],
        "numbers": []
    }
    
    if not isinstance(component_data, dict):
        return entities
    
    # Extract numeric index from component key (e.g., 1 from "hk1")
    index = 0
    for char in component_key:
        if char.isdigit():
            index = index * 10 + int(char)
    
    # First pass: Build a map of text values to keys to detect duplicates
    text_to_keys = {}
    for key, data in component_data.items():
        if key in IGNORE_KEYS:
            continue
            
        # Get the text value
        if isinstance(data, dict):
            text = data.get("text", "")
        else:
            continue
        
        if text:
            if text not in text_to_keys:
                text_to_keys[text] = []
            text_to_keys[text].append(key)
    
    # Find keys that need disambiguation (same text appears multiple times)
    keys_need_disambiguation = set()
    for text, keys in text_to_keys.items():
        if len(keys) > 1:
            # Multiple keys share the same text - they all need disambiguation
            keys_need_disambiguation.update(keys)
    
    # Second pass: Create entity definitions
    for key, data in component_data.items():
        # Skip info/metadata keys
        if key in IGNORE_KEYS:
            continue
        
        # Handle different data formats:
        # 1. Standard format: {"val": 123, "unit": "°C", ...}
        # 2. Simple format: 123 (just the value)
        # 3. String values: "text"
        
        if isinstance(data, dict):
            # Standard format - must have "val" key
            if "val" not in data:
                continue
        else:
            # Simple format - wrap in dict
            data = {"val": data}
        
        # Determine entity type and create definition
        if key.startswith("L_"):
            # Read-only sensor (API convention: L_ prefix = read-only)
            if is_binary_sensor(data):
                definition = create_sensor_definition(component_key, key, data, index, keys_need_disambiguation)
                definition["device_class"] = infer_binary_device_class(data, key)
                entities["binary_sensors"].append(definition)
            else:
                definition = create_sensor_definition(component_key, key, data, index, keys_need_disambiguation)
                entities["sensors"].append(definition)
        elif is_read_only_statistic(key):
            # Even without L_ prefix, this is a read-only statistic/counter
            # (e.g., storage_fill_yesterday, runtime_total, starts_count)
            _LOGGER.debug(
                "Key '%s.%s' identified as read-only statistic, creating sensor instead of number",
                component_key, key
            )
            definition = create_sensor_definition(component_key, key, data, index, keys_need_disambiguation)
            entities["sensors"].append(definition)
        else:
            # Writable entity (no L_ prefix and not a statistic = writable per API spec)
            if is_select(data):
                definition = create_select_definition(component_key, key, data, index, keys_need_disambiguation)
                entities["selects"].append(definition)
            elif is_binary_sensor(data):
                # Writable binary option (e.g., night_mode with "0:Off|1:On")
                # Treat as select with 2 options instead of binary_sensor
                definition = create_select_definition(component_key, key, data, index, keys_need_disambiguation)
                entities["selects"].append(definition)
            elif is_number(data):
                definition = create_number_definition(component_key, key, data, index, keys_need_disambiguation)
                entities["numbers"].append(definition)
            else:
                # Fallback: treat as read-only sensor
                # (e.g., text fields with 'length' property, or other unsupported writable types)
                _LOGGER.debug(
                    "Writable key '%s.%s' not recognized as select/number, treating as read-only sensor",
                    component_key, key
                )
                definition = create_sensor_definition(component_key, key, data, index, keys_need_disambiguation)
                entities["sensors"].append(definition)
    
    return entities


def discover_all_entities(api_data: dict) -> dict:
    """Discover all entities from complete API response.
    
    Args:
        api_data: Complete API response
    
    Returns:
        Dictionary with all discovered entities organized by type
    """
    all_entities = {
        "sensors": [],
        "binary_sensors": [],
        "selects": [],
        "numbers": []
    }
    
    for component_key, component_data in api_data.items():
        if component_key == "error":
            continue
        
        entities = discover_entities_from_component(component_key, component_data)
        
        # Merge into all_entities
        for entity_type in all_entities:
            all_entities[entity_type].extend(entities[entity_type])
    
    _LOGGER.info(
        "Discovered %d sensors, %d binary sensors, %d selects, %d numbers",
        len(all_entities["sensors"]),
        len(all_entities["binary_sensors"]),
        len(all_entities["selects"]),
        len(all_entities["numbers"])
    )
    
    return all_entities
