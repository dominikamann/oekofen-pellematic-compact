"""Tests for dynamic sensor discovery."""
import pytest
import json
from pathlib import Path
from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    is_binary_sensor,
    is_select,
    is_number,
    parse_select_options,
    infer_device_class,
    infer_binary_device_class,
    infer_icon,
    normalize_unit,
    create_sensor_definition,
    discover_entities_from_component,
    discover_all_entities,
)
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfFrequency, PERCENTAGE


def test_infer_binary_device_class():
    """Test binary sensor device class inference."""
    # Pumps -> RUNNING
    assert infer_binary_device_class({}, "L_pump") == BinarySensorDeviceClass.RUNNING
    assert infer_binary_device_class({}, "L_pummp") == BinarySensorDeviceClass.RUNNING

    # Burner / motor -> RUNNING
    assert infer_binary_device_class({}, "L_br") == BinarySensorDeviceClass.RUNNING
    assert infer_binary_device_class({}, "L_ak") == BinarySensorDeviceClass.RUNNING
    assert infer_binary_device_class({}, "L_stb") == BinarySensorDeviceClass.RUNNING

    # Emergency / fault -> PROBLEM
    assert infer_binary_device_class({}, "L_not") == BinarySensorDeviceClass.PROBLEM

    # USB -> CONNECTIVITY
    assert infer_binary_device_class({}, "L_usb_stick") == BinarySensorDeviceClass.CONNECTIVITY

    # Unknown -> None (generic on/off)
    assert infer_binary_device_class({}, "L_state") is None
    assert infer_binary_device_class({}, "L_unknown") is None

    # Text-based inference for pump
    assert infer_binary_device_class({"text": "Pumpe"}, "L_x") == BinarySensorDeviceClass.RUNNING


def test_binary_sensors_have_correct_device_class():
    """Test that binary sensors discovered from a real fixture get correct device classes."""
    data = {
        "hk1": {
            "hk_info": "heating circuit data",
            "L_pump": {"val": 1, "format": "0:Aus|1:Ein"},
        },
        "pe1": {
            "pe_info": "pellematic data",
            "L_br": {"val": 0, "format": "0:Aus|1:Ein"},
            "L_not": {"val": 0, "format": "0:Aus|1:Ein"},
        },
        "system": {
            "system_info": "system global variables",
            "L_usb_stick": {"val": 0, "format": "0:Aus|1:Ein"},
        },
    }
    from custom_components.oekofen_pellematic_compact.dynamic_discovery import discover_all_entities
    discovered = discover_all_entities(data)
    binary_sensors = {f"{s['component']}_{s['key']}": s for s in discovered['binary_sensors']}

    assert binary_sensors["hk1_L_pump"]["device_class"] == BinarySensorDeviceClass.RUNNING
    assert binary_sensors["pe1_L_br"]["device_class"] == BinarySensorDeviceClass.RUNNING
    assert binary_sensors["pe1_L_not"]["device_class"] == BinarySensorDeviceClass.PROBLEM
    assert binary_sensors["system_L_usb_stick"]["device_class"] == BinarySensorDeviceClass.CONNECTIVITY


def test_is_binary_sensor():
    """Test binary sensor detection."""
    # Binary sensor
    assert is_binary_sensor({"format": "0:Aus|1:Ein"}) is True
    assert is_binary_sensor({"format": "0:Off|1:On"}) is True
    assert is_binary_sensor({"format": "false:No|true:Yes"}) is True
    
    # Not binary sensor
    assert is_binary_sensor({"format": "0:Aus|1:Auto|2:Ein"}) is False
    assert is_binary_sensor({"val": 123}) is False
    assert is_binary_sensor({}) is False


def test_is_select():
    """Test select detection."""
    # Select
    assert is_select({"format": "0:Aus|1:Auto|2:Ein"}) is True
    assert is_select({"format": "0:Off|1:Auto|2:Heat|3:Cool"}) is True
    
    # Not select
    assert is_select({"format": "0:Aus|1:Ein"}) is False
    assert is_select({"val": 123}) is False
    assert is_select({}) is False


