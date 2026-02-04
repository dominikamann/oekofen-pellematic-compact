#!/usr/bin/env python3
"""Calculate correct entity counts for all fixtures."""
import sys
sys.path.insert(0, '/Users/dominikamannprivat/Documents/Code/oekofen-pellematic-compact')

from tests.conftest import load_fixture
from custom_components.oekofen_pellematic_compact.dynamic_discovery import discover_all_entities

fixtures = [
    "api_response_basic.json",
    "api_response_basic_yo_2.json",
    "api_response_basic_m9.json",
    "api_response_green_kn.json",
    "api_response_sk_lxy.json",
    "api_response_with_se_ml.json",
    "api_response_with_sk_dash.json",
    "api_response_base_csta.json",
    "api_response_base_srqu.json",
    "api_response_base_da.json",
]

print("Fixture Entity Counts:")
print("=" * 80)

total_sum = 0

for filename in fixtures:
    data = load_fixture(filename)
    discovered = discover_all_entities(data)
    
    count = (len(discovered['sensors']) + len(discovered['binary_sensors']) +
             len(discovered['selects']) + len(discovered['numbers']))
    
    total_sum += count
    
    print(f'("{filename}", {count}),')

print("=" * 80)
print(f"Total entities across all fixtures: {total_sum}")
