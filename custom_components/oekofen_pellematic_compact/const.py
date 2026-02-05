"""Constants for the Ökofen Pellematic Compact integration."""

# Domain and basic configuration
DOMAIN = "oekofen_pellematic_compact"
DEFAULT_NAME = "Pellematic"
DEFAULT_SCAN_INTERVAL = 30

# Default values for configuration
DEFAULT_NUM_OF_HEATING_CIRCUIT = 1
DEFAULT_NUM_OF_HOT_WATER = 1
DEFAULT_NUM_OF_PELLEMATIC_HEATER = 1
DEFAULT_NUM_OF_SMART_PV_SE = 0
DEFAULT_NUM_OF_SMART_PV_SK = 0
DEFAULT_NUM_OF_HEAT_PUMPS = 0
DEFAULT_NUM_OF_WIRELESS_SENSORS = 0
DEFAULT_NUM_OF_BUFFER_STORAGE = 1  # Important: 1 not 0

# Configuration keys
CONF_SOLAR_CIRCUIT = "solar_circuit"
CONF_CIRCULATOR = "circulator"
CONF_SMART_PV = "smart_pv"
CONF_STIRLING = "stirling"
CONF_CHARSET = "charset"
CONF_NUM_OF_HEATING_CIRCUIT = "num_of_heating_circuits"
CONF_NUM_OF_PELLEMATIC_HEATER = "num_of_pellematic_heaters"
CONF_NUM_OF_SMART_PV_SE = "num_of_smart_pv_se_count"
CONF_NUM_OF_HEAT_PUMPS = "num_of_heat_pumps_count"
CONF_NUM_OF_SMART_PV_SK = "num_of_smart_pv_sk_count"
CONF_NUM_OF_HOT_WATER = "num_of_hot_water"
CONF_NUM_OF_WIRELESS_SENSORS = "num_of_wireless_sensors"
CONF_NUM_OF_BUFFER_STORAGE = "num_of_buffer_storage"
CONF_SOLAREDGE_HUB = "solaredge_hub"

# Default connection settings
DEFAULT_HOST = "http://[YOU_IP]:4321/[YOUR_PASSWORD]/all"
DEFAULT_CHARSET = "iso-8859-1"

# Device attributes
ATTR_STATUS_DESCRIPTION = "status_description"
ATTR_MANUFACTURER = "Ökofen"
ATTR_MODEL = "Pellematic Compact"


def get_api_value(data_field, default=None):
    """Extract value from API data field.
    
    Supports multiple API formats:
    - New format with dict: {"val": 123, "unit": "°C", "factor": 0.1, ...}
    - New format with string values: {"val": "123", ...}
    - Old format: 123 (direct value as int/float)
    - Old old format: "123" (direct string value)
    
    Args:
        data_field: The API data field (dict or direct value)
        default: Default value if field is None or missing "val" key
        
    Returns:
        The extracted value (converted to int/float if string), or default
    """
    if data_field is None:
        return default
        
    # New format: {"val": ..., ...}
    if isinstance(data_field, dict):
        val = data_field.get("val", default)
        if isinstance(val, str):
            # Try to convert string to number
            try:
                return int(val)
            except ValueError:
                try:
                    return float(val)
                except ValueError:
                    # Return as string if conversion fails
                    return val
        return val
    
    # Old format: direct value (could be int, float, or string)
    if isinstance(data_field, str):
        # Try to convert string to number
        try:
            return int(data_field)
        except ValueError:
            try:
                return float(data_field)
            except ValueError:
                # Return as string if conversion fails (e.g., "true", "false")
                return data_field
    
    # Already a number or other type
    return data_field

# Data coordinator
DATA_COORDINATOR = "coordinator"

# ============================================================================
# NOTE: All sensor, binary sensor, select, and number entity definitions
# have been removed in favor of dynamic discovery from API metadata.
# See dynamic_discovery.py for the new approach.
#
# Previous approach (deprecated):
# - Hard-coded sensor definitions in SYSTEM_SENSOR_TYPES, HK_SENSOR_TYPES, etc.
# - ~1300 lines of repetitive entity definitions
# - Required manual updates for new Ökofen features
#
# New approach (current):
# - Automatic discovery from API responses
# - Entities created dynamically based on API metadata (text, unit, factor, min, max, format)
# - Multilingual support (names from API)
# - Future-proof for new features
#
# Migration: All entity creation now happens in the platform files
# (sensor.py, select.py, number.py) using discover_all_entities()
# ============================================================================
