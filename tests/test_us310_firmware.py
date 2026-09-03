"""Regression test for issue #191: US firmware 3.10 (bare values, no metadata).

The /all response contains bare string values only. Discovery must still
produce read-only sensors so entities populate.
"""
from tests.conftest import load_fixture
from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
)


def test_us310_bare_values_discover_sensors():
    data = load_fixture("api_response_us310.json")
    discovered = discover_all_entities(data)

    sensor_ids = {s["unique_id"] for s in discovered["sensors"]}

    # L_ prefixed bare values become read-only sensors.
    assert "pe1_L_temp_act" in sensor_ids
    assert "pe1_L_statetext" in sensor_ids
    assert "system_L_errors" in sensor_ids

    # Statistic-like bare values (yesterday/today) are sensors, not numbers.
    number_ids = {n["unique_id"] for n in discovered["numbers"]}
    assert "pe1_storage_fill_yesterday" in sensor_ids
    assert "pe1_storage_fill_yesterday" not in number_ids

    # Nothing should be silently dropped: we discovered a meaningful set.
    assert len(sensor_ids) >= 10
