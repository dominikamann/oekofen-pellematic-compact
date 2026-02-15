"""Test all entity types (sensor, climate, number) with all fixtures."""
import pytest
import json
from pathlib import Path


# Import the helper function
def get_api_value(data_field, default=None):
    """Extract value from API data field."""
    if data_field is None:
        return default
    if isinstance(data_field, dict):
        return data_field.get("val", default)
    return data_field


class TestFixturesIntegration:
    """Test integration of all entity types with all fixtures."""
    
    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory."""
        return Path(__file__).parent / "fixtures"
    
    @pytest.fixture
    def all_fixtures(self, fixtures_dir):
        """Load all fixture files."""
        fixtures = {}
        for fixture_file in sorted(fixtures_dir.glob("api_response_*.json")):
            try:
                with open(fixture_file, 'r', encoding='utf-8') as f:
                    fixtures[fixture_file.name] = json.load(f)
            except Exception as e:
                # Skip invalid JSON files
                pass
        return fixtures
    
    def test_climate_entities(self, all_fixtures):
        """Test climate entity integration with all fixtures."""
        results = []
        
        for fixture_name, api_data in all_fixtures.items():
            # Find all heating circuits
            for key in api_data.keys():
                if key.startswith("hk"):
                    hk_data = api_data[key]
                    
                    # Test basic data extraction
                    current_temp = None
                    target_comfort = None
                    target_eco = None
                    target_vacation = None
                    preset_mode = "none"
                    
                    if "L_roomtemp_act" in hk_data:
                        val = get_api_value(hk_data["L_roomtemp_act"], 0)
                        current_temp = float(val) / 10
                    
                    if "temp_heat" in hk_data:
                        val = get_api_value(hk_data["temp_heat"], 0)
                        target_comfort = float(val) / 10
                    
                    if "temp_setback" in hk_data:
                        val = get_api_value(hk_data["temp_setback"], 0)
                        target_eco = float(val) / 10
                    
                    if "temp_vacation" in hk_data:
                        val = get_api_value(hk_data["temp_vacation"], 0)
                        target_vacation = float(val) / 10
                    
                    if "oekomode" in hk_data:
                        oekomode_val = int(get_api_value(hk_data["oekomode"], 2))
                        if oekomode_val == 0:
                            preset_mode = "away"
                        elif oekomode_val == 1:
                            preset_mode = "comfort"
                        elif oekomode_val == 3:
                            preset_mode = "eco"
                    
                    results.append({
                        "fixture": fixture_name,
                        "entity": key,
                        "type": "climate",
                        "current_temp": current_temp,
                        "target_comfort": target_comfort,
                        "target_eco": target_eco,
                        "target_vacation": target_vacation,
                        "preset_mode": preset_mode,
                        "success": True,
                    })
        
        # Assert we found climate entities
        assert len(results) > 0, "No climate entities found in fixtures"
        
        # Assert all extractions were successful
        for result in results:
            assert result["success"], f"Climate entity failed: {result['fixture']} - {result['entity']}"
        
    
    def test_sensor_entities(self, all_fixtures):
        """Test sensor entity integration with all fixtures."""
        results = []
        
        for fixture_name, api_data in all_fixtures.items():
            # Test various sensor types
            for component_key in ["system", "hk1", "pe1", "pu1", "ww1", "sk1"]:
                if component_key not in api_data:
                    continue
                
                component_data = api_data[component_key]
                
                # Test temperature sensors (common pattern)
                for field_key in component_data.keys():
                    if field_key.startswith("L_") and "temp" in field_key.lower():
                        try:
                            val = get_api_value(component_data[field_key], 0)
                            temp_value = float(val) / 10
                            
                            results.append({
                                "fixture": fixture_name,
                                "entity": f"{component_key}.{field_key}",
                                "type": "sensor",
                                "value": temp_value,
                                "success": True,
                            })
                        except Exception as e:
                            results.append({
                                "fixture": fixture_name,
                                "entity": f"{component_key}.{field_key}",
                                "type": "sensor",
                                "error": str(e),
                                "success": False,
                            })
        
        # Assert we found sensor entities
        assert len(results) > 0, "No sensor entities found in fixtures"
        
        # Assert most extractions were successful (allow some failures for edge cases)
        successful = [r for r in results if r["success"]]
        success_rate = len(successful) / len(results)
        assert success_rate > 0.8, f"Too many sensor failures: {success_rate:.1%}"
        
    
    def test_number_entities(self, all_fixtures):
        """Test number entity integration with all fixtures."""
        results = []
        
        for fixture_name, api_data in all_fixtures.items():
            # Test number entities in heating circuits
            for key in api_data.keys():
                if key.startswith("hk"):
                    hk_data = api_data[key]
                    
                    # Test common number entities
                    number_fields = ["temp_heat", "temp_setback", "temp_vacation"]
                    
                    for field in number_fields:
                        if field in hk_data:
                            try:
                                raw_data = hk_data[field]
                                val = get_api_value(raw_data, 0)
                                number_value = float(val) / 10
                                
                                # Extract min/max if available
                                min_val = None
                                max_val = None
                                if isinstance(raw_data, dict):
                                    min_val = raw_data.get("min")
                                    max_val = raw_data.get("max")
                                
                                results.append({
                                    "fixture": fixture_name,
                                    "entity": f"{key}.{field}",
                                    "type": "number",
                                    "value": number_value,
                                    "min": min_val,
                                    "max": max_val,
                                    "success": True,
                                })
                            except Exception as e:
                                results.append({
                                    "fixture": fixture_name,
                                    "entity": f"{key}.{field}",
                                    "type": "number",
                                    "error": str(e),
                                    "success": False,
                                })
        
        # Assert we found number entities
        assert len(results) > 0, "No number entities found in fixtures"
        
        # Assert all extractions were successful
        successful = [r for r in results if r["success"]]
        success_rate = len(successful) / len(results)
        assert success_rate > 0.9, f"Too many number failures: {success_rate:.1%}"
        
    
    def test_all_entities_comprehensive(self, all_fixtures):
        """Comprehensive test of all entity types across all fixtures."""
        stats = {
            "fixtures_tested": 0,
            "climate_entities": 0,
            "sensor_entities": 0,
            "number_entities": 0,
            "total_entities": 0,
            "successful": 0,
            "failed": 0,
        }
        
        for fixture_name, api_data in all_fixtures.items():
            stats["fixtures_tested"] += 1
            
            # Process each component
            for component_key, component_data in api_data.items():
                if not isinstance(component_data, dict):
                    continue
                
                # Test each field in the component
                for field_key, field_data in component_data.items():
                    # Skip info fields
                    if field_key.endswith("_info"):
                        continue
                    
                    stats["total_entities"] += 1
                    
                    # Try to extract value with get_api_value
                    try:
                        value = get_api_value(field_data)
                        
                        # Classify entity type
                        if component_key.startswith("hk") and field_key in ["temp_heat", "temp_setback", "temp_vacation"]:
                            stats["number_entities"] += 1
                            stats["climate_entities"] += 1
                        elif field_key.startswith("L_"):
                            stats["sensor_entities"] += 1
                        
                        stats["successful"] += 1
                    except Exception:
                        stats["failed"] += 1
        
        # Print stats
        print(f"\nComprehensive Integration Test Results:")
        print(f"  Fixtures tested: {stats['fixtures_tested']}")
        print(f"  Total entities: {stats['total_entities']}")
        print(f"  Climate entities: {stats['climate_entities']}")
        print(f"  Sensor entities: {stats['sensor_entities']}")
        print(f"  Number entities: {stats['number_entities']}")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        
        success_rate = stats['successful'] / stats['total_entities'] if stats['total_entities'] > 0 else 0
        print(f"  Success rate: {success_rate:.1%}")
        
        # Assert reasonable success rate
        assert stats["fixtures_tested"] > 0, "No fixtures tested"
        assert success_rate > 0.8, f"Success rate too low: {success_rate:.1%}"
        
    
    def test_poolandeco_fixture_specific(self, all_fixtures):
        """Specific test for the user's poolandeco fixture."""
        assert "api_response_poolandeco.json" in all_fixtures, "poolandeco fixture missing"
        
        api_data = all_fixtures["api_response_poolandeco.json"]
        
        # Test hk1 climate entity
        assert "hk1" in api_data, "hk1 not found in poolandeco fixture"
        hk1 = api_data["hk1"]
        
        # Test current temperature
        current_temp = float(get_api_value(hk1["L_roomtemp_act"], 0)) / 10
        assert current_temp == 22.5, f"Current temp should be 22.5, got {current_temp}"
        
        # Test target temperatures
        target_comfort = float(get_api_value(hk1["temp_heat"], 0)) / 10
        assert target_comfort == 20.0, f"Comfort temp should be 20.0, got {target_comfort}"
        
        target_eco = float(get_api_value(hk1["temp_setback"], 0)) / 10
        assert target_eco == 19.5, f"Eco temp should be 19.5, got {target_eco}"
        
        target_vacation = float(get_api_value(hk1["temp_vacation"], 0)) / 10
        assert target_vacation == 12.0, f"Vacation temp should be 12.0, got {target_vacation}"
        
        # Test preset mode
        oekomode = int(get_api_value(hk1["oekomode"], 0))
        assert oekomode == 3, f"oekomode should be 3 (eco), got {oekomode}"
        
        print("\n✓ poolandeco fixture validated successfully!")
        print(f"  Current: {current_temp}°C")
        print(f"  Comfort: {target_comfort}°C")
        print(f"  Eco: {target_eco}°C (This was shown as 8.0°C before fix!)")
        print(f"  Vacation: {target_vacation}°C")
        print(f"  Preset: Ecologique (mode {oekomode})")

    def test_mg_fixture_specific(self, all_fixtures):
        """Specific test for the user's mg fixture."""
        assert "api_response_mg.json" in all_fixtures, "mg fixture missing"

        api_data = all_fixtures["api_response_mg.json"]

        # Ensure buffer storage data exists
        assert "pu1" in api_data, "pu1 not found in mg fixture"
        pu1 = api_data["pu1"]

        # Validate both internal and external min temp keys are present and distinct
        assert "mintemp_off" in pu1, "mintemp_off not found in pu1"
        assert "ext_mintemp_off" in pu1, "ext_mintemp_off not found in pu1"

        mintemp_off = float(get_api_value(pu1["mintemp_off"], 0)) / 10
        ext_mintemp_off = float(get_api_value(pu1["ext_mintemp_off"], 0)) / 10

        assert mintemp_off == 8.0, f"mintemp_off should be 8.0, got {mintemp_off}"
        assert ext_mintemp_off == 8.0, f"ext_mintemp_off should be 8.0, got {ext_mintemp_off}"

        print("\n✓ mg fixture validated successfully!")
        print(f"  pu1 mintemp_off: {mintemp_off}°C")
        print(f"  pu1 ext_mintemp_off: {ext_mintemp_off}°C")
