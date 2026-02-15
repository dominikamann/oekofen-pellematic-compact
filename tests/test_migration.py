"""Tests for entity ID migration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from homeassistant.helpers import entity_registry as er

from custom_components.oekofen_pellematic_compact.migration import (
    async_migrate_entity_ids,
    async_check_and_warn_entity_changes,
    _generate_old_entity_id_patterns,
)


@pytest.fixture
def mock_entity_registry():
    """Create a mock entity registry."""
    registry = Mock(spec=er.EntityRegistry)
    return registry


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.data = {
        "oekofen_pellematic_compact": {}
    }
    return hass


def test_generate_old_entity_id_patterns():
    """Test that old entity ID patterns are correctly generated."""
    patterns = _generate_old_entity_id_patterns()
    
    assert len(patterns) > 0
    
    # Check that common patterns exist
    pattern_texts = [p[1] for p in patterns]
    
    # Should have heater pattern
    assert any("heater" in p for p in pattern_texts)
    
    # Should have heating_circuit pattern
    assert any("heating_circuit" in p for p in pattern_texts)
    
    # Should have hot_water pattern
    assert any("hot_water" in p for p in pattern_texts)


@pytest.mark.asyncio
async def test_migrate_entity_ids_no_entities(mock_hass):
    """Test migration with no entities."""
    with patch("custom_components.oekofen_pellematic_compact.migration.er.async_get") as mock_get_registry:
        mock_registry = Mock()
        # Return actual empty list instead of Mock
        mock_entries = []
        mock_get_registry.return_value = mock_registry
        
        with patch("custom_components.oekofen_pellematic_compact.migration.er.async_entries_for_config_entry", return_value=mock_entries):
            migrated = await async_migrate_entity_ids(mock_hass, "test_entry", "test_hub")
            
            assert migrated == 0


@pytest.mark.asyncio
async def test_migrate_entity_ids_with_old_format(mock_hass):
    """Test migration with entities in old format."""
    # Create mock entities with old format
    old_entity = Mock()
    old_entity.entity_id = "sensor.pellematic_heater_1_temperature"
    old_entity.domain = "sensor"
    
    new_entity = Mock()
    new_entity.entity_id = "sensor.pellematic_pe1_L_temp_act"
    new_entity.domain = "sensor"
    
    # Return actual list instead of Mock
    mock_entries = [old_entity, new_entity]
    
    with patch("custom_components.oekofen_pellematic_compact.migration.er.async_get") as mock_get_registry:
        with patch("custom_components.oekofen_pellematic_compact.migration.er.async_entries_for_config_entry", return_value=mock_entries):
            # Mock persistent notification
            mock_hass.components = Mock()
            mock_hass.components.persistent_notification = Mock()
            mock_hass.components.persistent_notification.async_create = Mock()
            
            mock_registry = Mock()
            mock_get_registry.return_value = mock_registry
            
            migrated = await async_migrate_entity_ids(mock_hass, "test_entry", "test_hub")
            
            # Should detect and preserve the old entity
            assert migrated >= 1


@pytest.mark.asyncio
async def test_migrate_entity_ids_already_migrated(mock_hass):
    """Test that migration doesn't run twice."""
    # Mark as already migrated
    mock_hass.data["oekofen_pellematic_compact"]["test_hub"] = {
        "migrated_entity_ids": True
    }
    
    migrated = await async_migrate_entity_ids(mock_hass, "test_entry", "test_hub")
    
    # Should skip migration
    assert migrated == 0


@pytest.mark.asyncio
async def test_check_and_warn_german_entities(mock_hass):
    """Test detection of German entity IDs."""
    # Create entity with German name
    german_entity = Mock()
    german_entity.entity_id = "sensor.pellematic_pellematic_1_kesseltemperatur"
    german_entity.domain = "sensor"
    
    english_entity = Mock()
    english_entity.entity_id = "sensor.pellematic_pe1_L_temp_act"
    english_entity.domain = "sensor"
    
    # Return actual list
    mock_entries = [german_entity, english_entity]
    
    # Mock services.async_call for persistent notification
    mock_async_call = AsyncMock()
    mock_hass.services.async_call = mock_async_call
    
    with patch("custom_components.oekofen_pellematic_compact.migration.er.async_get") as mock_get_registry:
        with patch("custom_components.oekofen_pellematic_compact.migration.er.async_entries_for_config_entry", return_value=mock_entries):
            mock_registry = Mock()
            mock_get_registry.return_value = mock_registry
            
            warnings = await async_check_and_warn_entity_changes(
                mock_hass, "test_entry", "test_hub"
            )
            
            # Should detect German entity
            assert len(warnings) >= 1
            assert any("kesseltemperatur" in w.lower() for w in warnings)
            
            # Should create notification via services.async_call
            mock_async_call.assert_called_once()
            call_args = mock_async_call.call_args
            assert call_args[0][0] == "persistent_notification"
            assert call_args[0][1] == "create"


