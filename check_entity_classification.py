#!/usr/bin/env python3
"""Check entity classification for Ökofen integration."""

import json
from custom_components.oekofen_pellematic_compact.dynamic_discovery import discover_all_entities

def check_classification(fixture_file):
    """Check entity classification for a fixture file."""
    print(f"\n{'='*80}")
    print(f"Checking: {fixture_file}")
    print(f"{'='*80}")
    
    with open(fixture_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    result = discover_all_entities(data)
    
    # Find all storage_fill related entities
    storage_entities = {
        'sensors': [],
        'numbers': [],
        'selects': []
    }
    
    for entity_type in ['sensors', 'numbers', 'selects']:
        for entity in result[entity_type]:
            if 'storage' in entity['key'].lower() or 'pellet' in entity['key'].lower():
                storage_entities[entity_type].append(entity)
    
    # Display results
    print("\n📊 Storage/Pellet Related Entities:\n")
    
    print("✅ SENSORS (Read-Only):")
    for sens in storage_entities['sensors']:
        print(f"   • {sens['component']:8} | {sens['key']:30} -> {sens['name']}")
    
    if storage_entities['numbers']:
        print("\n⚠️  NUMBERS (Writable - SHOULD BE EMPTY!):")
        for num in storage_entities['numbers']:
            print(f"   • {num['component']:8} | {num['key']:30} -> {num['name']}")
    else:
        print("\n✅ NUMBERS: None (correct!)")
    
    if storage_entities['selects']:
        print("\n📋 SELECTS:")
        for sel in storage_entities['selects']:
            print(f"   • {sel['component']:8} | {sel['key']:30} -> {sel['name']}")
    
    # Summary
    print(f"\n📈 Summary:")
    print(f"   Total Sensors:  {len(result['sensors']):4}")
    print(f"   Total Numbers:  {len(result['numbers']):4}")
    print(f"   Total Selects:  {len(result['selects']):4}")
    print(f"   Total Binary:   {len(result['binary_sensors']):4}")
    print(f"   TOTAL:          {sum(len(result[k]) for k in result):4}")

if __name__ == "__main__":
    import sys
    
    fixtures = [
        'tests/fixtures/api_response_basic.json',
        'tests/fixtures/api_response_basic_m9.json',
        'tests/fixtures/api_response_basic_yo_2.json',
    ]
    
    for fixture in fixtures:
        try:
            check_classification(fixture)
        except FileNotFoundError:
            print(f"❌ File not found: {fixture}")
        except Exception as e:
            print(f"❌ Error processing {fixture}: {e}")
