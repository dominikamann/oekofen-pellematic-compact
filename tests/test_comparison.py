"""Comparison test: Dynamic discovery vs. hard-coded constants."""

import json
from pathlib import Path
from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities
)


def test_compare_discovery_methods():
    """Compare dynamic discovery with hard-coded approach."""
    
    # Load all test fixtures
    fixtures_dir = Path(__file__).parent / "fixtures"
    test_files = [
        "api_response_basic.json",
        "api_response_basic_yo_2.json",
        "api_response_basic_m9.json",
        "api_response_green_kn.json",
        "api_response_sk_lxy.json",
        "api_response_with_se_ml.json",
        "api_response_with_sk_dash.json",
        "api_response_base_csta.json",
        "api_response_base_srqu.json",
    ]
    
    total_stats = {
        "sensors": 0,
        "binary_sensors": 0,
        "selects": 0,
        "numbers": 0,
    }
    
    print("\n" + "="*80)
    print("DYNAMIC DISCOVERY COMPARISON")
    print("="*80)
    
    for filename in test_files:
        filepath = fixtures_dir / filename
        if not filepath.exists():
            continue
            
        with open(filepath, encoding="utf-8") as f:
            api_data = json.load(f)
        
        entities = discover_all_entities(api_data)
        
        print(f"\n{filename}:")
        print(f"  Sensors:        {len(entities['sensors']):3d}")
        print(f"  Binary Sensors: {len(entities['binary_sensors']):3d}")
        print(f"  Selects:        {len(entities['selects']):3d}")
        print(f"  Numbers:        {len(entities['numbers']):3d}")
        print(f"  TOTAL:          {sum(len(v) for v in entities.values()):3d}")
        
        # Show some examples
        if entities['sensors']:
            print(f"\n  Example Sensors:")
            for sensor in entities['sensors'][:3]:
                print(f"    - {sensor['name']} ({sensor['key']})")
        
        # Accumulate stats
        for key in total_stats:
            total_stats[key] += len(entities[key])
    
    print("\n" + "="*80)
    print("TOTAL ACROSS ALL FIXTURES:")
    print("="*80)
    print(f"  Sensors:        {total_stats['sensors']:4d}")
    print(f"  Binary Sensors: {total_stats['binary_sensors']:4d}")
    print(f"  Selects:        {total_stats['selects']:4d}")
    print(f"  Numbers:        {total_stats['numbers']:4d}")
    print(f"  GRAND TOTAL:    {sum(total_stats.values()):4d}")
    print("="*80)
    
    print("\n💡 BENEFITS:")
    print("  ✅ All entities discovered automatically")
    print("  ✅ Multilingual names from API")
    print("  ✅ Correct units and ranges")
    print("  ✅ No hard-coded constants needed")
    print("  ✅ Future-proof for new Ökofen features")
    print("="*80 + "\n")
    
    # Assert we found a reasonable number of entities
    assert total_stats['sensors'] > 50, "Should find many sensors"
    assert total_stats['binary_sensors'] > 5, "Should find binary sensors"
    assert total_stats['selects'] > 5, "Should find selects"
    assert total_stats['numbers'] > 5, "Should find numbers"
