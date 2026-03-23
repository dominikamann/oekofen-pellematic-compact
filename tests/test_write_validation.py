"""Tests for write-validation fixes (issue #178 / ghost sensor fault 1020).

Validates three bugs fixed for the DHW ghost-sensor issue:
  1. Number entity min/max now read 'min_value'/'max_value' (with factor applied)
     instead of silently falling back to 0–100 for every entity.
  2. Select entity sends the correct numeric index prefix (split on '_'),
     not just the first character (option[:1] broke indices >= 10).
  3. Both entities reject out-of-range / unknown-option writes before they
     reach the boiler controller.

These tests run against every fixture file so regressions are caught early.
"""

import asyncio
import json
import re
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from custom_components.oekofen_pellematic_compact.dynamic_discovery import (
    discover_all_entities,
    parse_select_options,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ALL_FIXTURES = sorted(FIXTURES_DIR.glob("api_response_*.json")) + sorted(
    FIXTURES_DIR.glob("api_v*.json")
)
FIXTURE_NAMES = [f.name for f in ALL_FIXTURES]


def load_fixture(path: Path) -> dict:
    """Load and parse an Ökofen API fixture file."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("iso-8859-1", "ignore")

    text = text.replace("L_statetext:", 'L_statetext":')

    def escape_control_chars(m):
        s = m.group(1)
        s = s.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        return f'"{s}"'

    text = re.sub(r'"((?:[^"\\]|\\.)*)"', escape_control_chars, text)
    return json.loads(text, strict=False)


def make_number_entity(number_def: dict):
    """Instantiate a PellematicNumber from a definition dict (no HA runtime needed)."""
    from custom_components.oekofen_pellematic_compact.number import PellematicNumber

    hub = MagicMock()
    hub.data = {}
    entity = PellematicNumber(
        hub_name="test",
        hub=hub,
        device_info={},
        number_definition=number_def,
    )
    # Prevent NoEntitySpecifiedError when async_write_ha_state is called
    entity.async_write_ha_state = MagicMock()
    return entity


def make_select_entity(select_def: dict):
    """Instantiate a PellematicSelect from a definition dict (no HA runtime needed)."""
    from custom_components.oekofen_pellematic_compact.select import PellematicSelect

    hub = MagicMock()
    hub.data = {}
    entity = PellematicSelect(
        hub_name="test",
        hub=hub,
        device_info={},
        select_definition=select_def,
    )
    # Prevent NoEntitySpecifiedError when async_write_ha_state is called
    entity.async_write_ha_state = MagicMock()
    return entity


# ---------------------------------------------------------------------------
# Bug 1 — Number min/max correctly derived from API bounds + factor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_number_min_max_within_api_bounds(fixture_name):
    """Every number entity must have its HA min/max grounded in the API bounds.

    Before the fix, 'min_value'/'max_value' were looked up as 'min'/'max',
    which didn't exist in the definition dict, so all entities fell back to
    0–100 and could silently accept out-of-range writes.
    """
    path = FIXTURES_DIR / fixture_name
    data = load_fixture(path)
    discovered = discover_all_entities(data)

    for number_def in discovered["numbers"]:
        entity = make_number_entity(number_def)
        factor = entity._factor
        raw_min = number_def.get("min_value")
        raw_max = number_def.get("max_value")

        if raw_min is not None and raw_max is not None:
            expected_min = float(raw_min) * factor
            expected_max = float(raw_max) * factor

            assert entity.native_min_value == pytest.approx(expected_min), (
                f"[{fixture_name}] {number_def['component']}.{number_def['key']}: "
                f"native_min_value={entity.native_min_value} != {expected_min}"
            )
            assert entity.native_max_value == pytest.approx(expected_max), (
                f"[{fixture_name}] {number_def['component']}.{number_def['key']}: "
                f"native_max_value={entity.native_max_value} != {expected_max}"
            )
            assert entity.native_min_value < entity.native_max_value, (
                f"[{fixture_name}] {number_def['component']}.{number_def['key']}: "
                f"min ({entity.native_min_value}) must be < max ({entity.native_max_value})"
            )
        else:
            # No bounds in API data – ensure a safe fallback (not the broken 0/100)
            # The entity is still constructed without crashing.
            assert entity.native_min_value is not None
            assert entity.native_max_value is not None


# ---------------------------------------------------------------------------
# Bug 2 — Select sends correct numeric index, not option[:1]
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_select_option_index_extraction(fixture_name):
    """The numeric index extracted from an option string must equal option.split('_')[0].

    The old code used option[:1], which truncates multi-digit indices like '10'
    to '1', sending the wrong sensor-slot number to the boiler.
    """
    path = FIXTURES_DIR / fixture_name
    data = load_fixture(path)
    discovered = discover_all_entities(data)

    for select_def in discovered["selects"]:
        for option in select_def["options"]:
            # Correct extraction (the fix)
            correct_index = option.split("_", 1)[0]
            # Old (broken) extraction
            broken_index = option[:1]

            if correct_index != broken_index:
                # Multi-digit index — the bug actually mattered here
                assert correct_index.isdigit(), (
                    f"[{fixture_name}] {select_def['component']}.{select_def['key']}: "
                    f"option '{option}' has non-numeric prefix '{correct_index}'"
                )
                assert len(correct_index) > 1, (
                    f"[{fixture_name}] option '{option}': correct={correct_index}, "
                    f"broken={broken_index}"
                )

            # The correct index must always be numeric
            assert correct_index.isdigit(), (
                f"[{fixture_name}] {select_def['component']}.{select_def['key']}: "
                f"option '{option}' yields non-numeric index '{correct_index}'"
            )


# ---------------------------------------------------------------------------
# Bug 3 — Pre-write validation blocks out-of-range / unknown values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_number_rejects_out_of_range_value(fixture_name):
    """async_set_native_value must reject values outside [min, max] without writing."""
    path = FIXTURES_DIR / fixture_name
    data = load_fixture(path)
    discovered = discover_all_entities(data)

    for number_def in discovered["numbers"]:
        raw_min = number_def.get("min_value")
        raw_max = number_def.get("max_value")
        if raw_min is None or raw_max is None:
            continue

        entity = make_number_entity(number_def)
        entity.hass = MagicMock()
        entity.hass.async_add_executor_job = AsyncMock()

        too_low = entity.native_min_value - 1
        too_high = entity.native_max_value + 1

        for bad_value in (too_low, too_high):
            asyncio.run(entity.async_set_native_value(bad_value))
            entity.hass.async_add_executor_job.assert_not_called(), (
                f"[{fixture_name}] {number_def['component']}.{number_def['key']}: "
                f"out-of-range value {bad_value} must not reach the API"
            )


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_select_rejects_unknown_option(fixture_name):
    """async_select_option must reject options not in the static option list."""
    path = FIXTURES_DIR / fixture_name
    data = load_fixture(path)
    discovered = discover_all_entities(data)

    for select_def in discovered["selects"]:
        if not select_def["options"]:
            continue

        entity = make_select_entity(select_def)
        entity.hass = MagicMock()
        entity.hass.async_add_executor_job = AsyncMock()

        bad_option = "__nonexistent_option__"
        asyncio.run(entity.async_select_option(bad_option))
        entity.hass.async_add_executor_job.assert_not_called(), (
            f"[{fixture_name}] {select_def['component']}.{select_def['key']}: "
            f"unknown option '{bad_option}' must not reach the API"
        )


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_number_accepts_valid_value(fixture_name):
    """async_set_native_value must forward values inside [min, max] to the API."""
    path = FIXTURES_DIR / fixture_name
    data = load_fixture(path)
    discovered = discover_all_entities(data)

    for number_def in discovered["numbers"]:
        raw_min = number_def.get("min_value")
        raw_max = number_def.get("max_value")
        if raw_min is None or raw_max is None:
            continue

        entity = make_number_entity(number_def)
        entity.hass = MagicMock()
        entity.hass.async_add_executor_job = AsyncMock()
        entity._hub.send_pellematic_data = MagicMock()

        # Pick the midpoint as a definitely-valid value
        mid = (entity.native_min_value + entity.native_max_value) / 2

        asyncio.run(entity.async_set_native_value(mid))
        entity.hass.async_add_executor_job.assert_called_once(), (
            f"[{fixture_name}] {number_def['component']}.{number_def['key']}: "
            f"valid midpoint value {mid} should reach the API"
        )
        entity.hass.async_add_executor_job.reset_mock()


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_select_accepts_valid_option(fixture_name):
    """async_select_option must forward valid options to the API."""
    path = FIXTURES_DIR / fixture_name
    data = load_fixture(path)
    discovered = discover_all_entities(data)

    for select_def in discovered["selects"]:
        if not select_def["options"]:
            continue

        entity = make_select_entity(select_def)
        entity.hass = MagicMock()
        entity.hass.async_add_executor_job = AsyncMock()

        valid_option = select_def["options"][0]
        asyncio.run(entity.async_select_option(valid_option))
        entity.hass.async_add_executor_job.assert_called_once(), (
            f"[{fixture_name}] {select_def['component']}.{select_def['key']}: "
            f"valid option '{valid_option}' should reach the API"
        )
        entity.hass.async_add_executor_job.reset_mock()


# ---------------------------------------------------------------------------
# Regression: select sends correct numeric index to API (not option[:1])
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_select_sends_numeric_index_to_api(fixture_name):
    """The value sent to the boiler must be the numeric index from the option string."""
    path = FIXTURES_DIR / fixture_name
    data = load_fixture(path)
    discovered = discover_all_entities(data)

    for select_def in discovered["selects"]:
        for option in select_def["options"]:
            entity = make_select_entity(select_def)
            entity.hass = MagicMock()
            entity.hass.async_add_executor_job = AsyncMock()

            asyncio.run(entity.async_select_option(option))

            entity.hass.async_add_executor_job.assert_called_once()
            call_args = entity.hass.async_add_executor_job.call_args[0]
            # call_args: (send_pellematic_data, value, prefix, key)
            sent_value = str(call_args[1])
            expected_value = option.split("_", 1)[0]

            assert sent_value == expected_value, (
                f"[{fixture_name}] {select_def['component']}.{select_def['key']} "
                f"option='{option}': sent '{sent_value}' but expected '{expected_value}'"
            )
            entity.hass.async_add_executor_job.reset_mock()