@pytest.mark.asyncio
async def test_check_and_warn_french_entities(mock_hass):
    """Test detection of French entity IDs."""
    # Create entity with French name
    french_entity = Mock()
    french_entity.entity_id = "sensor.pellematic_circuit_1_température"
    french_entity.domain = "sensor"
    
    # Return actual list
    mock_entries = [french_entity]
    
    # Mock services.async_call for persistent notification
    mock_async_call = AsyncMock()
    mock_hass.services.async_call = mock_async_call
    
    with patch("custom_components.oekofen_pellematic_compact.migration.er.async_get") as mock_get_registry:
        with patch("custom_components.oekofen_pellematic_compact.migration.er.async_entries_for_config_entry", return_value=mock_entries):
            mock_registry = Mock()
            mock_get_registry.return_value = mock_registry
            
            warnings = await async_check_and_warn_entity_changes(
                mock_hass, "test_entry", "test_hub"
            )
            
            # Should detect French entity
            assert len(warnings) >= 1
            assert any("température" in w.lower() for w in warnings)


@pytest.mark.asyncio
async def test_check_and_warn_no_warnings(mock_hass):
    """Test with properly formatted entity IDs."""
    # Create entities with correct format
    entity1 = Mock()
    entity1.entity_id = "sensor.pellematic_pe1_L_temp_act"
    entity1.domain = "sensor"
    
    entity2 = Mock()
    entity2.entity_id = "sensor.pellematic_hk1_L_roomtemp_act"
    entity2.domain = "sensor"
    
    # Return actual list
    mock_entries = [entity1, entity2]
    
    # Mock persistent notification properly
    mock_hass.components = Mock()
    mock_hass.components.persistent_notification = Mock()
    mock_create_notification = Mock()
    mock_hass.components.persistent_notification.async_create = mock_create_notification
    
    with patch("custom_components.oekofen_pellematic_compact.migration.er.async_get") as mock_get_registry:
        with patch("custom_components.oekofen_pellematic_compact.migration.er.async_entries_for_config_entry", return_value=mock_entries):
            mock_registry = Mock()
            mock_get_registry.return_value = mock_registry
            
            warnings = await async_check_and_warn_entity_changes(
                mock_hass, "test_entry", "test_hub"
            )
            
            # Should have no warnings
            assert len(warnings) == 0
            
            # Should not create notification
            mock_create_notification.assert_not_called()


def test_old_pattern_matching():
    """Test that old patterns match correctly."""
    import re
    
    patterns = _generate_old_entity_id_patterns()
    
    # Test heater pattern
    heater_pattern = next(p for p in patterns if "heater" in p[1])
    assert re.match(heater_pattern[1], "sensor.pellematic_heater_1_temperature")
    assert re.match(heater_pattern[1], "sensor.my_system_heater_2_power")
    assert not re.match(heater_pattern[1], "sensor.pellematic_pe1_L_temp_act")
    
    # Test heating circuit pattern
    hk_pattern = next(p for p in patterns if "heating_circuit" in p[1])
    assert re.match(hk_pattern[1], "sensor.pellematic_heating_circuit_1_temperature")
    assert re.match(hk_pattern[1], "sensor.my_heating_circuit_3_status")
    assert not re.match(hk_pattern[1], "sensor.pellematic_hk1_L_roomtemp_act")
    
    # Test climate pattern
    climate_pattern = next(p for p in patterns if p[0] == "climate")
    assert re.match(climate_pattern[1], "climate.pellematic_heating_circuit_1_climate")
    assert not re.match(climate_pattern[1], "climate.pellematic_hk1_climate")
