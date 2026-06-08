"""Tests for the binary_sensor.py platform split (issue #186).

Verifies that binary sensors are no longer created by sensor.py and that
the new binary_sensor.py exists and is wired into PLATFORMS.
"""

from pathlib import Path

from custom_components.oekofen_pellematic_compact import PLATFORMS


COMPONENT_DIR = Path(__file__).parents[2] / "custom_components" / "oekofen_pellematic_compact"


def test_binary_sensor_in_platforms():
    assert "binary_sensor" in PLATFORMS
    assert "sensor" in PLATFORMS


def test_binary_sensor_module_exists():
    assert (COMPONENT_DIR / "binary_sensor.py").is_file()


def test_sensor_module_no_longer_creates_binary_sensors():
    """sensor.py must not append PellematicBinarySensor instances anymore."""
    body = (COMPONENT_DIR / "sensor.py").read_text(encoding="utf-8")
    # The class lives in sensor.py (imported by binary_sensor.py), so the name
    # itself still appears. But the entity loop in create_sensor_entities must
    # not instantiate it.
    assert "for sensor_def in discovered['binary_sensors']" not in body
    assert "for sensor_def in discovered[\"binary_sensors\"]" not in body
