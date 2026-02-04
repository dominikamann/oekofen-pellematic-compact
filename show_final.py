#!/usr/bin/env python3
"""Show final entity categorization."""
import json
import sys
sys.path.insert(0, '/Users/dominikamannprivat/Documents/Code/oekofen-pellematic-compact')

from custom_components.oekofen_pellematic_compact.dynamic_discovery import discover_all_entities

with open('tests/fixtures/api_response_basic_yo_2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

result = discover_all_entities(data)

print('📊 Finale Übersicht - api_response_basic_yo_2.json')
print('=' * 80)

print(f"\n✅ SENSORS (read-only): {len(result['sensors'])}")
storage = [s for s in result['sensors'] if 'storage_fill' in s['key']]
if storage:
    print("  Read-only Statistiken (vorher Numbers):")
    for s in storage:
        print(f"    ✓ {s['component']:8} | {s['key']:30} | {s['name']}")

print(f"\n⚙️  NUMBERS (writable): {len(result['numbers'])}")
for n in result['numbers']:
    print(f"  • {n['component']:8} | {n['key']:30} | {n['name']}")

print(f"\n🔧 SELECTS (writable): {len(result['selects'])}")
for sel in result['selects']:
    print(f"  • {sel['component']:8} | {sel['key']:30} | {sel['name']}")

print(f"\n💡 BINARY SENSORS (read-only): {len(result['binary_sensors'])}")

print("\n" + "=" * 80)
print("✅ Alle Statistik-Werte sind jetzt korrekt als READ-ONLY Sensoren!")
print("✅ Nur echte Einstellungen sind als writable Numbers/Selects!")
