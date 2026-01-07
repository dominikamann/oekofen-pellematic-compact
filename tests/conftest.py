"""Pytest configuration and fixtures."""
import json
from pathlib import Path


def load_fixture(filename):
    """Load a fixture file."""
    path = Path(__file__).parent / "fixtures" / filename
    with open(path) as f:
        return json.load(f)
