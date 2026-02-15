#!/usr/bin/env python3
"""Test rate limiting implementation."""

import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

# Mock Home Assistant
mock_hass = Mock()
mock_hass.async_add_executor_job = AsyncMock()

# Import after mocking
import sys
sys.path.insert(0, 'custom_components/oekofen_pellematic_compact')
from custom_components.oekofen_pellematic_compact import PellematicHub

async def test_rate_limiting():
    """Test that API calls are rate limited to 2.5s minimum."""
    
    # Create hub
    hub = PellematicHub(
        hass=mock_hass,
        name="Test",
        host="http://test",
        scan_interval=30,
        charset="utf-8",
        api_suffix="?"
    )
    
    # Mock successful API response
    mock_hass.async_add_executor_job.return_value = {"test": "data"}
    
    print("Testing rate limiting...")
    print("=" * 60)
    
    # First call - should execute immediately
    start = time.time()
    result1 = await hub.fetch_pellematic_data()
    time1 = time.time() - start
    print(f"Call 1: {time1:.3f}s - Success: {result1}")
    
    # Second call - should wait ~2.5s
    start = time.time()
    result2 = await hub.fetch_pellematic_data()
    time2 = time.time() - start
    print(f"Call 2: {time2:.3f}s - Success: {result2}")
    
    # Third call - should wait ~2.5s again
    start = time.time()
    result3 = await hub.fetch_pellematic_data()
    time3 = time.time() - start
    print(f"Call 3: {time3:.3f}s - Success: {result3}")
    
    print("=" * 60)
    
    # Verify timing
    assert time1 < 0.5, f"First call should be immediate, was {time1:.3f}s"
    assert 2.4 < time2 < 2.7, f"Second call should wait ~2.5s, was {time2:.3f}s"
    assert 2.4 < time3 < 2.7, f"Third call should wait ~2.5s, was {time3:.3f}s"
    
    print("✅ Rate limiting working correctly!")
    print(f"   - First call: immediate ({time1:.3f}s)")
    print(f"   - Subsequent calls: ~2.5s delay ({time2:.3f}s, {time3:.3f}s)")
    
    # Test parallel calls (should be serialized by lock)
    print("\nTesting parallel calls (should be serialized)...")
    start = time.time()
    results = await asyncio.gather(
        hub.fetch_pellematic_data(),
        hub.fetch_pellematic_data(),
        hub.fetch_pellematic_data()
    )
    total_time = time.time() - start
    print(f"3 parallel calls took: {total_time:.3f}s")
    print(f"Expected: ~7.5s (3 calls * 2.5s each)")
    
    assert 7.0 < total_time < 8.0, f"Parallel calls should take ~7.5s, was {total_time:.3f}s"
    print("✅ Parallel calls are properly serialized!")

if __name__ == "__main__":
    asyncio.run(test_rate_limiting())
