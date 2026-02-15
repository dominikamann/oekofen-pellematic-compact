"""Tests for API rate limiting behavior."""
import itertools
import pytest
from unittest.mock import AsyncMock, MagicMock

import custom_components.oekofen_pellematic_compact as pellematic


@pytest.mark.asyncio
async def test_fetch_rate_limited_on_back_to_back_calls(monkeypatch):
    """Ensure back-to-back fetches wait to honor the 2.5s minimum interval."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value={"system": {}})

    hub = pellematic.PellematicHub(
        hass=hass,
        name="Test",
        host="http://example.local",
        scan_interval=60,
        charset="utf-8",
        api_suffix="?",
    )
    hub._min_fetch_interval = 2.5

    monotonic_values = itertools.chain([100.0, 100.0, 101.0, 102.5], itertools.repeat(102.5))
    monkeypatch.setattr(pellematic.time, "monotonic", lambda: next(monotonic_values))

    sleep_mock = AsyncMock()
    monkeypatch.setattr(pellematic.asyncio, "sleep", sleep_mock)

    assert await hub.fetch_pellematic_data() is True
    assert await hub.fetch_pellematic_data() is True

    assert hass.async_add_executor_job.await_count == 2
    sleep_mock.assert_awaited_once()
    wait_time = sleep_mock.await_args.args[0]
    assert wait_time == pytest.approx(1.5, rel=1e-3)
