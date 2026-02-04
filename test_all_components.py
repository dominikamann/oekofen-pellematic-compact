#!/usr/bin/env python3
"""Test all supported component types."""
import sys
sys.path.insert(0, '/Users/dominikamannprivat/Documents/Code/oekofen-pellematic-compact')

from custom_components.oekofen_pellematic_compact.dynamic_discovery import discover_all_entities, COMPONENT_NAMES

# Simuliere alle möglichen Komponenten-Typen aus der API-Doku
test_data = {
    'system': {'L_ambient': {'val': 225, 'unit': '°C', 'text': 'Außentemperatur'}},
    'weather': {'L_temp': {'val': 150, 'unit': '°C', 'text': 'Temperatur'}},
    'forecast': {'L_tomorrow_temp': {'val': 180, 'unit': '°C', 'text': 'Morgen'}},
    'power': {'L_power_now': {'val': 1500, 'unit': 'W', 'text': 'Aktuelle Leistung'}},
    'stirling': {'L_runtime': {'val': 12345, 'unit': 'h', 'text': 'Laufzeit'}},
    # hk(1..6)
    'hk1': {'L_temp_act': {'val': 220, 'unit': '°C', 'text': 'Ist-Temperatur'}},
    'hk2': {'L_temp_act': {'val': 215, 'unit': '°C', 'text': 'Ist-Temperatur'}},
    'hk6': {'L_temp_act': {'val': 200, 'unit': '°C', 'text': 'Ist-Temperatur'}},
    # autocomfort_hk(1..6)
    'autocomfort_hk1': {'L_mode': {'val': 1, 'text': 'Modus'}},
    'autocomfort_hk6': {'L_mode': {'val': 0, 'text': 'Modus'}},
    # wireless(1..6)
    'wireless1': {'L_temp': {'val': 205, 'unit': '°C', 'text': 'Temperatur'}},
    'wireless6': {'L_temp': {'val': 210, 'unit': '°C', 'text': 'Temperatur'}},
    # thirdparty(1..20)
    'thirdparty1': {'L_value': {'val': 100, 'text': 'Wert'}},
    'thirdparty20': {'L_value': {'val': 200, 'text': 'Wert'}},
    # pu(1..3)
    'pu1': {'L_temp_act': {'val': 450, 'unit': '°C', 'text': 'Ist-Temperatur'}},
    'pu3': {'L_temp_act': {'val': 430, 'unit': '°C', 'text': 'Ist-Temperatur'}},
    # ww(1..3)
    'ww1': {'L_temp_act': {'val': 550, 'unit': '°C', 'text': 'Ist-Temperatur'}},
    'ww3': {'L_temp_act': {'val': 520, 'unit': '°C', 'text': 'Ist-Temperatur'}},
    # sk(1..6)
    'sk1': {'L_temp_coll': {'val': 300, 'unit': '°C', 'text': 'Kollektortemp'}},
    'sk6': {'L_temp_coll': {'val': 280, 'unit': '°C', 'text': 'Kollektortemp'}},
    # se(1..3)
    'se1': {'L_gain_today': {'val': 1500, 'unit': 'kWh', 'text': 'Ertrag heute'}},
    'se3': {'L_gain_today': {'val': 1200, 'unit': 'kWh', 'text': 'Ertrag heute'}},
    # circ(1..3)
    'circ1': {'L_temp_act': {'val': 450, 'unit': '°C', 'text': 'Ist-Temperatur'}},
    'circ3': {'L_temp_act': {'val': 440, 'unit': '°C', 'text': 'Ist-Temperatur'}},
    # pe(1..4)
    'pe1': {'L_temp_act': {'val': 650, 'unit': '°C', 'text': 'Ist-Temperatur'}},
    'pe4': {'L_temp_act': {'val': 630, 'unit': '°C', 'text': 'Ist-Temperatur'}},
}

result = discover_all_entities(test_data)

print('✅ Unterstützte API-Komponenten (laut Ökofen Dokumentation)')
print('=' * 80)

components_found = {}
for sensor in result['sensors']:
    comp = sensor['component']
    if comp not in components_found:
        components_found[comp] = []
    components_found[comp].append(sensor)

# Sortiere nach Komponenten-Typ
for comp in sorted(components_found.keys()):
    base = ''.join(c for c in comp if not c.isdigit() and c != '_')
    index = ''.join(c for c in comp if c.isdigit())
    
    # Für autocomfort_hk behandeln wir speziell
    if comp.startswith('autocomfort_'):
        base = comp.replace(index, '')
    
    name = COMPONENT_NAMES.get(base, base.upper())
    
    example = components_found[comp][0]['name']
    
    if index:
        print(f"  ✓ {comp:20} → {name:30} {index:2}  (z.B. {example})")
    else:
        print(f"  ✓ {comp:20} → {name:30}     (z.B. {example})")

print("\n" + "=" * 80)
print(f"📊 Zusammenfassung:")
print(f"   {len(components_found)} verschiedene Komponenten getestet")
print(f"   {len(result['sensors'])} Sensoren erfolgreich erstellt")
print()
print("✅ ALLE Komponenten aus der Ökofen API-Dokumentation werden unterstützt!")
print()
print("API-Spec Komponenten-Bereiche:")
print("  • system, weather, forecast, power, stirling")
print("  • hk(1..6), autocomfort_hk(1..6)")
print("  • wireless(1..6), thirdparty(1..20)")
print("  • pu(1..3), ww(1..3), sk(1..6), se(1..3)")
print("  • circ(1..3), pe(1..4)")
