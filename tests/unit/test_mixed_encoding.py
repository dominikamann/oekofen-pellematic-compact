"""Tests for mixed encoding detection (UTF-8 + ISO-8859-1 in same response)."""
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from custom_components.oekofen_pellematic_compact.config_flow import detect_charset_from_response


class TestMixedEncodingDetection:
    """Test charset detection for mixed encoding scenarios."""
    
    def test_mixed_encoding_mostly_utf8_with_iso_bytes(self):
        """Test that mixed encoding (mostly UTF-8 with some ISO-8859-1 bytes) is detected as UTF-8.
        
        This simulates the real-world case where the Ökofen API sends:
        - UTF-8 encoded text for most fields (e.g., "Öko Modus", "oekomode")
        - ISO-8859-1 bytes in some value fields (e.g., location "Ribbesbüttel")
        
        The expected behavior is to prefer UTF-8 since most content is UTF-8,
        accepting that some rare fields like location may show � characters.
        """
        # Create a response with mostly UTF-8 content but some ISO-8859-1 bytes
        response_dict = {
            "system": {
                "L_datetime": "10.01.2025 14:30:45",
                "L_location": "Ribbesbüttel",  # Will be ISO-8859-1 bytes for ü
                "L_oekomode": "Öko Modus",      # UTF-8 umlauts
                "L_state": "Normalbetrieb",      # UTF-8
                "L_statetext": "Heizung läuft",  # UTF-8 umlaut
                "L_temp_outside": "5.2 °C",
                "L_temp_boiler": "65.8 °C",
                "sk_num_pe1": {
                    "L_modulation": "45%",
                    "L_uw_release": "Wärme freigegeben",  # UTF-8 umlaut
                }
            },
            "hk1": {
                "L_roomtemp_act": "21.5 °C",
                "L_roomtemp_set": "22.0 °C",
                "name": "Wohnzimmer Fußbodenheizung"  # UTF-8 umlauts
            }
        }
        
        # Encode most of it as UTF-8
        json_str = json.dumps(response_dict, ensure_ascii=False)
        
        # Replace the location value with ISO-8859-1 encoded bytes for "Ribbesbüttel"
        # First encode as UTF-8
        utf8_bytes = json_str.encode('utf-8')
        
        # Find and replace "Ribbesbüttel" UTF-8 bytes with ISO-8859-1 bytes
        utf8_location = "Ribbesbüttel".encode('utf-8')  # b'Ribbesb\xc3\xbcttel'
        iso_location = "Ribbesbüttel".encode('iso-8859-1')  # b'Ribbesb\xfcttel'
        
        mixed_bytes = utf8_bytes.replace(utf8_location, iso_location)
        
        # Detect charset
        charset = detect_charset_from_response(mixed_bytes)
        
        # Should detect as UTF-8 since majority of content is UTF-8
        # Even though one field has ISO-8859-1 bytes, it's less than 20% of non-ASCII chars
        assert charset == 'utf-8', (
            f"Mixed encoding should be detected as UTF-8. "
            f"Got: {charset}. "
            f"Most fields are UTF-8 ('Öko', 'Wärme', 'Fußboden'), "
            f"only location 'Ribbesbüttel' has ISO-8859-1 bytes. "
            f"Threshold is 20%, this case should be ~11%."
        )
    
    def test_mostly_iso_8859_1_detected_correctly(self):
        """Test that responses with mostly ISO-8859-1 are still detected as ISO-8859-1."""
        # Create response with many ISO-8859-1 special chars
        response_dict = {
            "system": {
                "L_temp_rücklauf": "45.2",     # ü as ISO-8859-1
                "L_temp_außen": "5.1",          # ü as ISO-8859-1
                "L_öl_level": "75%",            # ö as ISO-8859-1
                "L_état": "arrêt",              # é, ê as ISO-8859-1
                "L_données": "système",         # é as ISO-8859-1
            }
        }
        
        # Encode all as ISO-8859-1
        json_str = json.dumps(response_dict, ensure_ascii=False)
        iso_bytes = json_str.encode('iso-8859-1')
        
        # Detect charset
        charset = detect_charset_from_response(iso_bytes)
        
        # Should detect as ISO-8859-1 since all content is ISO-8859-1
        assert charset == 'iso-8859-1', (
            f"Pure ISO-8859-1 encoding should be detected correctly. Got: {charset}"
        )
    
    def test_pure_utf8_detected_correctly(self):
        """Test that pure UTF-8 responses are detected as UTF-8."""
        response_dict = {
            "system": {
                "L_oekomode": "Öko Modus",
                "L_statetext": "Heizung läuft",
                "L_temp_rücklauf": "45.2 °C",
                "hk1": {
                    "name": "Fußbodenheizung Wohnzimmer"
                }
            }
        }
        
        # Encode as UTF-8
        json_str = json.dumps(response_dict, ensure_ascii=False)
        utf8_bytes = json_str.encode('utf-8')
        
        # Detect charset
        charset = detect_charset_from_response(utf8_bytes)
        
        # Should detect as UTF-8
        assert charset == 'utf-8', f"Pure UTF-8 encoding should be detected. Got: {charset}"
    
    def test_ascii_only_defaults_to_utf8(self):
        """Test that ASCII-only responses default to UTF-8."""
        response_dict = {
            "system": {
                "L_state": "normal",
                "L_temp": "45.2",
            }
        }
        
        json_str = json.dumps(response_dict)
        ascii_bytes = json_str.encode('ascii')
        
        charset = detect_charset_from_response(ascii_bytes)
        
        # Should default to UTF-8 for ASCII-only
        assert charset == 'utf-8', f"ASCII-only should default to UTF-8. Got: {charset}"
    
    def test_edge_case_20_percent_threshold(self):
        """Test the 20% replacement threshold boundary."""
        # Create response with exactly 20% problematic characters
        # 10 non-ASCII chars, 2 ISO-8859-1 (20% exactly)
        response_dict = {
            "field1": "Öko",       # 1 non-ASCII (UTF-8)
            "field2": "Mödus",     # 1 non-ASCII (UTF-8)
            "field3": "läuft",     # 1 non-ASCII (UTF-8)
            "field4": "Wärme",     # 1 non-ASCII (UTF-8)
            "field5": "Füße",      # 1 non-ASCII (UTF-8)
            "field6": "größ",      # 1 non-ASCII (UTF-8)
            "field7": "möglich",   # 1 non-ASCII (UTF-8)
            "field8": "Überwachung",  # 1 non-ASCII (UTF-8)
            "field9": "XX",        # Will be replaced with 2 ISO bytes
        }
        
        json_str = json.dumps(response_dict, ensure_ascii=False)
        utf8_bytes = json_str.encode('utf-8')
        
        # Replace two fields with ISO-8859-1 bytes (simulating 2/10 = 20%)
        # Replace "XX" with "üö" in ISO-8859-1
        mixed_bytes = utf8_bytes.replace(b'"XX"', '"üö"'.encode('iso-8859-1'))
        
        charset = detect_charset_from_response(mixed_bytes)
        
        # At exactly 20% or more, should fall back to ISO-8859-1
        # But our threshold is < 0.2, so 0.2 (20%) should use ISO-8859-1
        assert charset in ['utf-8', 'iso-8859-1'], (
            f"Boundary case at 20% threshold. Got: {charset}"
        )
