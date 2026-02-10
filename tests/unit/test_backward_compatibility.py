"""Backward compatibility test for mixed encoding detection.

This test verifies that existing users with pure ISO-8859-1 or UTF-8
are not negatively affected by the new mixed encoding detection.
"""
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from custom_components.oekofen_pellematic_compact.config_flow import detect_charset_from_response


def test_pure_iso_8859_1_with_few_special_chars():
    """Test that pure ISO-8859-1 with only a few special chars is still detected correctly.
    
    This ensures we don't break users who have working ISO-8859-1 setups.
    """
    # Simulate a response with only 1-2 ISO-8859-1 special chars
    response = {
        "system": {
            "L_temp": "45.2",
            "L_state": "Normal",
            "L_name": "Heizüng",  # ü in ISO-8859-1
        }
    }
    
    json_str = json.dumps(response, ensure_ascii=False)
    iso_bytes = json_str.encode('iso-8859-1')
    
    charset = detect_charset_from_response(iso_bytes)
    
    # Should still detect as ISO-8859-1
    assert charset == 'iso-8859-1', (
        f"Pure ISO-8859-1 with few special chars should be detected as ISO-8859-1. "
        f"Got: {charset}. This would break existing users!"
    )


def test_pure_iso_8859_1_with_many_special_chars():
    """Test that pure ISO-8859-1 with many special chars is still detected correctly."""
    # Simulate a response with many ISO-8859-1 special chars (German umlauts)
    response = {
        "system": {
            "L_temp_rücklauf": "45.2",     # ü
            "L_temp_außen": "5.1",          # ß
            "L_öl_level": "75%",            # ö
            "L_größe": "Medium",            # ö
            "L_betriebsmodus": "Äko",       # Ä
            "L_wärme": "aktiv",             # ä
        }
    }
    
    json_str = json.dumps(response, ensure_ascii=False)
    iso_bytes = json_str.encode('iso-8859-1')
    
    charset = detect_charset_from_response(iso_bytes)
    
    # Should detect as ISO-8859-1
    assert charset == 'iso-8859-1', (
        f"Pure ISO-8859-1 with many special chars should be detected as ISO-8859-1. "
        f"Got: {charset}. This would break existing users!"
    )


def test_pure_utf8_users_unaffected():
    """Test that existing UTF-8 users are not affected."""
    response = {
        "system": {
            "L_oekomode": "Öko Modus",
            "L_temp_rücklauf": "45.2 °C",
            "L_statetext": "Heizung läuft normal",
            "hk1": {
                "name": "Fußbodenheizung Wohnzimmer"
            }
        }
    }
    
    json_str = json.dumps(response, ensure_ascii=False)
    utf8_bytes = json_str.encode('utf-8')
    
    charset = detect_charset_from_response(utf8_bytes)
    
    # Should still detect as UTF-8
    assert charset == 'utf-8', (
        f"Pure UTF-8 should still be detected as UTF-8. "
        f"Got: {charset}. This would break existing users!"
    )


def test_french_iso_8859_1_unaffected():
    """Test that French users with ISO-8859-1 are not affected."""
    # French text with accents in ISO-8859-1
    response = {
        "system": {
            "L_etat": "arrêt",              # ê
            "L_mode": "été",                # é
            "L_temp_extérieure": "15.5",    # é
            "L_données": "système",         # é, è
        }
    }
    
    json_str = json.dumps(response, ensure_ascii=False)
    iso_bytes = json_str.encode('iso-8859-1')
    
    charset = detect_charset_from_response(iso_bytes)
    
    # Should detect as ISO-8859-1
    assert charset == 'iso-8859-1', (
        f"French ISO-8859-1 should be detected correctly. "
        f"Got: {charset}. This would break existing French users!"
    )


def test_edge_case_mostly_ascii_with_one_iso_char():
    """Test edge case: mostly ASCII with just one ISO-8859-1 char.
    
    This is the riskiest case - if detection fails here, we break users.
    """
    # Large response with only ONE special character
    response = {
        "system": {
            "L_temp1": "20.5",
            "L_temp2": "21.0", 
            "L_temp3": "22.5",
            "L_temp4": "23.0",
            "L_temp5": "24.5",
            "L_state": "Normal",
            "L_mode": "Auto",
            "L_name": "Müller",  # Only this has ü in ISO-8859-1
        }
    }
    
    json_str = json.dumps(response, ensure_ascii=False)
    iso_bytes = json_str.encode('iso-8859-1')
    
    charset = detect_charset_from_response(iso_bytes)
    
    # CRITICAL: Should detect as ISO-8859-1, not UTF-8
    assert charset == 'iso-8859-1', (
        f"ISO-8859-1 with only one special char must be detected as ISO-8859-1. "
        f"Got: {charset}. This would break existing users with German names!"
    )


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
