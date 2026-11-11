"""The JSON interface help page must surface as its own error (issue #200).

When the URL or JSON password is wrong, the Touch answers with a plain-text
usage page instead of JSON. Setup used to show the generic cannot_connect.
"""
import json

import pytest

import custom_components.oekofen_pellematic_compact as hub
import custom_components.oekofen_pellematic_compact.config_flow as cf
from custom_components.oekofen_pellematic_compact.const import (
    ApiUsagePageError,
    is_api_usage_page,
)

# Real response from a Touch V4.04a (issue #200), shortened.
USAGE_PAGE = """Oekofen JSON Interface   V4.04a   http://www.oekofen.at

usage:
http://touch_ip:JSON_port/password/command

====================================================================================
read multiple values:
====================================================================================
http://192.168.0.10:4321/********/all?

Example: http://192.168.0.10:4321/********/hk1?


    all[?]     displays values of all available components
               optional parameter [?] adds meta data

only variables without a leading 'L_' can be set.
"""

DATA = json.dumps({"system": {"L_ambient": {"val": 98, "unit": "°C", "factor": 0.1}}})


class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def close(self):
        pass


def _serve(monkeypatch, module, body: str):
    monkeypatch.setattr(
        module.urllib.request, "urlopen",
        lambda req, timeout=None: _FakeResponse(body.encode("iso-8859-1")),
    )


def test_detects_usage_page():
    assert is_api_usage_page(USAGE_PAGE)
    assert is_api_usage_page("\r\n" + USAGE_PAGE)


def test_json_is_not_usage_page():
    assert not is_api_usage_page(DATA)
    # A JSON value mentioning "usage:" must not trip the check.
    assert not is_api_usage_page('{"pe1": {"L_statetext": "usage: none"}}')


def test_config_flow_raises_usage_page_error(monkeypatch):
    _serve(monkeypatch, cf, USAGE_PAGE)
    flow = cf.OekofenPellematicCompactConfigFlow()
    with pytest.raises(ApiUsagePageError):
        flow._fetch_api_data("http://192.168.0.10:4321/wrong/all", True, True, None)


def test_hub_fetch_raises_usage_page_error(monkeypatch):
    _serve(monkeypatch, hub, USAGE_PAGE)
    with pytest.raises(ApiUsagePageError):
        hub.fetch_data("http://192.168.0.10:4321/wrong/all")


def test_hub_fetch_still_parses_data(monkeypatch):
    _serve(monkeypatch, hub, DATA)
    assert hub.fetch_data("http://192.168.0.10:4321/pw/all")["system"]["L_ambient"]["val"] == 98


async def test_user_step_shows_usage_page_error(monkeypatch):
    _serve(monkeypatch, cf, USAGE_PAGE)
    flow = cf.OekofenPellematicCompactConfigFlow()

    class _Hass:
        async def async_add_executor_job(self, func, *args):
            return func(*args)

        class config_entries:
            @staticmethod
            def async_entries(domain):
                return []

    flow.hass = _Hass()
    result = await flow.async_step_user({
        "host": "http://192.168.0.10:4321/wrong/all",
        "name": "pellematic",
        "charset": "iso-8859-1",
        "old_firmware": False,
    })
    assert result["errors"] == {"base": "usage_page"}
