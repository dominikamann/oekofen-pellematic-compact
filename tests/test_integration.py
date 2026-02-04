"""Integration tests for dynamic discovery with mocked Hub."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from pathlib import Path

from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
)


@pytest.fixture
def mock_hub():
    """Create a mock Hub with API data."""
    hub = MagicMock()
    hub.name = "Pellematic Test"
    hub.data = {}
    
    # Load real API data
    fixture_path = Path(__file__).parent / "fixtures" / "api_response_basic.json"
    with open(fixture_path, "r") as f:
        hub.data = json.load(f)
    
    # Mock async_update method
    async def mock_update():
        return hub.data
    
    hub.async_update = AsyncMock(side_effect=mock_update)
    return hub


@pytest.mark.asyncio
async def test_integration_sensor_platform(mock_hub):
    """Test that sensor platform can use dynamic discovery."""
    # Simulate what sensor.py does
    initial_data = await mock_hub.async_update()
    assert initial_data is not None
    
    # Discover all entities
    discovered = discover_all_entities(initial_data)
    
    # Verify we got entities
    assert len(discovered["sensors"]) > 0
    assert len(discovered["binary_sensors"]) >= 0
    
    # Verify sensor structure matches what PellematicSensor expects
    for sensor in discovered["sensors"][:3]:  # Test first 3
        assert "component" in sensor
        assert "key" in sensor
        assert "name" in sensor
        assert "unique_id" in sensor
        assert "icon" in sensor
        assert "device_class" in sensor  # Can be None
        assert "unit" in sensor  # Can be None
        assert "state_class" in sensor  # Can be None


@pytest.mark.asyncio
async def test_integration_select_platform(mock_hub):
    """Test that select platform can use dynamic discovery."""
    initial_data = await mock_hub.async_update()
    discovered = discover_all_entities(initial_data)
    
    # Verify we got selects
    assert len(discovered["selects"]) > 0
    
    # Verify select structure
    for select in discovered["selects"][:3]:
        assert "component" in select
        assert "key" in select
        assert "name" in select
        assert "unique_id" in select
        assert "icon" in select
        assert "options" in select
        assert isinstance(select["options"], list)
        assert len(select["options"]) >= 2  # At least 2 options


@pytest.mark.asyncio
async def test_integration_number_platform(mock_hub):
    """Test that number platform can use dynamic discovery."""
    initial_data = await mock_hub.async_update()
    discovered = discover_all_entities(initial_data)
    
    # Verify we got numbers
    assert len(discovered["numbers"]) > 0
    
    # Verify number structure
    for number in discovered["numbers"][:3]:
        assert "component" in number
        assert "key" in number
        assert "name" in number
        assert "unique_id" in number
        assert "icon" in number
        assert "min_value" in number
        assert "max_value" in number
        assert "step" in number
        assert isinstance(number["min_value"], (int, float))
        assert isinstance(number["max_value"], (int, float))


@pytest.mark.asyncio
async def test_integration_entity_uniqueness(mock_hub):
    """Test that all entity IDs are unique across all platforms."""
    initial_data = await mock_hub.async_update()
    discovered = discover_all_entities(initial_data)
    
    # Collect all unique IDs
    all_ids = []
    all_ids.extend([s["unique_id"] for s in discovered["sensors"]])
    all_ids.extend([s["unique_id"] for s in discovered["binary_sensors"]])
    all_ids.extend([s["unique_id"] for s in discovered["selects"]])
    all_ids.extend([s["unique_id"] for s in discovered["numbers"]])
    
    # Verify uniqueness
    assert len(all_ids) == len(set(all_ids)), "Duplicate unique_id found!"


@pytest.mark.asyncio
async def test_integration_multilingual_support(mock_hub):
    """Test that multilingual names work correctly."""
    initial_data = await mock_hub.async_update()
    discovered = discover_all_entities(initial_data)
    
    # Find entities with multilingual text
    sensors_with_text = [
        s for s in discovered["sensors"]
        if s.get("name") and not s["name"].startswith(s["component"])
    ]
    
    # Should have at least some named entities
    assert len(sensors_with_text) > 10
    
    # Verify names are human-readable
    for sensor in sensors_with_text[:5]:
        name = sensor["name"]
        assert len(name) > 2
        # Should not be just the key
        assert name != sensor["key"]


@pytest.mark.asyncio
async def test_integration_backwards_compatibility(mock_hub):
    """Test that entity IDs remain stable for backwards compatibility."""
    initial_data = await mock_hub.async_update()
    discovered = discover_all_entities(initial_data)
    
    # Check some known entity IDs that should exist
    all_entities = (
        discovered["sensors"] +
        discovered["binary_sensors"] +
        discovered["selects"] +
        discovered["numbers"]
    )
    
    unique_ids = [e["unique_id"] for e in all_entities]
    
    # These are common entity IDs that should exist in most systems
    expected_patterns = ["system_", "hk1_", "pe1_", "ww1_"]
    
    for pattern in expected_patterns:
        matching = [uid for uid in unique_ids if uid.startswith(pattern)]
        assert len(matching) > 0, f"No entities found with pattern {pattern}"


@pytest.mark.asyncio
async def test_integration_component_detection(mock_hub):
    """Test that all major components are detected."""
    initial_data = await mock_hub.async_update()
    discovered = discover_all_entities(initial_data)
    
    all_entities = (
        discovered["sensors"] +
        discovered["binary_sensors"] +
        discovered["selects"] +
        discovered["numbers"]
    )
    
    # Get all detected components
    components = set(e["component"] for e in all_entities)
    
    # Should at least have these core components
    core_components = {"system", "hk1", "pe1"}
    assert core_components.issubset(components), f"Missing core components. Found: {components}"


@pytest.mark.asyncio
async def test_integration_device_classes(mock_hub):
    """Test that device classes are properly assigned."""
    initial_data = await mock_hub.async_update()
    discovered = discover_all_entities(initial_data)
    
    # Check temperature sensors have proper device class
    temp_sensors = [
        s for s in discovered["sensors"]
        if s.get("unit") == "°C"
    ]
    
    assert len(temp_sensors) > 0, "No temperature sensors found"
    
    # Most should have temperature device class
    with_device_class = [s for s in temp_sensors if s.get("device_class") == "temperature"]
    assert len(with_device_class) > len(temp_sensors) * 0.5, "Most temp sensors should have device_class"


@pytest.mark.asyncio
async def test_integration_full_pipeline():
    """Test complete integration pipeline with all fixtures."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixture_files = list(fixtures_dir.glob("api_response_*.json"))
    
    assert len(fixture_files) >= 9, "Should have at least 9 test fixtures"
    
    total_entities = 0
    
    for fixture_file in fixture_files:
        with open(fixture_file, "r") as f:
            api_data = json.load(f)
        
        discovered = discover_all_entities(api_data)
        
        count = (
            len(discovered["sensors"]) +
            len(discovered["binary_sensors"]) +
            len(discovered["selects"]) +
            len(discovered["numbers"])
        )
        
        total_entities += count
        assert count > 0, f"No entities discovered in {fixture_file.name}"
    
    # Should discover a significant number of entities across all fixtures
    assert total_entities > 1000, f"Expected >1000 entities, got {total_entities}"
    print(f"\n✅ Total entities discovered across all fixtures: {total_entities}")
