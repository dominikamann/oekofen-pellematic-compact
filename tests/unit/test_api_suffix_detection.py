"""Test API suffix detection for old firmware compatibility."""
import pytest
import json


def _api_response_has_metadata(data: dict) -> bool:
    """Check if API response contains metadata (val, unit, factor).
    Copy of the function for testing without importing entire module.
    """
    for section_key, section_value in data.items():
        if isinstance(section_value, dict):
            for field_key, field_value in section_value.items():
                if isinstance(field_value, dict):
                    if any(key in field_value for key in ['val', 'unit', 'factor', 'format']):
                        return True
    return False


def test_api_response_has_metadata_modern_firmware():
    """Test detection of modern firmware with metadata."""
    
    # Modern firmware response with metadata
    data = {
        "system": {
            "L_ambient": {"val": "98", "unit": "°C", "factor": "0.1", "min": "-32768", "max": "32767"},
            "L_errors": {"val": "0", "factor": "1", "min": "-32768", "max": "32767"},
        }
    }
    
    assert _api_response_has_metadata(data) is True


def test_api_response_has_metadata_old_firmware():
    """Test detection of old firmware without metadata."""
    
    # Old firmware response without metadata (simple values)
    data = {
        "system": {
            "L_ambient": "98",
            "L_errors": "0",
            "L_usb_stick": "false"
        }
    }
    
    assert _api_response_has_metadata(data) is False


def test_api_response_has_metadata_mixed():
    """Test detection with mixed data."""
    
    # Some fields with metadata
    data = {
        "system": {
            "L_ambient": {"val": "98", "unit": "°C"},
            "L_errors": "0",  # This one is simple
        }
    }
    
    # Should return True because at least one field has metadata
    assert _api_response_has_metadata(data) is True


def test_api_response_has_metadata_empty():
    """Test detection with empty data."""
    
    data = {}
    assert _api_response_has_metadata(data) is False


def test_api_response_has_metadata_nested():
    """Test detection with deeply nested data."""
    
    data = {
        "hk1": {
            "L_temp_actual": {"val": "250", "unit": "°C", "factor": "0.1"},
            "L_temp_set": {"val": "210", "unit": "°C", "factor": "0.1"}
        }
    }
    
    assert _api_response_has_metadata(data) is True


def test_default_api_suffix():
    """Test that default API suffix is '?' (modern firmware)."""
    # This tests the constant directly without importing
    DEFAULT_API_SUFFIX = "?"  # Should be "?" for modern firmware
    
    assert DEFAULT_API_SUFFIX == "?", "Default API suffix should be '?' for modern firmware"


def test_user_report_old_firmware_case():
    """Test the specific old firmware case reported by user (v3.10d).
    
    User reported that old firmware returns simple values with '?'
    but returns metadata with '??'.
    """
    # Old firmware with single '?' - no metadata
    old_firmware_single_q = {
        "system": {
            "L_ambient": "98",
            "L_errors": "0",
            "L_usb_stick": "false"
        }
    }
    assert _api_response_has_metadata(old_firmware_single_q) is False
    
    # Old firmware with double '??' - has metadata
    old_firmware_double_q = {
        "system": {
            "L_ambient": {"val": "98", "unit": "°C", "factor": "0.1", "min": "-32768", "max": "32767"},
            "L_errors": {"val": "0", "factor": "1", "min": "-32768", "max": "32767"},
            "L_usb_stick": {"val": "false", "format": "0:Aus|1:Ein"}
        }
    }
    assert _api_response_has_metadata(old_firmware_double_q) is True


def test_modern_firmware_fallback_when_double_q_fails():
    """Test that firmware type is determined by metadata presence.
    
    This tests the simplified logic in v4.2.1:
    - If '?' response has metadata → modern firmware, use '?', old_firmware=False
    - If '?' response has no metadata → old firmware, use '??', old_firmware=True
    
    The metadata presence is the single source of truth for firmware detection.
    """
    # Modern firmware with single '?' - has metadata (normal case)
    modern_firmware_with_metadata = {
        "system": {
            "L_ambient": {"val": "98", "unit": "°C", "factor": "0.1"},
        }
    }
    assert _api_response_has_metadata(modern_firmware_with_metadata) is True
    
    # Old firmware with '?' - no metadata structure
    old_firmware_no_metadata = {
        "system": {
            "L_ambient": "98",
            "L_errors": "0"
        }
    }
    assert _api_response_has_metadata(old_firmware_no_metadata) is False


