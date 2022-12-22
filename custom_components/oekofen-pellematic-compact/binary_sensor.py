"""Platform for sensor integration."""

import asyncio
from datetime import timedelta
from urllib.parse import urlparse

import aiohttp

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_PROBLEM,
    BinarySensorEntity,
)
from homeassistant.const import CONF_URL, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_UPDATE_INTERVAL, CONF_HEATER_URL, CONF_HEATER_NAME, LOGGER


SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    entities = []
    update_interval = discovery_info.get(CONF_UPDATE_INTERVAL)
    url = discovery_info.get(CONF_HEATER_URL)
    name = discovery_info.get(CONF_HEATER_NAME)
    websession = async_create_clientsession(
        hass,
        timeout=aiohttp.ClientTimeout(
            total=10, connect=None, sock_connect=None, sock_read=None
        ),
    )
    entities.append(PellematicCompact(websession, url, name, update_interval))
    LOGGER.debug(f"Added entity for url:{url}, name:{name}")
    add_entities(entities, True)


class PellematicCompact(BinarySensorEntity):
    """Representation of a Sensor."""

    def __init__(self, websession, url, name, update_interval):
        """Initialize the sensor."""
        self._is_down = None
        self._url = url
        self._websession = websession
        self._update_interval = update_interval
        self._update_interval_remaining = 0  # Make sure to update at startup
        self._last_status = "Not updated yet"
        self._last_error_status = "None"

        self._attr_device_class = DEVICE_CLASS_PROBLEM
        self._attr_name = name
        self._attr_unique_id = self._url

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._is_down

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._is_down is not None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return {
            "url": self._url,
            "last_status": self._last_status,
            "last_error_status": self._last_error_status,
        }

    async def async_update(self):
        """Do a request to the website"""
        self._update_interval_remaining -= 1
        if self._update_interval_remaining <= 0:
            self._update_interval_remaining = self._update_interval
            try:
                LOGGER.debug("Start checking: %s", self._url)
                async with self._websession.get(self._url) as resp:
                    LOGGER.debug(
                        "Done checking: %s, status = %s", self._url, resp.status
                    )
                    self._is_down = resp.status >= 500
                    self._last_status = f"{resp.status} - {resp.reason}"
            except aiohttp.ClientConnectionError:
                LOGGER.debug("ConnectionError for %s", self._url)
                self._is_down = True
                self._last_status = "Connection error"
                self._last_error_status = self._last_status
            except asyncio.TimeoutError:
                LOGGER.debug("Timeout for %s", self._url)
                self._is_down = True
                self._last_status = "Timeout"
                self._last_error_status = self._last_status
            except:
                LOGGER.exception("Unhandled exception for %s", self._url)
                self._is_down = True
                self._last_status = "Unhandled error"
                self._last_error_status = self._last_status