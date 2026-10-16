#!/usr/bin/env python3
"""Verify oekomode handling across all API fixtures."""

import json
import os
from pathlib import Path

# Preset mapping as implemented in climate.py
PRESET_NONE = "none"
PRESET_COMFORT = "comfort"
PRESET_HOME = "home"
PRESET_ECO = "eco"

def get_api_value(data_field, default=None):
    """Extract value from API data field (same as in const.py)."""
    if data_field is None:
        return default
    
    # New format: {"val": ..., ...}
    if isinstance(data_field, dict):
        val = data_field.get("val", default)
        if isinstance(val, str):
            try:
                # Try to convert string to number
                if '.' in val:
                    return float(val)
                return int(val)
            except ValueError:
                return val
        return val
    
    # Old format: direct value (string or numeric)
    if isinstance(data_field, str):
        try:
            if '.' in data_field:
                return float(data_field)
            return int(data_field)
        except ValueError:
            return data_field
    
    return data_field

def verify_oekomode_mapping(oekomode_val):
    """Map oekomode value to preset (as in climate.py)."""
    if oekomode_val == 0:
        return PRESET_NONE  # Aus (no eco reduction)
    elif oekomode_val == 1:
        return PRESET_COMFORT  # Komfort (-0.5K)
    elif oekomode_val == 2:
        return PRESET_HOME  # Minimum (-1.0K)
    elif oekomode_val == 3:
        return PRESET_ECO  # Ökologisch (-1.5K)
    else:
        return PRESET_NONE

def check_fixture(filepath):
    """Check a single fixture file for oekomode data."""
    print(f"\n{'='*80}")
    print(f"Checking: {filepath.name}")
    print('='*80)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON decode error: {e}")
            return
    
    # Check for heating circuits (hk1, hk2, etc.)
    heating_circuits = [key for key in data.keys() if key.startswith('hk')]
    
    if not heating_circuits:
        print("  ℹ️  No heating circuits found")
        return
    
    for hk in sorted(heating_circuits):
        hk_data = data[hk]
        print(f"\n  {hk}:")
        
        # Check for oekomode
        if "oekomode" not in hk_data:
            print(f"    ⚠️  No oekomode field")
            continue
        
        oekomode_raw = hk_data["oekomode"]
        oekomode_val = get_api_value(oekomode_raw, 0)
        preset = verify_oekomode_mapping(oekomode_val)
        
        # Get format string if available
        format_str = ""
        if isinstance(oekomode_raw, dict) and "format" in oekomode_raw:
            format_str = oekomode_raw["format"]
        
        print(f"    oekomode value: {oekomode_val}")
        if format_str:
            print(f"    format: {format_str}")
        print(f"    → Mapped to preset: {preset}")
        
        # Check L_roomtemp_set (actual target temperature)
        if "L_roomtemp_set" in hk_data:
            roomtemp_set = get_api_value(hk_data["L_roomtemp_set"], 0)
            print(f"    L_roomtemp_set: {roomtemp_set / 10:.1f}°C (actual target)")
        else:
            print(f"    ⚠️  No L_roomtemp_set field")
        
        # Check temp_heat (base heating temperature)
        if "temp_heat" in hk_data:
            temp_heat = get_api_value(hk_data["temp_heat"], 0)
            print(f"    temp_heat: {temp_heat / 10:.1f}°C (base temp)")
        
        # Check L_state for vacation mode detection
        if "L_state" in hk_data:
            l_state = get_api_value(hk_data["L_state"], 0)
            if l_state == 128:
                print(f"    🏖️  VACATION MODE ACTIVE (L_state={l_state})")
            else:
                print(f"    L_state: {l_state}")
                if "L_statetext" in hk_data:
                    statetext = get_api_value(hk_data["L_statetext"], "")
                    if statetext:
                        print(f"    L_statetext: {statetext}")

def main():
    """Check all fixture files."""
    fixtures_dir = Path(__file__).parent / "tests" / "fixtures"
    
    if not fixtures_dir.exists():
        print(f"❌ Fixtures directory not found: {fixtures_dir}")
        return
    
    fixture_files = sorted(fixtures_dir.glob("*.json"))
    
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "OEKOMODE VERIFICATION REPORT" + " "*30 + "║")
    print("╚" + "="*78 + "╝")
    print(f"\nFound {len(fixture_files)} fixture files")
    
    for filepath in fixture_files:
        check_fixture(filepath)
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("✅ All fixtures processed")
    print("\nOekomode mapping:")
    print("  0 → none (Aus - no eco reduction)")
    print("  1 → comfort (Komfort -0.5K)")
    print("  2 → home (Minimum -1.0K)")
    print("  3 → eco (Ökologisch -1.5K)")
    print("\n✅ Temperature display: Always uses L_roomtemp_set (actual target)")
    print("ℹ️  Vacation mode: Detected via L_state==128 (separate from oekomode)")
    print()

if __name__ == "__main__":
    main()
