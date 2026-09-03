"""Tests for localized component prefixes (see docs spec 2026-09-03)."""
from pathlib import Path

import pytest

from tests.conftest import load_fixture
from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    COMPONENT_NAMES,
    COMPONENT_NAMES_TRANSLATIONS,
    discover_all_entities,
    get_component_display_name,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
ALL_ENTITY_TYPES = ("sensors", "binary_sensors", "selects", "numbers")


# --- Unit: get_component_display_name --------------------------------------

def test_localized_prefix_de():
    assert get_component_display_name("hk1", 1, "de") == "Heizkreis 1"
    assert get_component_display_name("ww2", 2, "de") == "Warmwasser 2"


def test_localized_prefix_fr_uses_native_terms():
    # Taken verbatim from PR #190 (native French speaker).
    assert get_component_display_name("ww1", 1, "fr") == "ECS 1"
    assert get_component_display_name("sk1", 1, "fr") == "Solaire 1"


def test_missing_component_in_language_falls_back_to_english():
    # "pe" is a proper noun, intentionally absent from the overlays.
    assert get_component_display_name("pe1", 1, "de") == "Pellematic 1"
    assert get_component_display_name("pe1", 1, "fr") == "Pellematic 1"


def test_unknown_language_falls_back_to_english():
    assert get_component_display_name("hk1", 1, "es") == COMPONENT_NAMES["hk"] + " 1"


def test_unknown_component_uppercases_base():
    assert get_component_display_name("xyz1", 1, "de") == "XYZ 1"


def test_no_index_suffix_when_index_zero():
    assert get_component_display_name("weather", 0, "de") == "Wetter"


def test_default_language_is_english():
    assert get_component_display_name("hk1", 1) == "Heating Circuit 1"


# --- Fixture-based regression guard ----------------------------------------

@pytest.mark.parametrize("language", ["de", "fr"])
def test_known_component_names_localized_across_all_fixtures(language):
    """Over every real fixture, entity names for components that HAVE a
    translation in this language must start with the localized prefix (no
    English leakage) and must never be empty.
    """
    overlay = COMPONENT_NAMES_TRANSLATIONS[language]
    fixtures = sorted(FIXTURES_DIR.glob("api_response_*.json"))
    assert fixtures, "no fixtures found"

    for fixture_file in fixtures:
        data = load_fixture(fixture_file.name)
        discovered = discover_all_entities(data, language)

        for entity_type in ALL_ENTITY_TYPES:
            for entity in discovered[entity_type]:
                name = entity["name"]
                assert name, f"{fixture_file.name}: empty name for {entity}"

                base = "".join(c for c in entity["component"] if not c.isdigit())
                if base in overlay:
                    prefix = overlay[base]
                    assert name.startswith(prefix), (
                        f"{fixture_file.name} [{language}]: "
                        f"{entity['component']}.{entity['key']} name {name!r} "
                        f"does not start with localized prefix {prefix!r}"
                    )
