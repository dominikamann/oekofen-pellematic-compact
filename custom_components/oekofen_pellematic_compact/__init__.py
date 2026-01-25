"""The Ökofen Pellematic Compact Integration."""
import asyncio
import logging
import threading
import time
import socket
from datetime import timedelta
from typing import Optional
import json

import urllib.request
import urllib.error

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
from .const import (
    CONF_CHARSET,
    DEFAULT_CHARSET,
    DEFAULT_HOST,
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)
_CHARSET = DEFAULT_CHARSET

PELLEMATIC_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
        vol.Optional(CONF_CHARSET, default=DEFAULT_CHARSET): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): cv.positive_int,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({cv.slug: PELLEMATIC_SCHEMA})}, extra=vol.ALLOW_EXTRA
)

PLATFORMS = ["sensor", "select", "number", "climate"]


async def async_setup(hass: HomeAssistant, config):
    """Set up the Ökofen Pellematic component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up a Ökofen Pellematic Component."""
    host = entry.data[CONF_HOST]
    name = entry.data[CONF_NAME]
    scan_interval = entry.data[CONF_SCAN_INTERVAL]

    global _CHARSET
    _CHARSET = entry.data.get(CONF_CHARSET, DEFAULT_CHARSET)

    _LOGGER.debug("Setup Pellematic Hub %s, %s", DOMAIN, name)

    hub = PellematicHub(hass, name, host, scan_interval)

    # Register the hub.
    hass.data[DOMAIN][name] = {"hub": hub}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload Pellematic entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.data["name"])
    return True


class PellematicHub:
    """Thread safe wrapper class."""

    def __init__(
        self,
        hass: HomeAssistant,
        name,
        host,
        scan_interval,
    ) -> None:
        """Initialize the hub."""
        self._hass = hass
        self._host = host
        self._lock = threading.Lock()
        self._name = name
        self._scan_interval = timedelta(seconds=scan_interval)
        self._unsub_interval_method = None
        self._sensors = []
        self.data = {}

    @callback
    def async_add_pellematic_sensor(self, update_callback):
        """Listen for data updates."""
        # This is the first sensor, set up interval.
        if not self._sensors:
            self._unsub_interval_method = async_track_time_interval(
                self._hass, self.async_refresh_api_data, self._scan_interval
            )

        self._sensors.append(update_callback)

    @callback
    def async_remove_pellematic_sensor(self, update_callback):
        """Remove data update."""
        self._sensors.remove(update_callback)

        if not self._sensors:
            # stop the interval timer upon removal of last sensor.
            self._unsub_interval_method()
            self._unsub_interval_method = None

    def send_pellematic_data(self, val, prefix, key) -> None:
        """Call data update."""
        urlsent = f"{self._host[:-3]}{prefix}_{key}={val}"
        _LOGGER.debug("URL maj : %s", urlsent)
        _ = send_data(urlsent)

    async def async_refresh_api_data(self, _now: Optional[int] = None) -> None:
        """Time to update."""
        if not self._sensors:
            return

        try:
            update_result = await self.fetch_pellematic_data()
        except Exception:
            _LOGGER.exception("Error reading pellematic data")
            update_result = False

        if update_result:
            for update_callback in self._sensors:
                update_callback()

    @property
    def name(self):
        """Return the name of this hub."""
        return self._name

    async def fetch_pellematic_data(self):
        """Get data from api"""
        result = await self._hass.async_add_executor_job(fetch_data, self._host)
        self.data = result
        return True


def fetch_data(url: str):
    """Get data"""
    url = url.strip()

    # Sicherstellen, dass die URL mit einem Fragezeichen endet
    if not url.endswith("?"):
        url += "?"

    req = urllib.request.Request(url)

    # Ökofen kann manchmal langsam sein → Retry + längere Timeouts
    timeouts = [6, 12]  # Sekunden (2 Versuche)
    last_exc = None

    for t in timeouts:
        response = None
        try:
            response = urllib.request.urlopen(req, timeout=t)
            str_response = response.read().decode(_CHARSET, "ignore")

            # Hotfix for pellematic update 4.02 (invalid json)
            str_response = str_response.replace("L_statetext:", 'L_statetext":')

            result = json.loads(str_response, strict=False)
            return result

        except (TimeoutError, socket.timeout, urllib.error.URLError) as e:
            last_exc = e
            _LOGGER.warning("Pellematic fetch timeout/error (timeout=%ss): %s", t, e)
            time.sleep(0.25)

        finally:
            if response is not None:
                response.close()

    raise last_exc


def send_data(url: str):
    """Put data"""
    url = url.strip()
    req = urllib.request.Request(url)

    timeouts = [6, 12]
    last_exc = None

    for t in timeouts:
        response = None
        try:
            response = urllib.request.urlopen(req, timeout=t)
            str_response = response.read().decode(_CHARSET, "ignore")
            return str_response

        except (TimeoutError, socket.timeout, urllib.error.URLError) as e:
            last_exc = e
            _LOGGER.warning("Pellematic send timeout/error (timeout=%ss): %s", t, e)
            time.sleep(0.25)

        finally:
            if response is not None:
                response.close()

    raise last_exc
