"""Tests for auto-discovery functionality."""
import pytest
from custom_components.oekofen_pellematic_compact import discover_components_from_api
from custom_components.oekofen_pellematic_compact.const import (
    CONF_NUM_OF_HEATING_CIRCUIT,
    CONF_NUM_OF_HOT_WATER,
    CONF_NUM_OF_PELLEMATIC_HEATER,
    CONF_NUM_OF_BUFFER_STORAGE,
    CONF_NUM_OF_SMART_PV_SE,
    CONF_NUM_OF_SMART_PV_SK,
    CONF_NUM_OF_HEAT_PUMPS,
    CONF_NUM_OF_WIRELESS_SENSORS,
    CONF_SOLAR_CIRCUIT,
    CONF_STIRLING,
    CONF_CIRCULATOR,
    CONF_SMART_PV,
)


def test_discovery_basic_setup():
    """Test discovery with basic setup (1 HK, 1 WW, 1 PE, 1 PU)."""
    # Real API response from a basic Pellematic Compact setup
    api_data = {
        "system": {
            "system_info": "system global variables",
            "L_ambient": {"val": -69, "unit": "°C", "factor": 0.1},
            "mode": {"val": 1, "format": "0:Aus|1:Auto|2:Warmwasser"},
        },
        "hk1": {
            "hk_info": "heating circuit data",
            "L_roomtemp_act": {"val": 0, "unit": "°C", "factor": 0.1},
        },
        "pu1": {
            "pu_info": "accu data",
            "L_tpo_act": {"val": 636, "unit": "°C", "factor": 0.1},
        },
        "ww1": {
            "ww_info": "domestic hot water data",
            "L_temp_set": {"val": 370, "unit": "°C", "factor": 0.1},
        },
        "pe1": {
            "pe_info": "pellematic data",
            "L_temp_act": {"val": 633, "unit": "°C", "factor": 0.1},
        },
        "error": {},
    }

    discovered = discover_components_from_api(api_data)

    assert discovered[CONF_NUM_OF_HEATING_CIRCUIT] == 1
    assert discovered[CONF_NUM_OF_HOT_WATER] == 1
    assert discovered[CONF_NUM_OF_PELLEMATIC_HEATER] == 1
    assert discovered[CONF_NUM_OF_BUFFER_STORAGE] == 1
    
    # These should not be present
    assert CONF_NUM_OF_SMART_PV_SE not in discovered
    assert CONF_NUM_OF_SMART_PV_SK not in discovered
    assert CONF_NUM_OF_HEAT_PUMPS not in discovered
    assert CONF_SOLAR_CIRCUIT not in discovered
    assert CONF_STIRLING not in discovered
    assert CONF_CIRCULATOR not in discovered
    assert CONF_SMART_PV not in discovered


def test_discovery_multiple_heating_circuits():
    """Test discovery with multiple heating circuits."""
    api_data = {
        "system": {},
        "hk1": {"hk_info": "heating circuit data"},
        "hk2": {"hk_info": "heating circuit data"},
        "hk3": {"hk_info": "heating circuit data"},
        "ww1": {"ww_info": "domestic hot water data"},
        "pe1": {"pe_info": "pellematic data"},
        "pu1": {"pu_info": "accu data"},
    }

    discovered = discover_components_from_api(api_data)

    assert discovered[CONF_NUM_OF_HEATING_CIRCUIT] == 3
    assert discovered[CONF_NUM_OF_HOT_WATER] == 1
    assert discovered[CONF_NUM_OF_PELLEMATIC_HEATER] == 1
    assert discovered[CONF_NUM_OF_BUFFER_STORAGE] == 1


def test_discovery_with_solar():
    """Test discovery with solar components."""
    api_data = {
        "system": {},
        "hk1": {},
        "ww1": {},
        "pe1": {},
        "pu1": {},
        "sk1": {"sk_info": "solar collector data"},
        "sk2": {"sk_info": "solar collector data"},
        "se1": {"se_info": "solar electronic data"},
    }

    discovered = discover_components_from_api(api_data)

    assert discovered[CONF_NUM_OF_SMART_PV_SK] == 2
    assert discovered[CONF_NUM_OF_SMART_PV_SE] == 1
    assert discovered[CONF_SOLAR_CIRCUIT] is True


