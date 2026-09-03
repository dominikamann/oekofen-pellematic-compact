"""Config-flow auto-detect must decouple suffix from metadata (issue #191).

The US firmware 3.10 case: '?' returns valid bare JSON, '??' drops the
connection. Auto-detection must keep '?' instead of forcing '??'.
"""
import http.client
import json

import pytest

import custom_components.oekofen_pellematic_compact.config_flow as cf


class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def close(self):
        pass


def _install_urlopen(monkeypatch, *, single=None, double=None, single_exc=None, double_exc=None):
    def _urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url.endswith("??"):
            if double_exc is not None:
                raise double_exc
            if double is None:
                raise http.client.IncompleteRead(b"")
            return _FakeResponse(double)
        if single_exc is not None:
            raise single_exc
        if single is None:
            raise http.client.IncompleteRead(b"")
        return _FakeResponse(single)

    monkeypatch.setattr(cf.urllib.request, "urlopen", _urlopen)


HOST = "http://192.168.1.50:4321/passw/all"
_MODERN = json.dumps({"system": {"L_ambient": {"val": "98", "unit": "C", "factor": "0.1"}}}).encode()
_BARE = json.dumps({"system": {"L_ambient": "98"}, "pe1": {"L_temp_act": "813"}}).encode()


def _autodetect(flow):
    # detect_charset=True, detect_api_suffix=True, user_old_firmware=None (auto)
    return flow._fetch_api_data(HOST, True, True, None)


def test_flow_modern_uses_single(monkeypatch):
    _install_urlopen(monkeypatch, single=_MODERN)
    flow = cf.OekofenPellematicCompactConfigFlow()
    data, charset, suffix, old_fw = _autodetect(flow)
    assert suffix == "?"
    assert old_fw is False


def test_flow_us310_keeps_single_when_double_drops(monkeypatch):
    _install_urlopen(
        monkeypatch,
        single=_BARE,
        double_exc=http.client.IncompleteRead(b"", 3112),
    )
    flow = cf.OekofenPellematicCompactConfigFlow()
    data, charset, suffix, old_fw = _autodetect(flow)
    assert suffix == "?", "US 3.10 auto-detect must keep '?' - '??' drops the connection"
    assert old_fw is True


def test_flow_euro_old_prefers_double_metadata(monkeypatch):
    _install_urlopen(monkeypatch, single=_BARE, double=_MODERN)
    flow = cf.OekofenPellematicCompactConfigFlow()
    data, charset, suffix, old_fw = _autodetect(flow)
    assert suffix == "??"
    assert old_fw is True
