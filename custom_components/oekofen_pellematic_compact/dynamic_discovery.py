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
from homeassistant.components.number import NumberDeviceClass

_LOGGER = logging.getLogger(__name__)

# Component name translations for better entity names
COMPONENT_NAMES = {
    "system": "System",
    "hk": "Heizkreis",  # Heating Circuit
    "pe": "Pellematic",  # Pellematic Heater
    "pu": "Pufferspeicher",  # Buffer Storage
    "ww": "Warmwasser",  # Hot Water
    "sk": "Solar SK",  # Solar Collector SK
    "se": "Solar SE",  # Solar Collector SE
    "wp": "Wärmepumpe",  # Heat Pump
    "circ": "Zirkulation",  # Circulator
    "weather": "Wetter",  # Weather
    "forecast": "Prognose",  # Forecast
    "power": "Smart PV",  # Smart PV
    "stirling": "Stirling",  # Stirling Engine
}

# Keys to ignore (metadata/info fields)
IGNORE_KEYS = {
    "system_info",
    "hk_info",
    "pe_info",
    "pu_info",
    "ww_info",
    "sk_info",
    "se_info",
    "wp_info",
    "circ_info",
    "weather_info",
    "forecast_info",
    "power_info",
}


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
    """Check if data represents a number entity."""
    # Numbers have min and max values and are writable (no L_ prefix)
    return "min" in data and "max" in data


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
    
    # Temperature
    if unit in ("°C", "K"):
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
    
    # Total/Counter sensors
    if any(word in key_lower for word in ["total", "gesamt", "counter", "starts", "runtime", "laufzeit"]):
        return SensorStateClass.TOTAL_INCREASING
    
    # Measurement sensors (temperature, power, energy, frequency, etc.)
    if "val" in data and unit:
        # These are typically measurement sensors
        if unit in ("°C", "K", "W", "kW", "kWh", "kg", "Pa", "bar", "V", "A", "Hz", "rps"):
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
    
    # Map common units
    unit_map = {
        "Â°C": UnitOfTemperature.CELSIUS,
        "°C": UnitOfTemperature.CELSIUS,
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
    }
    
    return unit_map.get(unit, unit)


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
    index: int = 0
) -> dict:
    """Create sensor definition from API data.
    
    Args:
        component: Component name (e.g., "hk1", "pe1", "system")
        key: Sensor key (e.g., "L_temp_act")
        data: API data for this sensor
        index: Index for numbered components (for display name)
    
    Returns:
        Dictionary with sensor configuration
    """
    # Get name from API or use key as fallback
    base_name = data.get("text", key)
    
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
    index: int = 0
) -> dict:
    """Create number entity definition from API data."""
    definition = create_sensor_definition(component, key, data, index)
    definition["device_class"] = infer_number_device_class(data, key)
    definition["step"] = 0.1 if definition["unit"] in (UnitOfTemperature.CELSIUS, UnitOfTemperature.KELVIN) else 1
    
    return definition


def create_select_definition(
    component: str,
    key: str,
    data: dict,
    index: int = 0
) -> dict:
    """Create select entity definition from API data."""
    definition = create_sensor_definition(component, key, data, index)
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
            # Read-only sensor
            if is_binary_sensor(data):
                definition = create_sensor_definition(component_key, key, data, index)
                entities["binary_sensors"].append(definition)
            else:
                definition = create_sensor_definition(component_key, key, data, index)
                entities["sensors"].append(definition)
        else:
            # Writable entity
            if is_select(data):
                definition = create_select_definition(component_key, key, data, index)
                entities["selects"].append(definition)
            elif is_number(data):
                definition = create_number_definition(component_key, key, data, index)
                entities["numbers"].append(definition)
    
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
