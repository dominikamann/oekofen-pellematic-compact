"""The select platform must map the API value to an option, not index into the
option list.

`_update_current_option()` used `self._attr_options[int(val)]`. Options are
built as "<api value>_<label>" (`parse_select_options`), and the API value is
*not* a list position:

* `hk1.autocomfort` reports -1 when the feature is unavailable. Python's
  negative indexing then returned the *last* option, so Home Assistant showed
  "3_abends" ("evenings") for a circuit that has no autocomfort at all.
  Ten occurrences across six real fixtures.
* Old firmware answers boolean fields with "false"/"true" (`ww1.heat_once`),
  where `int()` raised and the state went `unknown` although the value is known.

The write path already extracted the value prefix (`option.split("_", 1)[0]`),
so reading and writing were not even symmetric.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
)
from custom_components.oekofen_pellematic_compact.select import (
    PellematicSelect,
    _api_value_as_option_prefix,
)
from tests.conftest import load_fixture

FIXTURES = sorted(Path(__file__).parent.parent.joinpath("fixtures").glob("*.json"))

MODE_FORMAT = "0:Aus|1:Auto|2:Morgens|3:Abends"


class _StubHub:
    def __init__(self, data):
        self.data = data


def _select_for(raw, component="hk1", key="autocomfort"):
    api_data = {component: {"hk_info": "heating circuit data", key: raw}}
    definition = next(
        d for d in discover_all_entities(api_data)["selects"] if d["key"] == key
    )
    select = PellematicSelect(
        hub_name="Pellematic",
        hub=_StubHub(api_data),
        device_info={},
        select_definition=definition,
    )
    select._update_state()
    return select


@pytest.mark.parametrize(
    "val,expected",
    [
        (0, "0_aus"),
        (1, "1_auto"),
        (3, "3_abends"),
        # Numeric strings and floats from different firmware generations.
        ("2", "2_morgens"),
        (2.0, "2_morgens"),
        # Old-firmware booleans.
        ("false", "0_aus"),
        ("true", "1_auto"),
        (False, "0_aus"),
        # Unavailable / unknown values must not silently pick an option.
        (-1, None),
        (7, None),
        ("", None),
        ("Auto", None),
    ],
)
def test_api_value_maps_to_its_own_option(val, expected):
    select = _select_for({"val": val, "format": MODE_FORMAT, "text": "Autocomfort"})
    assert select.current_option == expected


def test_negative_value_no_longer_selects_the_last_option():
    """The exact regression: -1 used to return options[-1]."""
    select = _select_for({"val": -1, "format": MODE_FORMAT, "text": "Autocomfort"})
    assert select.current_option != "3_abends"
    assert select.current_option is None


def test_non_contiguous_format_keys_map_correctly():
    """Nothing guarantees the API numbers its options 0..n. With index access a
    gap shifted every option after it."""
    select = _select_for(
        {"val": 10, "format": "0:Aus|2:Ein|10:Puffer", "text": "Quelle"},
        key="sensor_on",
    )
    assert select.current_option == "10_puffer"


def test_bare_value_firmware_without_metadata_dict():
    """Firmware <= v3.10d sends the value instead of a dict. The old code read
    `raw_data["val"]` and fell into its bare `except`, so the state was lost.
    The option list still comes from the definition, so the mapping works."""
    api_data = {"hk1": {"autocomfort": 1}}
    definition = {
        "component": "hk1",
        "key": "autocomfort",
        "name": "Autocomfort",
        "options": ["0_aus", "1_auto"],
    }
    select = PellematicSelect(
        hub_name="Pellematic",
        hub=_StubHub(api_data),
        device_info={},
        select_definition=definition,
    )
    select._update_state()
    assert select.current_option == "1_auto"


def test_missing_key_stays_none():
    select = PellematicSelect(
        hub_name="Pellematic",
        hub=_StubHub({}),
        device_info={},
        select_definition={
            "component": "hk1",
            "key": "autocomfort",
            "name": "Autocomfort",
            "options": ["0_aus", "1_auto"],
        },
    )
    select._update_state()
    assert select.current_option is None


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_every_fixture_option_is_the_one_the_api_reports(fixture):
    """Across all real responses: whatever a select shows must be the option
    whose value prefix equals the reported API value — or nothing at all."""
    api_data = load_fixture(fixture.name)
    wrong = []
    for definition in discover_all_entities(api_data)["selects"]:
        select = PellematicSelect(
            hub_name="Pellematic",
            hub=_StubHub(api_data),
            device_info={},
            select_definition=definition,
        )
        select._update_state()
        option = select.current_option
        if option is None:
            continue
        raw = api_data[definition["component"]][definition["key"]]
        value = raw["val"] if isinstance(raw, dict) else raw
        prefix = option.split("_", 1)[0]
        # "false"/"true" and 1.0 are the same selection as "0"/"1" and "1".
        if prefix != _api_value_as_option_prefix(value):
            wrong.append(
                f"{definition['component']}.{definition['key']}: "
                f"val={value!r} shown as {option!r}"
            )
    assert not wrong, f"{fixture.name}: {wrong}"
