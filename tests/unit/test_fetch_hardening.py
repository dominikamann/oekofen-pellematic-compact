"""Hardening for slow/old firmware (issue #191): longer read timeout,
safer rate-limit margin, and one retry on a dropped connection."""
import http.client
import json

import pytest

import custom_components.oekofen_pellematic_compact as pellematic


class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def close(self):
        pass


VALID = json.dumps({"system": {"L_ambient": "98"}}).encode()
URL = "http://192.168.1.50:4321/passw/all"


def test_fetch_data_uses_generous_timeout(monkeypatch):
    """The read timeout must be >= 10s; 3s is too short for US 3.10 boilers."""
    captured = {}

    def _urlopen(req, timeout=None):
        captured["timeout"] = timeout
        return _FakeResponse(VALID)

    monkeypatch.setattr(pellematic.urllib.request, "urlopen", _urlopen)
    pellematic.fetch_data(URL, "utf-8", "?")
    assert captured["timeout"] >= 10


def test_default_min_fetch_interval_has_margin():
    """Rate-limit interval must sit above the boiler's 2.5s minimum."""
    hub = pellematic.PellematicHub(
        hass=None, name="t", host=URL, scan_interval=60, charset="utf-8", api_suffix="?"
    )
    assert hub._min_fetch_interval >= 3.0


def test_fetch_data_retries_once_on_incomplete_read(monkeypatch):
    """A single dropped connection should be retried, not fatal."""
    calls = {"n": 0}

    def _urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise http.client.IncompleteRead(b"", 3112)
        return _FakeResponse(VALID)

    monkeypatch.setattr(pellematic.urllib.request, "urlopen", _urlopen)
    monkeypatch.setattr(pellematic.time, "sleep", lambda *_: None)

    result = pellematic.fetch_data(URL, "utf-8", "?")
    assert calls["n"] == 2
    assert result == {"system": {"L_ambient": "98"}}


def test_fetch_data_raises_after_retries_exhausted(monkeypatch):
    def _urlopen(req, timeout=None):
        raise http.client.IncompleteRead(b"", 3112)

    monkeypatch.setattr(pellematic.urllib.request, "urlopen", _urlopen)
    monkeypatch.setattr(pellematic.time, "sleep", lambda *_: None)

    with pytest.raises(http.client.IncompleteRead):
        pellematic.fetch_data(URL, "utf-8", "?")
