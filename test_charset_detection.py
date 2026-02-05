#!/usr/bin/env python3
"""Test charset detection with fixtures."""
import json
from pathlib import Path


def detect_charset_from_response(raw_data: bytes) -> str:
    """Detect the most likely charset from API response data.
    
    This function analyzes the raw bytes from the API response and detects
    common encoding issues to suggest the correct charset.
    
    Args:
        raw_data: Raw bytes from API response
        
    Returns:
        Suggested charset ('utf-8' or 'iso-8859-1')
    """
    # Common patterns that indicate UTF-8 wrongly decoded as ISO-8859-1
    # ü = UTF-8: C3 BC → wrongly as ISO: Ã¼
    # ö = UTF-8: C3 B6 → wrongly as ISO: Ã¶
    # ä = UTF-8: C3 A4 → wrongly as ISO: Ã¤
    # ß = UTF-8: C3 9F → wrongly as ISO: ÃŸ
    # ° = UTF-8: C2 B0 → wrongly as ISO: Â°
    
    utf8_wrong_patterns = [
        b'\xc3\xbc',  # ü as UTF-8
        b'\xc3\xb6',  # ö as UTF-8
        b'\xc3\xa4',  # ä as UTF-8
        b'\xc3\x9f',  # ß as UTF-8
        b'\xc2\xb0',  # ° as UTF-8
    ]
    
    # Count how many UTF-8 multi-byte sequences we find
    utf8_indicators = sum(1 for pattern in utf8_wrong_patterns if pattern in raw_data)
    
    # Try to decode as UTF-8 and check if it's valid
    try:
        decoded_utf8 = raw_data.decode('utf-8')
        # If we can decode as UTF-8 and find typical German umlauts, it's likely UTF-8
        if any(char in decoded_utf8 for char in ['ü', 'ö', 'ä', 'ß', 'Ü', 'Ö', 'Ä']):
            return 'utf-8'
    except UnicodeDecodeError:
        # Can't decode as UTF-8, probably ISO-8859-1
        pass
    
    # If we found UTF-8 multi-byte patterns, suggest UTF-8
    if utf8_indicators > 0:
        return 'utf-8'
    
    # Try ISO-8859-1 and look for mojibake patterns (Ã¼, Ã¶, etc.)
    try:
        decoded_iso = raw_data.decode('iso-8859-1')
        # Check for common mojibake patterns indicating UTF-8 data decoded as ISO
        if any(pattern in decoded_iso for pattern in ['Ã¼', 'Ã¶', 'Ã¤', 'Ã', 'Â°']):
            return 'utf-8'  # Data is actually UTF-8, not ISO
    except:
        pass
    
    # Default to iso-8859-1 (old default)
    return 'iso-8859-1'


def test_fixture(fixture_path: Path):
    """Test charset detection on a fixture file."""
    try:
        # Read fixture
        with open(fixture_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert to JSON bytes (simulating UTF-8 API response)
        json_str = json.dumps(data, ensure_ascii=False)
        utf8_bytes = json_str.encode('utf-8')
        
        # Detect charset
        detected = detect_charset_from_response(utf8_bytes)
        
        # Check if we can find German umlauts in the data
        has_umlauts = any(char in json_str for char in ['ü', 'ö', 'ä', 'ß', 'Ü', 'Ö', 'Ä'])
        
        print(f"\n{fixture_path.name}:")
        print(f"  Detected charset: {detected}")
        print(f"  Has German umlauts: {has_umlauts}")
        
        # If it has umlauts, it should be detected as UTF-8
        if has_umlauts and detected != 'utf-8':
            print(f"  ⚠️  WARNING: Expected UTF-8 but got {detected}")
        elif has_umlauts:
            print(f"  ✓ Correctly detected UTF-8")
    except Exception as e:
        print(f"\n{fixture_path.name}:")
        print(f"  ⚠️  Skipped: {e}")


def main():
    """Run charset detection tests on all fixtures."""
    fixtures_dir = Path(__file__).parent / "tests" / "fixtures"
    
    print("Testing charset detection on fixtures:")
    print("=" * 60)
    
    for fixture_file in sorted(fixtures_dir.glob("api_response_*.json")):
        test_fixture(fixture_file)
    
    print("\n" + "=" * 60)
    print("\nTesting mojibake pattern detection:")
    
    # Test: UTF-8 "Rücklauf" wrongly decoded as ISO-8859-1 becomes "RÃ¼cklauf"
    utf8_text = "Rücklauf Vorlauf Ölkessel"
    utf8_bytes = utf8_text.encode('utf-8')
    
    # Decode as ISO-8859-1 (wrong)
    iso_wrong = utf8_bytes.decode('iso-8859-1')
    print(f"\nOriginal UTF-8 text: {utf8_text}")
    print(f"Wrongly decoded as ISO: {iso_wrong}")
    
    # Re-encode to bytes and test detection
    iso_wrong_bytes = iso_wrong.encode('iso-8859-1')
    detected = detect_charset_from_response(iso_wrong_bytes)
    print(f"Detected charset: {detected}")
    
    if detected == 'utf-8':
        print("✓ Correctly detected UTF-8 from mojibake pattern!")
    else:
        print("⚠️  Failed to detect UTF-8 from mojibake")


if __name__ == "__main__":
    main()