def test_is_number():
    """Test number detection."""
    # Number
    assert is_number({"min": 0, "max": 100, "val": 50}) is True
    assert is_number({"min": -10, "max": 40}) is True
    
    # Not number
    assert is_number({"val": 123}) is False
    assert is_number({"max": 100}) is False
    assert is_number({}) is False


def test_parse_select_options():
    """Test parsing select options."""
    assert parse_select_options("0:Aus|1:Auto|2:Ein") == ["0_aus", "1_auto", "2_ein"]
    assert parse_select_options("0:Off|1:On") == ["0_off", "1_on"]
    assert parse_select_options("") == []
    assert parse_select_options("invalid") == []


def test_infer_device_class():
    """Test device class inference."""
    # Temperature
    assert infer_device_class({"unit": "°C"}, "temp") == SensorDeviceClass.TEMPERATURE
    assert infer_device_class({"unit": "K"}, "temp") == SensorDeviceClass.TEMPERATURE
    
    # Energy
    assert infer_device_class({"unit": "kWh"}, "energy") == SensorDeviceClass.ENERGY
    
    # Power
    assert infer_device_class({"unit": "W"}, "power") == SensorDeviceClass.POWER
    assert infer_device_class({"unit": "kW"}, "power") == SensorDeviceClass.POWER
    
    # Weight
    assert infer_device_class({"unit": "kg"}, "weight") == SensorDeviceClass.WEIGHT
    
    # Duration
    assert infer_device_class({"unit": "h"}, "runtime") == SensorDeviceClass.DURATION
    assert infer_device_class({"unit": "min"}, "time") == SensorDeviceClass.DURATION
    
    # Frequency
    assert infer_device_class({"unit": "Hz"}, "freq") == SensorDeviceClass.FREQUENCY
    assert infer_device_class({"unit": "rps"}, "rotation") == SensorDeviceClass.FREQUENCY


def test_infer_icon():
    """Test icon inference."""
    assert infer_icon({"text": "Außentemperatur"}, "L_ambient") == "mdi:thermometer"
    assert infer_icon({"text": "Fehler"}, "L_errors") == "mdi:alert-circle"
    assert infer_icon({"text": "Pumpe"}, "L_pump") == "mdi:pump"
    assert infer_icon({"text": "Solar Kollektor"}, "L_koll") == "mdi:solar-power"
    assert infer_icon({"text": "USB Stick"}, "L_usb") == "mdi:usb-flash-drive"


def test_normalize_unit():
    """Test unit normalization."""
    assert normalize_unit("°C") == UnitOfTemperature.CELSIUS
    assert normalize_unit("Â°C") == UnitOfTemperature.CELSIUS  # Encoding issue fix
    assert normalize_unit("%") == PERCENTAGE
    assert normalize_unit("Hz") == UnitOfFrequency.HERTZ
    assert normalize_unit("rps") == "rps"
    assert normalize_unit("") is None


def test_create_sensor_definition():
    """Test sensor definition creation."""
    data = {
        "val": 79,
        "unit": "°C",
        "factor": 0.1,
        "min": -32768,
        "max": 32767,
        "text": "Außentemperatur"
    }
    
    definition = create_sensor_definition("system", "L_ambient", data)
    
    assert definition["component"] == "system"
    assert definition["key"] == "L_ambient"
    assert definition["name"] == "Außentemperatur"
    assert definition["unique_id"] == "system_L_ambient"
    assert definition["unit"] == UnitOfTemperature.CELSIUS
    assert definition["factor"] == 0.1
    assert definition["device_class"] == SensorDeviceClass.TEMPERATURE


