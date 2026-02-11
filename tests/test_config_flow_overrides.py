"""Test config flow charset and old_firmware override behavior."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL
from custom_components.oekofen_pellematic_compact.config_flow import OekofenPellematicCompactConfigFlow
from custom_components.oekofen_pellematic_compact.const import (
    DOMAIN,
    CONF_CHARSET,
    CONF_OLD_FIRMWARE,
    CONF_API_SUFFIX,
    CONF_NUM_OF_HEATING_CIRCUIT,
    DEFAULT_CHARSET,
    DEFAULT_OLD_FIRMWARE,
    DEFAULT_NAME,
)


@pytest.mark.asyncio
async def test_initial_config_auto_detection():
    """Test that charset and old_firmware are auto-detected when user leaves defaults."""
    flow = OekofenPellematicCompactConfigFlow()
    flow.hass = MagicMock()
    
    # Mock API response for modern firmware with UTF-8
    mock_data = {
        "system": {
            "L_ambient": {"val": "98", "unit": "°C", "factor": "0.1"}
        },
        "pe1": {
            "L_temp": {"val": "500", "unit": "°C", "factor": "0.1"}
        }
    }
    
    async def mock_fetch(*args):
        # Return: data, charset, api_suffix, old_firmware
        return mock_data, "utf-8", "?", False
    
    flow.hass.async_add_executor_job = AsyncMock(side_effect=mock_fetch)
    flow.async_set_unique_id = AsyncMock(return_value=None)
    flow._abort_if_unique_id_configured = MagicMock(return_value=None)
    
    # User input with defaults (triggers auto-detection)
    user_input = {
        CONF_HOST: "http://192.168.1.100/pass/",
        CONF_NAME: "My Heater",
        CONF_CHARSET: DEFAULT_CHARSET,  # iso-8859-1 (default)
        CONF_OLD_FIRMWARE: DEFAULT_OLD_FIRMWARE,  # False (default)
    }
    
    with patch('custom_components.oekofen_pellematic_compact.discover_components_from_api') as mock_discover:
        mock_discover.return_value = {
            CONF_NUM_OF_HEATING_CIRCUIT: 2,
            "num_of_hot_water": 1,
            "num_of_pellematic_heaters": 1,
        }
        
        result = await flow.async_step_user(user_input)
    
    # Verify entry was created
    assert result["type"] == "create_entry"
    
    # Verify auto-detected values were used (UTF-8 and modern firmware)
    assert result["data"][CONF_CHARSET] == "utf-8"  # Auto-detected, not iso-8859-1
    assert result["data"][CONF_OLD_FIRMWARE] is False  # Auto-detected modern firmware
    assert result["data"][CONF_API_SUFFIX] == "?"


@pytest.mark.asyncio
async def test_initial_config_user_charset_override():
    """Test that user's explicit charset choice is respected."""
    flow = OekofenPellematicCompactConfigFlow()
    flow.hass = MagicMock()
    
    # Mock API response that would detect UTF-8
    mock_data = {
        "system": {
            "L_ambient": {"val": "98", "unit": "°C", "factor": "0.1"}
        }
    }
    
    async def mock_fetch(*args):
        # Auto-detection would suggest utf-8
        return mock_data, "utf-8", "?", False
    
    flow.hass.async_add_executor_job = AsyncMock(side_effect=mock_fetch)
    flow.async_set_unique_id = AsyncMock(return_value=None)
    flow._abort_if_unique_id_configured = MagicMock(return_value=None)
    
    # User explicitly sets windows-1252
    user_input = {
        CONF_HOST: "http://192.168.1.100/pass/",
        CONF_NAME: "My Heater",
        CONF_CHARSET: "windows-1252",  # User's explicit choice
        CONF_OLD_FIRMWARE: DEFAULT_OLD_FIRMWARE,
    }
    
    with patch('custom_components.oekofen_pellematic_compact.discover_components_from_api') as mock_discover:
        mock_discover.return_value = {
            CONF_NUM_OF_HEATING_CIRCUIT: 1,
        }
        
        result = await flow.async_step_user(user_input)
    
    # Verify user's charset was respected despite auto-detection
    assert result["type"] == "create_entry"
    assert result["data"][CONF_CHARSET] == "windows-1252"  # User's choice, NOT utf-8


