#!/usr/bin/env python3
"""Standalone test for migration pattern matching (no HA dependencies)."""

import re
import sys


def _generate_old_entity_id_patterns():
    """Generate patterns for old entity IDs that might need migration.
    
    Returns:
        List of tuples (platform, old_pattern, new_component_prefix)
    """
    patterns = []
    
    # Pellematic heater sensors: heater_1_xxx -> pe1_xxx
    # Match: sensor.{anything}_heater_{number}_{rest}
    patterns.append(("sensor", r"^sensor\..+_heater_(\d+)_(.+)$", "pe"))
    
    # Heating circuit sensors: heating_circuit_1_xxx -> hk1_xxx
    patterns.append(("sensor", r"^sensor\..+_heating_circuit_(\d+)_(.+)$", "hk"))
    
    # Hot water sensors: hot_water_1_xxx -> ww1_xxx
    patterns.append(("sensor", r"^sensor\..+_hot_water_(\d+)_(.+)$", "ww"))
    
    # Buffer storage sensors: buffer_storage_1_xxx -> pu1_xxx
    patterns.append(("sensor", r"^sensor\..+_buffer_storage_(\d+)_(.+)$", "pu"))
    
    # Climate entities
    patterns.append(("climate", r"^climate\..+_heating_circuit_(\d+)_climate$", "hk"))
    
    return patterns


def test_pattern_generation():
    """Test that patterns are generated correctly."""
    patterns = _generate_old_entity_id_patterns()
    
    print(f"✓ Generated {len(patterns)} patterns")
    assert len(patterns) > 0, "No patterns generated"
    
    # Check that we have expected patterns
    pattern_dict = {(p[0], p[2]): p[1] for p in patterns}
    
    assert ('sensor', 'pe') in pattern_dict, "Missing heater pattern"
    assert ('sensor', 'hk') in pattern_dict, "Missing heating circuit pattern"
    assert ('sensor', 'ww') in pattern_dict, "Missing hot water pattern"
    assert ('sensor', 'pu') in pattern_dict, "Missing buffer storage pattern"
    assert ('climate', 'hk') in pattern_dict, "Missing climate pattern"
    
    print("✓ All expected pattern types found")
    return True


def test_heater_pattern_matching():
    """Test heater pattern matching."""
    patterns = _generate_old_entity_id_patterns()
    heater_pattern = next(p for p in patterns if "heater" in p[1])
    
    test_cases = [
        ("sensor.pellematic_heater_1_temperature", True),
        ("sensor.my_system_heater_2_power", True),
        ("sensor.pellematic_heater_10_status", True),
        ("sensor.pellematic_pe1_L_temp_act", False),
        ("sensor.pellematic_pe1_temperature", False),
        ("climate.pellematic_heater_1_climate", False),  # Wrong platform
    ]
    
    for entity_id, should_match in test_cases:
        match = re.match(heater_pattern[1], entity_id)
        matched = match is not None
        
        if matched == should_match:
            status = "✓"
        else:
            status = "✗"
            print(f"{status} FAIL: {entity_id} - Expected: {should_match}, Got: {matched}")
            return False
        
        print(f"{status} {entity_id}: {'matches' if matched else 'no match'} (expected: {should_match})")
    
    print("✓ All heater pattern tests passed")
    return True


def test_heating_circuit_pattern_matching():
    """Test heating circuit pattern matching."""
    patterns = _generate_old_entity_id_patterns()
    hk_pattern = next(p for p in patterns if p[0] == 'sensor' and "heating_circuit" in p[1])
    
    test_cases = [
        ("sensor.pellematic_heating_circuit_1_temperature", True),
        ("sensor.my_heating_circuit_3_status", True),
        ("sensor.pellematic_hk1_L_roomtemp_act", False),
        ("climate.pellematic_heating_circuit_1_climate", False),  # Wrong platform
    ]
    
    for entity_id, should_match in test_cases:
        match = re.match(hk_pattern[1], entity_id)
        matched = match is not None
        
        if matched == should_match:
            status = "✓"
        else:
            status = "✗"
            print(f"{status} FAIL: {entity_id} - Expected: {should_match}, Got: {matched}")
            return False
        
        print(f"{status} {entity_id}: {'matches' if matched else 'no match'} (expected: {should_match})")
    
    print("✓ All heating circuit pattern tests passed")
    return True


