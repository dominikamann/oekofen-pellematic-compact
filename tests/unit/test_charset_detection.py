"""Test charset detection for international support."""
import pytest
import json


def detect_charset_from_response(raw_data: bytes) -> str:
    """Detect the most likely charset from API response data.
    
    This is a copy of the function from config_flow.py for testing.
    """
    try:
        decoded_utf8 = raw_data.decode('utf-8')
        if any(ord(char) > 127 for char in decoded_utf8):
            return 'utf-8'
        return 'utf-8'
    except UnicodeDecodeError:
        return 'iso-8859-1'


class TestCharsetDetection:
    """Test charset detection for various languages and encodings."""
    
    @pytest.mark.parametrize("language,text", [
        ("German", "Rücklauf Temperatur"),
        ("German", "Ölkessel Außentemperatur"),
        ("French", "Télécommande arrêt"),
        ("French", "Température extérieure"),
        ("Italian", "Temperatura esterna àèìòù"),
        ("Spanish", "Calefacción año"),
        ("Polish", "Temperatura ąćęłńóśźż"),
        ("Czech", "Teplota čěšřž"),
        ("Greek", "Θερμοκρασία"),
        ("Cyrillic", "Температура"),
    ])
    def test_utf8_detection_various_languages(self, language, text):
        """Test UTF-8 detection for various languages."""
        # Simulate API response with UTF-8 encoding
        api_data = {"test": {"text": text}}
        json_str = json.dumps(api_data, ensure_ascii=False)
        utf8_bytes = json_str.encode('utf-8')
        
        detected = detect_charset_from_response(utf8_bytes)
        
        assert detected == 'utf-8', f"{language} text should be detected as UTF-8"
    
    def test_iso_8859_1_detection(self):
        """Test ISO-8859-1 detection for old systems."""
        # Characters that exist in ISO-8859-1
        text = "Rücklauf"
        api_data = {"test": {"text": text}}
        json_str = json.dumps(api_data, ensure_ascii=False)
        
        # Encode as ISO-8859-1 (simulating old system)
        iso_bytes = json_str.encode('iso-8859-1')
        
        detected = detect_charset_from_response(iso_bytes)
        
        assert detected == 'iso-8859-1', "ISO-8859-1 encoded data should be detected"
    
    def test_ascii_defaults_to_utf8(self):
        """Test that ASCII-only data defaults to UTF-8."""
        text = "Temperature Sensor"
        utf8_bytes = text.encode('utf-8')
        
        detected = detect_charset_from_response(utf8_bytes)
        
        assert detected == 'utf-8', "ASCII-only should default to UTF-8"
    
    def test_french_user_report_case(self):
        """Test the specific French case reported by user.
        
        User reported: "TÃ©lÃ©commande" instead of "Télécommande"
        This happens when UTF-8 is wrongly decoded as ISO-8859-1.
        """
        text = "Télécommande"
        api_data = {"test": {"text": text}}
        json_str = json.dumps(api_data, ensure_ascii=False)
        utf8_bytes = json_str.encode('utf-8')
        
        # Detection should return UTF-8
        detected = detect_charset_from_response(utf8_bytes)
        assert detected == 'utf-8'
        
        # Verify correct decoding
        decoded_correct = utf8_bytes.decode('utf-8')
        assert 'Télécommande' in decoded_correct
        
        # Show what would happen with wrong charset
        decoded_wrong = utf8_bytes.decode('iso-8859-1')
        assert 'TÃ©lÃ©commande' in decoded_wrong, "Wrong charset produces mojibake"
    
    def test_french_arret_case(self):
        """Test French 'arrêt' case from user report."""
        text = "arrêt"
        api_data = {"test": {"text": text}}
        json_str = json.dumps(api_data, ensure_ascii=False)
        utf8_bytes = json_str.encode('utf-8')
        
        detected = detect_charset_from_response(utf8_bytes)
        assert detected == 'utf-8'
        
        # Verify correct vs wrong decoding
        decoded_correct = utf8_bytes.decode('utf-8')
        assert 'arrêt' in decoded_correct
        
        decoded_wrong = utf8_bytes.decode('iso-8859-1')
        assert 'arrÃªt' in decoded_wrong
