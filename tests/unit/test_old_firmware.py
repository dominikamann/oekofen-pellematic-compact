"""Test old firmware without writeable flag (v3.24.0)."""

import pytest
from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
)


def test_old_firmware_v324_number_entities():
    """Test that old firmware v3.24.0 correctly discovers number entities.
    
    Old firmware does not have 'writeable' flag, but number entities
    should still be detected by min/max presence.
    """
    # Minimal test data from real v3.24.0 firmware (reported by Peter)
    api_data = {
        "ww1": {
            "ww_info": "domestic hot water data",
            "L_temp_set": {"val": "700", "unit": "°C", "factor": 0.1, "min": "-32768", "max": "32767", "text": "Wassertemp Soll"},
            "temp_min_set": {"val": "450", "unit": "°C", "factor": 0.1, "min": "80", "max": "800", "text": "Wassertemp Min"},
            "temp_max_set": {"val": "700", "unit": "°C", "factor": 0.1, "min": "80", "max": "800", "text": "Wassertemp Soll"},
            "smartstart": {"val": "0", "unit": "min", "factor": 1, "min": "0", "max": "90", "text": "Intelligenter Start"},
            "mode_auto": {"val": "1", "format": "0:Aus|1:Auto|2:Ein", "text": "Betriebsart"},
        },
        "hk1": {
            "hk_info": "heating circuit data",
            "L_roomtemp_act": {"val": "205", "unit": "°C", "factor": 0.1, "min": "-32768", "max": "32767", "text": "Raumtemperatur"},
            "temp_setback": {"val": "190", "unit": "°C", "factor": 0.1, "min": "100", "max": "400", "text": "Raumtemp Absenken"},
            "temp_heat": {"val": "210", "unit": "°C", "factor": 0.1, "min": "100", "max": "400", "text": "Raumtemp Heizen"},
        }
    }
    
    discovered = discover_all_entities(api_data)
    
    # Verify number entities are detected
    number_ids = [n["unique_id"] for n in discovered["numbers"]]
    
    # These should all be number entities (writable with min/max)
    assert "ww1_temp_min_set" in number_ids, "temp_min_set should be a number entity"
    assert "ww1_temp_max_set" in number_ids, "temp_max_set should be a number entity"
    assert "ww1_smartstart" in number_ids, "smartstart should be a number entity"
    assert "hk1_temp_setback" in number_ids, "temp_setback should be a number entity"
    assert "hk1_temp_heat" in number_ids, "temp_heat should be a number entity"
    
    # Select entities
    select_ids = [s["unique_id"] for s in discovered["selects"]]
    assert "ww1_mode_auto" in select_ids, "mode_auto should be a select"
    
    # Read-only sensors (L_ prefix)
    sensor_ids = [s["unique_id"] for s in discovered["sensors"]]
    assert "ww1_L_temp_set" in sensor_ids, "L_temp_set should be a sensor (readonly)"
    assert "hk1_L_roomtemp_act" in sensor_ids, "L_roomtemp_act should be a sensor (readonly)"


def test_old_firmware_no_writeable_flag():
    """Test that absence of writeable flag doesn't break number detection."""
    api_data = {
        "test": {
            # Number entity without writeable flag (old firmware)
            "temp_set": {"val": "500", "unit": "°C", "factor": 0.1, "min": "100", "max": "900", "text": "Temperature"},
            # Read-only with min/max (should be sensor due to L_ prefix)
            "L_temp_act": {"val": "450", "unit": "°C", "factor": 0.1, "min": "-32768", "max": "32767", "text": "Actual Temp"},
        }
    }
    
    discovered = discover_all_entities(api_data)
    
    # temp_set should be number (no L_ prefix + has min/max)
    assert len(discovered["numbers"]) == 1
    assert discovered["numbers"][0]["unique_id"] == "test_temp_set"
    
    # L_temp_act should be sensor (L_ prefix = readonly)
    sensor_ids = [s["unique_id"] for s in discovered["sensors"]]
    assert "test_L_temp_act" in sensor_ids
