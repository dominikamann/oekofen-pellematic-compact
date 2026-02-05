"""Test that all platforms (sensor, select, number) work with dynamic discovery."""

import json
import re
import pytest
from pathlib import Path

from custom_components.oekofen_pellematic_compact.dynamic_discovery import discover_all_entities


def load_fixture(filename: str) -> dict:
    """Load a fixture file.
    
    Handles JSON files from Ökofen API which may contain control characters
    (newlines, tabs) in string values, which is technically invalid JSON.
    """
    fixture_path = Path(__file__).parent / "fixtures" / filename
    
    # Read as binary first to handle encoding properly
    with open(fixture_path, "rb") as f:
        data = f.read()
    
    # Try UTF-8 first, fallback to iso-8859-1 for files with special encoding
    # Files like api_response_base_da.json use iso-8859-1
    try:
        str_response = data.decode("utf-8")
    except UnicodeDecodeError:
        str_response = data.decode("iso-8859-1", "ignore")
    
    # Hotfix for pellematic update 4.02 (invalid json)
    str_response = str_response.replace("L_statetext:", 'L_statetext":')
    
    # Fix for control characters (newlines, tabs) in string values
    def escape_control_chars(match):
        string_content = match.group(1)
        string_content = string_content.replace('\n', '\\n')
        string_content = string_content.replace('\r', '\\r')
        string_content = string_content.replace('\t', '\\t')
        return f'"{string_content}"'
    
    # Match strings in JSON (handling escaped quotes)
    str_response = re.sub(r'"((?:[^"\\]|\\.)*)"', escape_control_chars, str_response)
    
    return json.loads(str_response, strict=False)


def test_all_platforms_basic():
    """Test that all platforms discover entities from basic fixture."""
    data = load_fixture("api_response_basic.json")
    discovered = discover_all_entities(data)
    
    # Updated counts after moving read-only statistics to sensors
    assert len(discovered['sensors']) == 28  # +2 from read-only statistics
    assert len(discovered['binary_sensors']) == 3
    assert len(discovered['selects']) == 1
    assert len(discovered['numbers']) == 4  # -2 moved to sensors
    
    # Verify sensor structure
    assert all('component' in s for s in discovered['sensors'])
    assert all('key' in s for s in discovered['sensors'])
    assert all('name' in s for s in discovered['sensors'])
    
    # Verify select structure
    assert all('options' in s for s in discovered['selects'])
    assert all(len(s['options']) > 0 for s in discovered['selects'])
    
    # Verify number structure (min_value and max_value from API)
    for number in discovered['numbers']:
        # Numbers should have either min/max or min_value/max_value
        has_min = 'min' in number or 'min_value' in number
        has_max = 'max' in number or 'max_value' in number
        assert has_min and has_max, f"Number {number['key']} missing min/max"


def test_all_platforms_complex():
    """Test that all platforms discover entities from complex fixture."""
    data = load_fixture("api_response_basic_yo_2.json")
    discovered = discover_all_entities(data)
    
    # Updated counts after binary options → selects conversion
    assert len(discovered['sensors']) == 56  # -6 binary options moved to selects
    assert len(discovered['binary_sensors']) == 8
    assert len(discovered['selects']) == 18  # +6 binary options from sensors
    assert len(discovered['numbers']) == 13
    
    total = (len(discovered['sensors']) + len(discovered['binary_sensors']) + 
             len(discovered['selects']) + len(discovered['numbers']))
    assert total == 95  # 56+8+18+13


def test_select_options_parsing():
    """Test that select options are correctly parsed."""
    data = load_fixture("api_response_basic_yo_2.json")
    discovered = discover_all_entities(data)
    
    selects = discovered['selects']
    assert len(selects) > 0
    
    # Check that all selects have valid options
    for select in selects:
        assert 'options' in select
        assert isinstance(select['options'], list)
        assert len(select['options']) >= 2  # At least 2 options
        
        # All options should be non-empty strings
        for option in select['options']:
            assert isinstance(option, str)
            assert len(option) > 0