def test_climate_pattern_matching():
    """Test climate pattern matching."""
    patterns = _generate_old_entity_id_patterns()
    climate_pattern = next(p for p in patterns if p[0] == 'climate')
    
    test_cases = [
        ("climate.pellematic_heating_circuit_1_climate", True),
        ("climate.my_system_heating_circuit_2_climate", True),
        ("climate.pellematic_hk1_climate", False),
        ("sensor.pellematic_heating_circuit_1_climate", False),  # Wrong platform
    ]
    
    for entity_id, should_match in test_cases:
        match = re.match(climate_pattern[1], entity_id)
        matched = match is not None
        
        if matched == should_match:
            status = "✓"
        else:
            status = "✗"
            print(f"{status} FAIL: {entity_id} - Expected: {should_match}, Got: {matched}")
            return False
        
        print(f"{status} {entity_id}: {'matches' if matched else 'no match'} (expected: {should_match})")
    
    print("✓ All climate pattern tests passed")
    return True


def test_hot_water_pattern_matching():
    """Test hot water pattern matching."""
    patterns = _generate_old_entity_id_patterns()
    ww_pattern = next(p for p in patterns if p[2] == 'ww')
    
    test_cases = [
        ("sensor.pellematic_hot_water_1_temperature", True),
        ("sensor.system_hot_water_2_status", True),
        ("sensor.pellematic_ww1_L_temp_act", False),
    ]
    
    for entity_id, should_match in test_cases:
        match = re.match(ww_pattern[1], entity_id)
        matched = match is not None
        
        if matched == should_match:
            status = "✓"
        else:
            status = "✗"
            print(f"{status} FAIL: {entity_id} - Expected: {should_match}, Got: {matched}")
            return False
        
        print(f"{status} {entity_id}: {'matches' if matched else 'no match'} (expected: {should_match})")
    
    print("✓ All hot water pattern tests passed")
    return True


def test_buffer_storage_pattern_matching():
    """Test buffer storage pattern matching."""
    patterns = _generate_old_entity_id_patterns()
    pu_pattern = next(p for p in patterns if p[2] == 'pu')
    
    test_cases = [
        ("sensor.pellematic_buffer_storage_1_temperature", True),
        ("sensor.system_buffer_storage_2_level", True),
        ("sensor.pellematic_pu1_L_temp_top", False),
    ]
    
    for entity_id, should_match in test_cases:
        match = re.match(pu_pattern[1], entity_id)
        matched = match is not None
        
        if matched == should_match:
            status = "✓"
        else:
            status = "✗"
            print(f"{status} FAIL: {entity_id} - Expected: {should_match}, Got: {matched}")
            return False
        
        print(f"{status} {entity_id}: {'matches' if matched else 'no match'} (expected: {should_match})")
    
    print("✓ All buffer storage pattern tests passed")
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("MIGRATION PATTERN TESTING (Standalone)")
    print("=" * 70)
    print()
    
    tests = [
        ("Pattern Generation", test_pattern_generation),
        ("Heater Pattern Matching", test_heater_pattern_matching),
        ("Heating Circuit Pattern Matching", test_heating_circuit_pattern_matching),
        ("Climate Pattern Matching", test_climate_pattern_matching),
        ("Hot Water Pattern Matching", test_hot_water_pattern_matching),
        ("Buffer Storage Pattern Matching", test_buffer_storage_pattern_matching),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'─' * 70}")
        print(f"TEST: {test_name}")
        print(f"{'─' * 70}")
        
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name}: PASSED")
            else:
                failed += 1
                print(f"✗ {test_name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name}: FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