def test_discovery_with_heat_pump():
    """Test discovery with heat pump."""
    api_data = {
        "system": {},
        "hk1": {},
        "ww1": {},
        "pe1": {},
        "pu1": {},
        "wp1": {"wp_info": "heat pump data"},
        "wp2": {"wp_info": "heat pump data"},
    }

    discovered = discover_components_from_api(api_data)

    assert discovered[CONF_NUM_OF_HEAT_PUMPS] == 2


def test_discovery_with_special_components():
    """Test discovery with Stirling, Circulator and Smart PV."""
    api_data = {
        "system": {},
        "hk1": {},
        "ww1": {},
        "pe1": {},
        "pu1": {},
        "stirling": {"L_temp_1": {"val": 100}},
        "circ1": {"L_temp": {"val": 50}},
        "power": {"L_usage": {"val": 1000}},
    }

    discovered = discover_components_from_api(api_data)

    assert discovered[CONF_STIRLING] is True
    assert discovered[CONF_CIRCULATOR] is True
    assert discovered[CONF_SMART_PV] is True


def test_discovery_with_wireless_sensors():
    """Test discovery with wireless sensors."""
    api_data = {
        "system": {},
        "hk1": {},
        "ww1": {},
        "pe1": {},
        "pu1": {},
        "wireless1": {"L_wireless_temp": {"val": 200}},
        "wireless2": {"L_wireless_temp": {"val": 210}},
        "wireless3": {"L_wireless_temp": {"val": 220}},
    }

    discovered = discover_components_from_api(api_data)

    assert discovered[CONF_NUM_OF_WIRELESS_SENSORS] == 3


def test_discovery_empty_api_response():
    """Test discovery with empty API response."""
    api_data = {}

    discovered = discover_components_from_api(api_data)

    assert discovered == {}


def test_discovery_only_system():
    """Test discovery with only system data."""
    api_data = {
        "system": {"L_ambient": {"val": -50}},
    }

    discovered = discover_components_from_api(api_data)

    # No components should be discovered, only system exists
    assert CONF_NUM_OF_HEATING_CIRCUIT not in discovered
    assert CONF_NUM_OF_HOT_WATER not in discovered


def test_discovery_complex_setup():
    """Test discovery with complex multi-component setup."""
    api_data = {
        "system": {},
        "hk1": {},
        "hk2": {},
        "hk3": {},
        "ww1": {},
        "ww2": {},
        "pe1": {},
        "pe2": {},
        "pu1": {},
        "pu2": {},
        "sk1": {},
        "se1": {},
        "wp1": {},
        "wireless1": {},
        "wireless2": {},
        "stirling": {},
        "circ1": {},
        "power": {},
    }

    discovered = discover_components_from_api(api_data)

    assert discovered[CONF_NUM_OF_HEATING_CIRCUIT] == 3
    assert discovered[CONF_NUM_OF_HOT_WATER] == 2
    assert discovered[CONF_NUM_OF_PELLEMATIC_HEATER] == 2
    assert discovered[CONF_NUM_OF_BUFFER_STORAGE] == 2
    assert discovered[CONF_NUM_OF_SMART_PV_SK] == 1
    assert discovered[CONF_NUM_OF_SMART_PV_SE] == 1
    assert discovered[CONF_NUM_OF_HEAT_PUMPS] == 1
    assert discovered[CONF_NUM_OF_WIRELESS_SENSORS] == 2
    assert discovered[CONF_SOLAR_CIRCUIT] is True
    assert discovered[CONF_STIRLING] is True
    assert discovered[CONF_CIRCULATOR] is True
    assert discovered[CONF_SMART_PV] is True


def test_discovery_ignores_non_numeric_suffixes():
    """Test that discovery ignores keys with non-numeric suffixes."""
    api_data = {
        "system": {},
        "hk1": {},
        "hk_test": {},  # Should be ignored
        "ww1": {},
        "ww_info": {},  # Should be ignored
        "pe1": {},
        "pe_data": {},  # Should be ignored
    }

    discovered = discover_components_from_api(api_data)

    assert discovered[CONF_NUM_OF_HEATING_CIRCUIT] == 1
    assert discovered[CONF_NUM_OF_HOT_WATER] == 1
    assert discovered[CONF_NUM_OF_PELLEMATIC_HEATER] == 1
