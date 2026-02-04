#!/usr/bin/env python3
"""Check for writable keys that might be ignored."""
import json

# Lade eine Test-Fixture
with open('tests/fixtures/api_response_basic_yo_2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Finde Keys OHNE L_ prefix
non_l_keys = []
for component, comp_data in data.items():
    if component == 'error' or not isinstance(comp_data, dict):
        continue
    for key, value in comp_data.items():
        if not key.startswith('L_') and isinstance(value, dict) and 'val' in value:
            has_format = 'format' in value and '|' in str(value.get('format', ''))
            has_minmax = 'min' in value and 'max' in value
            non_l_keys.append({
                'component': component,
                'key': key,
                'has_format': has_format,
                'has_minmax': has_minmax,
                'value': value
            })

print(f'Gefunden: {len(non_l_keys)} Keys ohne L_ prefix\n')

print('Alle writable Keys:')
print('=' * 80)
for item in non_l_keys:
    entity_type = 'IGNORED'
    if item['has_format']:
        entity_type = 'Select'
    elif item['has_minmax']:
        entity_type = 'Number'
    
    print(f"{entity_type:10} | {item['component']:8} | {item['key']:25} | min/max: {item['has_minmax']} | format: {item['has_format']}")

print('\n\nKeys die IGNORIERT werden würden:')
print('=' * 80)
ignored_count = 0
for item in non_l_keys:
    if not item['has_format'] and not item['has_minmax']:
        ignored_count += 1
        print(f"Component: {item['component']:8} | Key: {item['key']:25} | Data: {item['value']}")

print(f"\n\nZusammenfassung: {ignored_count} von {len(non_l_keys)} writable Keys werden IGNORIERT!")