def test_discover_entities_from_component():
    """Test entity discovery from single component."""
    component_data = {
        "hk_info": "heating circuit data",
        "L_roomtemp_act": {
            "val": 225,
            "unit": "°C",
            "factor": 0.1,
            "min": -32768,
            "max": 32767,
            "text": "Raumtemperatur"
        },
        "L_pump": {
            "val": 1,
            "format": "0:Aus|1:Ein",
            "text": "HK Pumpe"
        },
        "mode_auto": {
            "val": 1,
            "format": "0:Aus|1:Auto|2:Heizen|3:Absenken",
            "text": "Betriebsart"
        },
        "temp_heat": {
            "val": 200,
            "unit": "°C",
            "factor": 0.1,
            "min": 100,
            "max": 400,
            "text": "Raumtemp Heizen"
        }
    }
    
    entities = discover_entities_from_component("hk1", component_data)
    
    # Should find 1 sensor, 1 binary sensor, 1 select, 1 number
    assert len(entities["sensors"]) == 1
    assert len(entities["binary_sensors"]) == 1
    assert len(entities["selects"]) == 1
    assert len(entities["numbers"]) == 1
    
    # Check sensor - now includes component name (in English)
    assert entities["sensors"][0]["key"] == "L_roomtemp_act"
    assert entities["sensors"][0]["name"] == "Heating Circuit 1 Raumtemperatur"
    
    # Check binary sensor
    assert entities["binary_sensors"][0]["key"] == "L_pump"
    
    # Check select
    assert entities["selects"][0]["key"] == "mode_auto"
    assert len(entities["selects"][0]["options"]) == 4
    
    # Check number
    assert entities["numbers"][0]["key"] == "temp_heat"
    assert entities["numbers"][0]["min_value"] == 100
    assert entities["numbers"][0]["max_value"] == 400


def test_discover_all_entities_basic():
    """Test full entity discovery with basic setup."""
    fixture_path = Path(__file__).parent / "fixtures" / "api_response_basic.json"
    with open(fixture_path, encoding="utf-8") as f:
        api_data = json.load(f)
    
    entities = discover_all_entities(api_data)
    
    # Should find various entities
    assert len(entities["sensors"]) > 0
    assert len(entities["binary_sensors"]) > 0
    assert len(entities["selects"]) > 0
    assert len(entities["numbers"]) > 0
    
    # Check that system sensors are found
    system_sensors = [s for s in entities["sensors"] if s["component"] == "system"]
    assert len(system_sensors) > 0
    
    # Check that heating circuit sensors are found
    hk_sensors = [s for s in entities["sensors"] if s["component"] == "hk1"]
    assert len(hk_sensors) > 0


def test_discover_all_entities_with_solar():
    """Test discovery with solar components."""
    fixture_path = Path(__file__).parent / "fixtures" / "api_response_with_se_ml.json"
    with open(fixture_path, encoding="utf-8") as f:
        api_data = json.load(f)
    
    entities = discover_all_entities(api_data)
    
    # Should find solar entities
    sk_sensors = [s for s in entities["sensors"] if s["component"] == "sk1"]
    se_sensors = [s for s in entities["sensors"] if s["component"] == "se1"]
    
    assert len(sk_sensors) > 0
    assert len(se_sensors) > 0


def test_discover_all_entities_green_mode():
    """Test discovery with green mode and heat pump."""
    fixture_path = Path(__file__).parent / "fixtures" / "api_response_green_kn.json"
    with open(fixture_path, encoding="utf-8") as f:
        api_data = json.load(f)
    
    entities = discover_all_entities(api_data)
    
    # Should find multiple heating circuits
    hk_components = set()
    for sensor in entities["sensors"]:
        if sensor["component"].startswith("hk"):
            hk_components.add(sensor["component"])
    
    assert len(hk_components) >= 4  # Has hk1-hk4
    
    # Should find solar entities
    sk_components = set()
    for sensor in entities["sensors"]:
        if sensor["component"].startswith("sk"):
            sk_components.add(sensor["component"])
    
    assert len(sk_components) >= 3  # Has sk1-sk3


def test_multilingual_support():
    """Test that names are taken from API (multilingual)."""
    # German
    data_de = {"val": 100, "text": "Außentemperatur"}
    definition_de = create_sensor_definition("system", "L_ambient", data_de)
    assert definition_de["name"] == "Außentemperatur"
    
    # French
    data_fr = {"val": 100, "text": "Température extérieure"}
    definition_fr = create_sensor_definition("system", "L_ambient", data_fr)
    assert definition_fr["name"] == "Température extérieure"
    
    # English (fallback to key if no text)
    data_en = {"val": 100}
    definition_en = create_sensor_definition("system", "L_ambient", data_en)
    assert definition_en["name"] == "L_ambient"