@pytest.mark.asyncio
async def test_initial_config_user_old_firmware_override():
    """Test that user's explicit old_firmware choice is respected."""
    flow = OekofenPellematicCompactConfigFlow()
    flow.hass = MagicMock()
    
    # Mock API response for modern firmware (would auto-detect as False)
    mock_data = {
        "system": {
            "L_ambient": {"val": "98", "unit": "°C", "factor": "0.1"}
        }
    }
    
    async def mock_fetch(*args):
        # Auto-detection would suggest modern firmware (False)
        return mock_data, "utf-8", "?", False
    
    flow.hass.async_add_executor_job = AsyncMock(side_effect=mock_fetch)
    flow.async_set_unique_id = AsyncMock(return_value=None)
    flow._abort_if_unique_id_configured = MagicMock(return_value=None)
    
    # User explicitly forces old firmware mode
    user_input = {
        CONF_HOST: "http://192.168.1.100/pass/",
        CONF_NAME: "My Heater",
        CONF_CHARSET: DEFAULT_CHARSET,
        CONF_OLD_FIRMWARE: True,  # User's explicit choice
    }
    
    with patch('custom_components.oekofen_pellematic_compact.discover_components_from_api') as mock_discover:
        mock_discover.return_value = {
            CONF_NUM_OF_HEATING_CIRCUIT: 1,
        }
        
        result = await flow.async_step_user(user_input)
    
    # Verify user's old_firmware flag was respected despite auto-detection
    assert result["type"] == "create_entry"
    assert result["data"][CONF_OLD_FIRMWARE] is True  # User's choice, NOT False
    assert result["data"][CONF_API_SUFFIX] == "?"  # API suffix still from detection


@pytest.mark.asyncio
async def test_initial_config_both_overrides():
    """Test that both charset and old_firmware overrides work together."""
    flow = OekofenPellematicCompactConfigFlow()
    flow.hass = MagicMock()
    
    mock_data = {
        "system": {
            "L_ambient": {"val": "98", "unit": "°C", "factor": "0.1"}
        }
    }
    
    async def mock_fetch(*args):
        # Auto-detection suggests different values
        return mock_data, "utf-8", "?", False
    
    flow.hass.async_add_executor_job = AsyncMock(side_effect=mock_fetch)
    flow.async_set_unique_id = AsyncMock(return_value=None)
    flow._abort_if_unique_id_configured = MagicMock(return_value=None)
    
    # User overrides BOTH settings
    user_input = {
        CONF_HOST: "http://192.168.1.100/pass/",
        CONF_NAME: "My Heater",
        CONF_CHARSET: "iso-8859-15",  # User override
        CONF_OLD_FIRMWARE: True,  # User override
    }
    
    with patch('custom_components.oekofen_pellematic_compact.discover_components_from_api') as mock_discover:
        mock_discover.return_value = {
            CONF_NUM_OF_HEATING_CIRCUIT: 1,
        }
        
        result = await flow.async_step_user(user_input)
    
    # Verify both user choices were respected
    assert result["type"] == "create_entry"
    assert result["data"][CONF_CHARSET] == "iso-8859-15"
    assert result["data"][CONF_OLD_FIRMWARE] is True


