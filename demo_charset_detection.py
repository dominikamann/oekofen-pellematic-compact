#!/usr/bin/env python3
"""Demonstrate charset detection in action."""
import json


def detect_charset_from_response(raw_data: bytes) -> str:
    """Detect the most likely charset from API response data."""
    utf8_wrong_patterns = [
        b'\xc3\xbc',  # ü as UTF-8
        b'\xc3\xb6',  # ö as UTF-8
        b'\xc3\xa4',  # ä as UTF-8
        b'\xc3\x9f',  # ß as UTF-8
        b'\xc2\xb0',  # ° as UTF-8
    ]
    
    utf8_indicators = sum(1 for pattern in utf8_wrong_patterns if pattern in raw_data)
    
    try:
        decoded_utf8 = raw_data.decode('utf-8')
        if any(char in decoded_utf8 for char in ['ü', 'ö', 'ä', 'ß', 'Ü', 'Ö', 'Ä']):
            return 'utf-8'
    except UnicodeDecodeError:
        pass
    
    if utf8_indicators > 0:
        return 'utf-8'
    
    try:
        decoded_iso = raw_data.decode('iso-8859-1')
        if any(pattern in decoded_iso for pattern in ['Ã¼', 'Ã¶', 'Ã¤', 'Ã', 'Â°']):
            return 'utf-8'
    except:
        pass
    
    return 'iso-8859-1'


def demo_scenario(name: str, api_charset: str, user_charset: str):
    """Demonstrate what happens with different charset combinations."""
    print(f"\n{'='*70}")
    print(f"Scenario: {name}")
    print(f"  API encoding: {api_charset}")
    print(f"  User selected: {user_charset}")
    print(f"{'='*70}")
    
    # Simulate API response with German text
    api_data = {"pe1": {"L_temp": {"text": "Rücklauf", "unit": "°C"}}}
    json_str = json.dumps(api_data, ensure_ascii=False)
    
    # Encode with API's charset
    if api_charset == 'utf-8':
        api_bytes = json_str.encode('utf-8')
    else:
        api_bytes = json_str.encode('iso-8859-1')
    
    # Auto-detect
    detected = detect_charset_from_response(api_bytes)
    print(f"\nAuto-detected charset: {detected}")
    
    # Decode with user's charset
    try:
        if user_charset == 'utf-8':
            user_decoded = api_bytes.decode('utf-8')
        else:
            user_decoded = api_bytes.decode('iso-8859-1', 'ignore')
        
        data = json.loads(user_decoded, strict=False)
        text_result = data['pe1']['L_temp']['text']
        print(f"Decoded with user charset ({user_charset}): {text_result}")
    except Exception as e:
        print(f"Error decoding: {e}")
    
    # Show mismatch warning
    if detected != user_charset:
        print(f"\n⚠️  WARNING: Charset mismatch!")
        print(f"   API uses '{detected}' but you selected '{user_charset}'")
        print(f"   This may cause encoding issues with special characters.")
    else:
        print(f"\n✓ Charset match - no issues expected")


def main():
    """Run demonstration scenarios."""
    print("Charset Auto-Detection Demo")
    print("This shows what users will experience with different configurations\n")
    
    # Scenario 1: Perfect match - UTF-8
    demo_scenario(
        "Perfect UTF-8 match",
        api_charset='utf-8',
        user_charset='utf-8'
    )
    
    # Scenario 2: User mistake - API is UTF-8 but user selects ISO
    demo_scenario(
        "User selects ISO but API is UTF-8 (PROBLEM)",
        api_charset='utf-8',
        user_charset='iso-8859-1'
    )
    
    # Scenario 3: Perfect match - ISO-8859-1
    demo_scenario(
        "Perfect ISO-8859-1 match (old systems)",
        api_charset='iso-8859-1',
        user_charset='iso-8859-1'
    )
    
    # Scenario 4: User mistake - API is ISO but user selects UTF-8
    demo_scenario(
        "User selects UTF-8 but API is ISO (rare)",
        api_charset='iso-8859-1',
        user_charset='utf-8'
    )
    
    print("\n" + "="*70)
    print("Summary:")
    print("  - Auto-detection helps users avoid encoding problems")
    print("  - Warnings appear when detected charset != user selection")
    print("  - Most modern Ökofen systems use UTF-8")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
