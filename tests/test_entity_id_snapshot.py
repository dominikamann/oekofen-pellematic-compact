"""Snapshot test for entity_id and unique_id stability."""
import json
from pathlib import Path

from tests.conftest import load_fixture
from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
)


HUB_NAME = "Pellematic"
SNAPSHOT_PATH = Path(__file__).parent / "entity_id_snapshot.json"


def _add_object(entities: list, domain: str, object_id: str) -> None:
    entities.append(
        {
            "entity_id": f"{domain}.{object_id}",
            "unique_id": f"{HUB_NAME.lower()}_{object_id}",
        }
    )


def _build_snapshot() -> dict:
    fixtures_dir = Path(__file__).parent / "fixtures"
    snapshot = {}

    for fixture_file in sorted(fixtures_dir.glob("api_response_*.json")):
        data = load_fixture(fixture_file.name)
        discovered = discover_all_entities(data)
        entities = []

        for entity in discovered["sensors"]:
            _add_object(entities, "sensor", f"{entity['component']}_{entity['key']}")
        for entity in discovered["binary_sensors"]:
            _add_object(entities, "binary_sensor", f"{entity['component']}_{entity['key']}")
        for entity in discovered["selects"]:
            _add_object(entities, "select", f"{entity['component']}_{entity['key']}")
        for entity in discovered["numbers"]:
            _add_object(entities, "number", f"{entity['component']}_{entity['key']}")

        hk_components = sorted(
            key for key in data.keys() if key.startswith("hk") and key[2:].isdigit()
        )
        for hk in hk_components:
            _add_object(entities, "climate", f"{hk}_climate")

        for i in range(1, 6):
            _add_object(entities, "sensor", f"error_error_{i}")

        entities = sorted(entities, key=lambda item: item["entity_id"])

        entity_ids = [item["entity_id"] for item in entities]
        unique_ids = [item["unique_id"] for item in entities]
        assert len(entity_ids) == len(set(entity_ids)), f"Duplicate entity_id in {fixture_file.name}"
        assert len(unique_ids) == len(set(unique_ids)), f"Duplicate unique_id in {fixture_file.name}"

        snapshot[fixture_file.name] = entities

    return snapshot


def test_entity_id_and_unique_id_snapshot():
    """Ensure entity_id and unique_id values stay stable across all fixtures."""
    assert SNAPSHOT_PATH.exists(), "Snapshot file missing: tests/entity_id_snapshot.json"

    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    current = _build_snapshot()

    assert current == expected, (
        "Entity ID snapshot mismatch. If changes are intentional, regenerate the snapshot."
    )