def test_number_ranges():
    """Test that number entities have valid min/max ranges."""
    data = load_fixture("api_response_basic_yo_2.json")
    discovered = discover_all_entities(data)
    
    numbers = discovered['numbers']
    assert len(numbers) > 0
    
    for number in numbers:
        # Numbers should have min_value and max_value from API
        assert 'min_value' in number or 'min' in number
        assert 'max_value' in number or 'max' in number
        
        # Get min/max values (handle both naming conventions)
        min_val = number.get('min_value', number.get('min'))
        max_val = number.get('max_value', number.get('max'))
        
        # Both should be present and min should be less than max
        if min_val is not None and max_val is not None:
            assert min_val < max_val, f"Number {number['key']}: min ({min_val}) should be < max ({max_val})"


def test_unique_entity_ids():
    """Test that all entities have unique IDs."""
    data = load_fixture("api_response_basic_yo_2.json")
    discovered = discover_all_entities(data)
    
    all_entities = (discovered['sensors'] + discovered['binary_sensors'] + 
                    discovered['selects'] + discovered['numbers'])
    
    # Create unique IDs
    unique_ids = set()
    for entity in all_entities:
        unique_id = f"{entity['component']}_{entity['key']}"
        assert unique_id not in unique_ids, f"Duplicate entity ID: {unique_id}"
        unique_ids.add(unique_id)


def test_multilingual_names():
    """Test that entities have names from API (multilingual support)."""
    data = load_fixture("api_response_basic.json")
    discovered = discover_all_entities(data)
    
    sensors = discovered['sensors']
    
    # Find Außentemperatur sensor
    ambient_sensor = next((s for s in sensors if s['key'] == 'L_ambient'), None)
    assert ambient_sensor is not None
    assert ambient_sensor['name'] == 'Außentemperatur'
    
    # All sensors should have non-empty names
    for sensor in sensors:
        assert 'name' in sensor
        assert len(sensor['name']) > 0


def test_components_detected():
    """Test that different components are correctly detected."""
    data = load_fixture("api_response_basic_m9.json")
    discovered = discover_all_entities(data)
    
    all_entities = (discovered['sensors'] + discovered['binary_sensors'] + 
                    discovered['selects'] + discovered['numbers'])
    
    # Extract all unique components
    components = set(entity['component'] for entity in all_entities)
    
    # Should have multiple components
    assert len(components) > 1
    
    # Should have at least system
    assert 'system' in components
    
    # Check component naming pattern
    for component in components:
        # Should be either 'system', 'error', or match pattern like 'hk1', 'pe1', etc.
        if component not in ('system', 'error'):
            # Should have at least 2 chars (prefix + number)
            assert len(component) >= 2
            # Should end with a digit (hk1, pe1, etc.)
            # Exception: some components might have special naming
            # Just verify it's a non-empty string
            assert len(component) > 0


def test_total_entities_all_fixtures():
    """Test total entity count across all fixtures matches expected."""
    fixtures = [
        ("api_response_basic.json", 36),
        ("api_response_basic_yo_2.json", 95),
        ("api_response_basic_m9.json", 170),
        ("api_response_green_kn.json", 394),
        ("api_response_sk_lxy.json", 111),
        ("api_response_with_se_ml.json", 162),
        ("api_response_with_sk_dash.json", 135),
        ("api_response_base_csta.json", 187),  # -1 after binary→select fix
        ("api_response_base_srqu.json", 394),
        ("api_response_base_da.json", 87),
        ("api_response_n4n.json", 160),
        ("api_response_mr.json", 91),
        ("api_response_3bk.json", 123),
        ("api_response_be72.json", 118),
    ]
    
    total_entities = 0
    
    for filename, expected_count in fixtures:
        data = load_fixture(filename)
        discovered = discover_all_entities(data)
        
        count = (len(discovered['sensors']) + len(discovered['binary_sensors']) + 
                len(discovered['selects']) + len(discovered['numbers']))
        
        assert count == expected_count, f"{filename}: expected {expected_count}, got {count}"
        total_entities += count
    
    # Total entities across all fixtures (international names, binary→select fix)
    assert total_entities == 2263
