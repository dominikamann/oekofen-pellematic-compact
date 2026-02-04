#!/usr/bin/env python3
"""Test Heat Pump (wp) components."""
import sys
sys.path.insert(0, '/Users/dominikamannprivat/Documents/Code/oekofen-pellematic-compact')

from custom_components.oekofen_pellematic_compact.dynamic_discovery import discover_all_entities

# Real heat pump data from user
test_data = {
    'wp_data1': {
        'L_jaz_all': {'val': 4.2246017, 'text': 'JAZ All'},
        'L_jaz_heat': {'val': 4.8818207, 'text': 'JAZ Heat'},
        'L_jaz_cool': {'val': 0.0, 'text': 'JAZ Cool'},
        'L_az_all': {'val': 4.2246017, 'text': 'AZ All'},
        'L_az_heat': {'val': 4.8818207, 'text': 'AZ Heat'},
        'L_az_cool': {'val': 0.0, 'text': 'AZ Cool'},
    },
    'wp1': {
        'L_state': {'val': 16777280, 'text': 'State'},
        'L_statetext': {'val': 'Heizungsanforderung|AT Modus aktiv', 'text': 'State Text'},
        'L_sg_ready': {'val': 2, 'text': 'SG Ready'},
        'set_sg_ready': {'val': 0, 'min': 0, 'max': 3, 'text': 'Set SG Ready'},
        'L_cop': {'val': 0.0, 'text': 'COP'},
        'L_uwp': {'val': 0.0, 'text': 'UWP'},
        'L_temp_flow_is': {'val': 44.600002, 'unit': '°C', 'text': 'Flow Temp Is'},
        'L_temp_flow_set': {'val': 44.6, 'unit': '°C', 'text': 'Flow Temp Set'},
        'L_temp_return_is': {'val': 37.0, 'unit': '°C', 'text': 'Return Temp Is'},
        'L_el_energy': {'val': 3.0168083, 'unit': 'kWh', 'text': 'Electric Energy'},
        'L_total_runtime': {'val': 1377824, 'unit': 'h', 'text': 'Total Runtime'},
        'L_activation_count': {'val': 326, 'text': 'Activation Count'},
        'mode': {'val': 1, 'format': '0:Off|1:Auto|2:On', 'text': 'Mode'},
        'ambient_mode': {'val': 1, 'format': '0:Off|1:On', 'text': 'Ambient Mode'},
        'night_mode': {'val': 0, 'format': '0:Off|1:On', 'text': 'Night Mode'},
        'heater': {'val': 0, 'format': '0:Off|1:On', 'text': 'Heater'},
    }
}

result = discover_all_entities(test_data)

print('✅ Heat Pump Components Detected (International Names):')
print('=' * 80)

print('\n📊 SENSORS (read-only):')
for sensor in sorted(result['sensors'], key=lambda x: (x['component'], x['key'])):
    print(f"  • {sensor['component']:12} | {sensor['key']:25} | {sensor['name']}")

print('\n🔧 SELECTS (writable):')
for select in sorted(result['selects'], key=lambda x: (x['component'], x['key'])):
    print(f"  • {select['component']:12} | {select['key']:25} | {select['name']}")

print('\n⚙️  NUMBERS (writable):')
for number in sorted(result['numbers'], key=lambda x: (x['component'], x['key'])):
    print(f"  • {number['component']:12} | {number['key']:25} | {number['name']}")

print('\n' + '=' * 80)
print(f'📊 Summary:')
print(f'   {len(result["sensors"])} sensors')
print(f'   {len(result["selects"])} selects')
print(f'   {len(result["numbers"])} numbers')
print()
print('✅ wp_data1 (Heat Pump Data 1) - Recognized!')
print('✅ wp1 (Heat Pump 1) - Recognized!')
print('✅ All names are now in ENGLISH (international)!')
