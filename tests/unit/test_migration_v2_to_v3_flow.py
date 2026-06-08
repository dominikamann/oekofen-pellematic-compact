"""End-to-end flow tests for the V2→V3 schedule + deferred-rename split.

These complement test_migration_v2_to_v3.py (which exercises the rename logic
in isolation) by verifying the two-phase architecture: async_migrate_entry
only schedules the work, async_setup_entry runs it after the hub has data.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.oekofen_pellematic_compact.migration import (
    PENDING_BINARY_SENSOR_DOMAIN_MIGRATION_KEY,
)


class _FakeConfigEntries:
    """Minimal stand-in for hass.config_entries with async_update_entry."""

    def __init__(self):
        self.updates: list[dict] = []

    def async_update_entry(self, entry, data=None, version=None):
        if data is not None:
            entry.data = data
        if version is not None:
            entry.version = version
        self.updates.append({"data": dict(entry.data), "version": entry.version})


@pytest.mark.asyncio
async def test_migrate_entry_v2_to_v3_does_not_touch_hub_data():
    """async_migrate_entry V2→V3 must not access hass.data[DOMAIN] — the hub
    isn't set up at migration time. It only bumps the version and sets a flag.
    """
    from custom_components.oekofen_pellematic_compact import async_migrate_entry

    entry = SimpleNamespace(
        version=2,
        data={"name": "Pellematic"},
        entry_id="abc",
    )
    hass = SimpleNamespace(
        data={},  # deliberately empty — async_migrate_entry runs before async_setup
        config_entries=_FakeConfigEntries(),
        async_add_executor_job=AsyncMock(),
    )

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == 3
    assert entry.data[PENDING_BINARY_SENSOR_DOMAIN_MIGRATION_KEY] is True


@pytest.mark.asyncio
async def test_migrate_entry_v2_to_v3_does_not_call_domain_migration():
    """The actual rename helper must NOT be invoked from async_migrate_entry —
    it requires hub.data, which isn't available yet.
    """
    from custom_components.oekofen_pellematic_compact import async_migrate_entry

    entry = SimpleNamespace(
        version=2,
        data={"name": "Pellematic"},
        entry_id="abc",
    )
    hass = SimpleNamespace(
        data={},
        config_entries=_FakeConfigEntries(),
        async_add_executor_job=AsyncMock(),
    )

    with patch(
        "custom_components.oekofen_pellematic_compact.migration.async_migrate_binary_sensor_domain"
    ) as mock_migrate:
        await async_migrate_entry(hass, entry)

    mock_migrate.assert_not_called()
