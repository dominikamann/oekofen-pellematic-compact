"""Tests for empirical API suffix/charset detection (_detect_api_config).

Regression coverage for issue #191: a US firmware 3.10 boiler returns valid
JSON *without* metadata on the single-'?' endpoint, and *drops the connection*
on the double-'??' endpoint. The suffix must therefore be decoupled from
metadata presence and chosen by what actually works, preferring '?'.
"""
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


def _install_urlopen(monkeypatch, *, single=None, double=None, single_exc=None, double_exc=None):
    """Patch urlopen to serve different payloads for '?' vs '??' URLs."""

    def _urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url.endswith("??"):
            if double_exc is not None:
                raise double_exc
            if double is None:
                raise http.client.IncompleteRead(b"")
            return _FakeResponse(double)
        else:  # ends with single '?'
            if single_exc is not None:
                raise single_exc
            if single is None:
                raise http.client.IncompleteRead(b"")
            return _FakeResponse(single)

    monkeypatch.setattr(pellematic.urllib.request, "urlopen", _urlopen)


HOST = "http://192.168.1.50:4321/passw/all"

_MODERN = json.dumps({"system": {"L_ambient": {"val": "98", "unit": "C", "factor": "0.1"}}}).encode()
_BARE = json.dumps({"system": {"L_ambient": "98", "L_errors": "0"}, "pe1": {"L_temp_act": "813"}}).encode()
_BARE_DOUBLE = json.dumps({"system": {"L_ambient": "98"}}).encode()


def test_modern_firmware_uses_single_question_mark(monkeypatch):
    _install_urlopen(monkeypatch, single=_MODERN, double=_MODERN)
    charset, suffix, old_firmware = pellematic._detect_api_config(HOST)
    assert suffix == "?"
    assert old_firmware is False


def test_euro_old_firmware_prefers_double_when_it_yields_metadata(monkeypatch):
    # Type A: '?' bare, '??' returns metadata -> richer, use '??'
    _install_urlopen(monkeypatch, single=_BARE, double=_MODERN)
    charset, suffix, old_firmware = pellematic._detect_api_config(HOST)
    assert suffix == "??"
    assert old_firmware is True


def test_us_310_bare_single_and_double_drops_connection(monkeypatch):
    # Type B (issue #191): '?' bare valid, '??' drops connection -> must use '?'
    _install_urlopen(
        monkeypatch,
        single=_BARE,
        double_exc=http.client.IncompleteRead(b"", 3112),
    )
    charset, suffix, old_firmware = pellematic._detect_api_config(HOST)
    assert suffix == "?", "US 3.10 must keep '?' because '??' drops the connection"
    assert old_firmware is True  # bare data format


def test_falls_back_to_double_when_single_fails(monkeypatch):
    _install_urlopen(
        monkeypatch,
        single_exc=http.client.IncompleteRead(b"", 100),
        double=_BARE_DOUBLE,
    )
    charset, suffix, old_firmware = pellematic._detect_api_config(HOST)
    assert suffix == "??"
    assert old_firmware is True


def test_us_310_bare_single_when_double_also_bare(monkeypatch):
    # '??' works but yields no richer metadata -> prefer '?'
    _install_urlopen(monkeypatch, single=_BARE, double=_BARE_DOUBLE)
    charset, suffix, old_firmware = pellematic._detect_api_config(HOST)
    assert suffix == "?"
    assert old_firmware is True
