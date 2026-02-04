# Tests für Ökofen Pellematic Integration

## Übersicht

Die Test-Suite validiert die Auto-Discovery-Funktionalität der Integration.

## Struktur

```
tests/
├── __init__.py           # Test-Package
├── conftest.py           # Pytest-Konfiguration und Fixtures
├── test_discovery.py     # Tests für Auto-Discovery
└── fixtures/
    └── api_response_basic.json  # Echte API-Daten (anonymisiert)
```

## Ausführen der Tests

### Voraussetzungen

```bash
pip install pytest
```

### Tests ausführen

```bash
# Alle Tests
pytest tests/

# Nur Discovery-Tests
pytest tests/test_discovery.py

# Mit Ausgabe
pytest tests/ -v

# Mit Coverage
pytest tests/ --cov=custom_components.oekofen_pellematic_compact
```

## Test-Fälle

### ✅ test_discovery_basic_setup
Testet die Discovery mit einer Standard-Konfiguration:
- 1 Heizkreis (hk1)
- 1 Warmwasser (ww1)
- 1 Pellematic Heater (pe1)
- 1 Pufferspeicher (pu1)

Basiert auf echten API-Daten.

### ✅ test_discovery_multiple_heating_circuits
Testet mehrere Heizkreise (hk1, hk2, hk3).

### ✅ test_discovery_with_solar
Testet Solar-Komponenten (SK und SE).

### ✅ test_discovery_with_heat_pump
Testet Wärmepumpen-Erkennung.

### ✅ test_discovery_with_special_components
Testet Stirling, Circulator und Smart PV.

### ✅ test_discovery_with_wireless_sensors
Testet Wireless-Sensor-Erkennung.

### ✅ test_discovery_empty_api_response
Testet leere API-Antwort.

### ✅ test_discovery_complex_setup
Testet komplexes Setup mit allen Komponenten.

### ✅ test_discovery_ignores_non_numeric_suffixes
Stellt sicher, dass nur numerische Suffixe gezählt werden.

## Fixtures

### api_response_basic.json
Echte API-Antwort von einem Pellematic Compact mit:
- System-Daten (Außentemperatur, Fehler, etc.)
- 1 Heizkreis mit allen Parametern
- 1 Pufferspeicher
- 1 Warmwasser
- 1 Pellematic Heater mit Statistiken

Passwort wurde anonymisiert.

## Neue Tests hinzufügen

1. Neue Fixture erstellen in `fixtures/`:
```json
{
  "system": {},
  "hk1": {},
  ...
}
```

2. Test in `test_discovery.py` hinzufügen:
```python
def test_my_scenario():
    api_data = load_fixture("my_scenario.json")
    discovered = discover_components_from_api(api_data)
    assert discovered[CONF_NUM_OF_HEATING_CIRCUIT] == 2
```

## CI/CD Integration

Die Tests können in GitHub Actions integriert werden:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install pytest
      - run: pytest tests/
```

## Verifizierte Setups

### ✅ Basic Setup (Real)
- Quelle: Echte API-Daten
- Komponenten: 1 HK, 1 WW, 1 PE, 1 PU
- Status: Vollständig getestet

### ⏳ Erweiterte Setups (Mock)
- Multiple Heizkreise
- Solar-Anlagen
- Wärmepumpen
- Wireless Sensoren
- Kombination aller Komponenten

## Bekannte Einschränkungen

- Tests benötigen keine Home Assistant Installation
- Discovery-Funktion wird isoliert getestet
- Integration-Tests mit echter HA folgen später