@pytest.mark.asyncio
async def test_reconfigure_auto_detection():
    """Test that reconfigure auto-detects when user leaves defaults unchanged."""
    flow = OekofenPellematicCompactConfigFlow()
    flow.hass = MagicMock()
    
    # Mock existing config entry
    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_HOST: "http://192.168.1.100/pass/",
        CONF_NAME: "My Heater",
        CONF_CHARSET: "iso-8859-1",
        CONF_OLD_FIRMWARE: False,
        CONF_API_SUFFIX: "?",
        CONF_NUM_OF_HEATING_CIRCUIT: 2,
    }
    
    flow.hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    flow.hass.config_entries.async_update_entry = MagicMock()
    flow.hass.config_entries.async_reload = AsyncMock(return_value=None)
    
    flow.context = {"entry_id": "test123"}
    
    # Mock API detection finding UTF-8 and modern firmware
    mock_data = {
        "system": {"L_ambient": {"val": "98", "unit": "°C", "factor": "0.1"}}
    }
    
    async def mock_fetch(*args):
        return mock_data, "utf-8", "?", False
    
    flow.hass.async_add_executor_job = AsyncMock(side_effect=mock_fetch)
    
    # User doesn't change anything (keeps current defaults)
    user_input = {
        CONF_HOST: "http://192.168.1.100/pass/",
        CONF_SCAN_INTERVAL: 60,
        CONF_CHARSET: "iso-8859-1",  # Same as current
        CONF_OLD_FIRMWARE: False,  # Same as current
    }
    
    with patch('custom_components.oekofen_pellematic_compact.discover_components_from_api') as mock_discover:
        mock_discover.return_value = {
            CONF_NUM_OF_HEATING_CIRCUIT: 3,  # Discovered changed value
        }
        
        result = await flow.async_step_reconfigure(user_input)
    
    # Get the updated config
    update_call = flow.hass.config_entries.async_update_entry.call_args
    updated_data = update_call[1]["data"]
    
    # Verify auto-detection happened and components were updated
    assert updated_data[CONF_CHARSET] == "utf-8"  # Auto-detected
    assert updated_data[CONF_OLD_FIRMWARE] is False  # Auto-detected
    assert updated_data[CONF_NUM_OF_HEATING_CIRCUIT] == 3  # Re-discovered


@pytest.mark.asyncio
async def test_reconfigure_user_override():
    """Test that reconfigure respects user's manual changes."""
    flow = OekofenPellematicCompactConfigFlow()
    flow.hass = MagicMock()
    
    # Mock existing config entry
    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_HOST: "http://192.168.1.100/pass/",
        CONF_NAME: "My Heater",
        CONF_CHARSET: "iso-8859-1",
        CONF_OLD_FIRMWARE: False,
        CONF_API_SUFFIX: "?",
    }
    
    flow.hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)
    flow.hass.config_entries.async_update_entry = MagicMock()
    flow.hass.config_entries.async_reload = AsyncMock(return_value=None)
    
    flow.context = {"entry_id": "test123"}
    
    # Mock API detection
    mock_data = {
        "system": {"L_ambient": {"val": "98", "unit": "°C", "factor": "0.1"}}
    }
    
    async def mock_fetch(*args):
        # Would auto-detect utf-8 and modern firmware
        return mock_data, "utf-8", "?", False
    
    flow.hass.async_add_executor_job = AsyncMock(side_effect=mock_fetch)
    
    # User explicitly changes both settings
    user_input = {
        CONF_HOST: "http://192.168.1.100/pass/",
        CONF_SCAN_INTERVAL: 60,
        CONF_CHARSET: "windows-1252",  # User changed from iso-8859-1
        CONF_OLD_FIRMWARE: True,  # User changed from False
    }
    
    with patch('custom_components.oekofen_pellematic_compact.discover_components_from_api') as mock_discover:
        mock_discover.return_value = {
            CONF_NUM_OF_HEATING_CIRCUIT: 2,
        }
        
        result = await flow.async_step_reconfigure(user_input)
    
    # Get the updated config
    update_call = flow.hass.config_entries.async_update_entry.call_args
    updated_data = update_call[1]["data"]
    
    # Verify user's manual changes were respected
    assert updated_data[CONF_CHARSET] == "windows-1252"  # User's choice
    assert updated_data[CONF_OLD_FIRMWARE] is True  # User's choice (NOT auto-detected False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
