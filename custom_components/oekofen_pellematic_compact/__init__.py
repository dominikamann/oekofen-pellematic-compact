"""The Ökofen Pellematic Compact Integration."""
import asyncio
import logging
from datetime import timedelta
from typing import Optional
import json
import urllib

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
    CONF_NUM_OF_HEATING_CIRCUIT,
    CONF_NUM_OF_HOT_WATER,
    CONF_NUM_OF_PELLEMATIC_HEATER,
    CONF_NUM_OF_SMART_PV_SE,
    CONF_NUM_OF_SMART_PV_SK,
    CONF_NUM_OF_HEAT_PUMPS,
    CONF_NUM_OF_WIRELESS_SENSORS,
    CONF_NUM_OF_BUFFER_STORAGE,
    CONF_SOLAR_CIRCUIT,
    CONF_CIRCULATOR,
    CONF_SMART_PV,
    CONF_STIRLING,
    DEFAULT_NUM_OF_HEATING_CIRCUIT,
    DEFAULT_NUM_OF_HOT_WATER,
    DEFAULT_NUM_OF_PELLEMATIC_HEATER,
    DEFAULT_NUM_OF_SMART_PV_SE,
    DEFAULT_NUM_OF_SMART_PV_SK,
    DEFAULT_NUM_OF_HEAT_PUMPS,
    DEFAULT_NUM_OF_WIRELESS_SENSORS,
    DEFAULT_NUM_OF_BUFFER_STORAGE,
)

_LOGGER = logging.getLogger(__name__)

# Current config version
CONFIG_VERSION = 2

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

PLATFORMS = ["sensor","select","number","climate"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Ökofen Pellematic component."""
    hass.data[DOMAIN] = {}
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry to new version."""
    _LOGGER.debug("Migrating config entry from version %s", entry.version)

    if entry.version == 1:
        # Migrate from version 1 to version 2
        new_data = {**entry.data}
        
        # Add missing config values with defaults if not present
        new_data.setdefault(CONF_STIRLING, False)
        new_data.setdefault(CONF_SMART_PV, False)
        new_data.setdefault(CONF_CIRCULATOR, False)
        new_data.setdefault(CONF_NUM_OF_HOT_WATER, DEFAULT_NUM_OF_HOT_WATER)
        new_data.setdefault(CONF_NUM_OF_PELLEMATIC_HEATER, DEFAULT_NUM_OF_PELLEMATIC_HEATER)
        new_data.setdefault(CONF_NUM_OF_SMART_PV_SE, DEFAULT_NUM_OF_SMART_PV_SE)
        new_data.setdefault(CONF_NUM_OF_SMART_PV_SK, DEFAULT_NUM_OF_SMART_PV_SK)
        new_data.setdefault(CONF_NUM_OF_HEAT_PUMPS, DEFAULT_NUM_OF_HEAT_PUMPS)
        new_data.setdefault(CONF_NUM_OF_WIRELESS_SENSORS, DEFAULT_NUM_OF_WIRELESS_SENSORS)
        new_data.setdefault(CONF_NUM_OF_BUFFER_STORAGE, DEFAULT_NUM_OF_BUFFER_STORAGE)
        new_data.setdefault(CONF_SOLAR_CIRCUIT, False)
        
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        _LOGGER.info("Migration to version 2 successful")

    return True


def discover_components_from_api(data: dict) -> dict:
    """Auto-discover available components from API response.
    
    Args:
        data: The API response data
        
    Returns:
        Dictionary with discovered component counts
    """
    discovered = {}
    
    # Count heating circuits (hk1, hk2, ...)
    hk_count = len([k for k in data.keys() if k.startswith('hk') and k[2:].isdigit()])
    if hk_count > 0:
        discovered[CONF_NUM_OF_HEATING_CIRCUIT] = hk_count
        _LOGGER.debug("Discovered %d heating circuit(s)", hk_count)
    
    # Count hot water circuits (ww1, ww2, ...)
    ww_count = len([k for k in data.keys() if k.startswith('ww') and k[2:].isdigit()])
    if ww_count > 0:
        discovered[CONF_NUM_OF_HOT_WATER] = ww_count
        _LOGGER.debug("Discovered %d hot water circuit(s)", ww_count)
    
    # Count pellematic heaters (pe1, pe2, ...)
    pe_count = len([k for k in data.keys() if k.startswith('pe') and k[2:].isdigit()])
    if pe_count > 0:
        discovered[CONF_NUM_OF_PELLEMATIC_HEATER] = pe_count
        _LOGGER.debug("Discovered %d pellematic heater(s)", pe_count)
    
    # Count solar collectors SK (sk1, sk2, ...)
    sk_count = len([k for k in data.keys() if k.startswith('sk') and k[2:].isdigit()])
    if sk_count > 0:
        discovered[CONF_NUM_OF_SMART_PV_SK] = sk_count
        discovered[CONF_SOLAR_CIRCUIT] = True
        _LOGGER.debug("Discovered %d solar collector(s) SK", sk_count)
    
    # Count solar collectors SE (se1, se2, ...)
    se_count = len([k for k in data.keys() if k.startswith('se') and k[2:].isdigit()])
    if se_count > 0:
        discovered[CONF_NUM_OF_SMART_PV_SE] = se_count
        if not discovered.get(CONF_SOLAR_CIRCUIT):
            discovered[CONF_SOLAR_CIRCUIT] = True
        _LOGGER.debug("Discovered %d solar collector(s) SE", se_count)
    
    # Count heat pumps (wp1, wp2, ...)
    wp_count = len([k for k in data.keys() if k.startswith('wp') and k[2:].isdigit()])
    if wp_count > 0:
        discovered[CONF_NUM_OF_HEAT_PUMPS] = wp_count
        _LOGGER.debug("Discovered %d heat pump(s)", wp_count)
    
    # Count buffer storage (pu1, pu2, ...)
    pu_count = len([k for k in data.keys() if k.startswith('pu') and k[2:].isdigit()])
    if pu_count > 0:
        discovered[CONF_NUM_OF_BUFFER_STORAGE] = pu_count
        _LOGGER.debug("Discovered %d buffer storage(s)", pu_count)
    
    # Count wireless sensors (wireless1, wireless2, ...)
    wireless_count = len([k for k in data.keys() if k.startswith('wireless') and k[8:].isdigit()])
    if wireless_count > 0:
        discovered[CONF_NUM_OF_WIRELESS_SENSORS] = wireless_count
        _LOGGER.debug("Discovered %d wireless sensor(s)", wireless_count)
    
    # Detect special components
    if 'stirling' in data:
        discovered[CONF_STIRLING] = True
        _LOGGER.debug("Discovered Stirling engine")
    
    if 'circ1' in data:
        discovered[CONF_CIRCULATOR] = True
        _LOGGER.debug("Discovered circulator")
    
    if 'power' in data:
        discovered[CONF_SMART_PV] = True
        _LOGGER.debug("Discovered Smart PV")
    
    return discovered

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Ökofen Pellematic Component."""
    host = entry.data[CONF_HOST]
    name = entry.data[CONF_NAME]
    scan_interval = entry.data[CONF_SCAN_INTERVAL]
    charset = entry.data.get(CONF_CHARSET, DEFAULT_CHARSET)

    _LOGGER.debug("Setup Pellematic Hub %s, %s", DOMAIN, name)

    hub = PellematicHub(hass, name, host, scan_interval, charset)

    # Pre-fetch API data before setting up platforms
    # This ensures all platforms have data available immediately
    try:
        _LOGGER.debug("Pre-fetching API data for %s", name)
        await hub.fetch_pellematic_data()
        _LOGGER.info("Successfully pre-fetched API data for %s", name)
    except Exception as e:
        _LOGGER.error("Failed to pre-fetch API data for %s: %s", name, e)
        # Continue anyway - platforms will retry later

    # Register the hub.
    hass.data[DOMAIN][name] = {"hub": hub}

    # Register services
    await async_setup_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the integration."""
    
    async def handle_rediscover_components(call) -> None:
        """Handle the rediscover_components service call."""
        config_entry_id = call.data.get("config_entry_id")
        
        if config_entry_id:
            # Re-discover for specific entry
            entry = hass.config_entries.async_get_entry(config_entry_id)
            if entry and entry.domain == DOMAIN:
                await rediscover_and_update_entry(hass, entry)
        else:
            # Re-discover for all entries
            for entry in hass.config_entries.async_entries(DOMAIN):
                await rediscover_and_update_entry(hass, entry)
    
    # Register service only once
    if not hass.services.has_service(DOMAIN, "rediscover_components"):
        hass.services.async_register(
            DOMAIN,
            "rediscover_components",
            handle_rediscover_components,
        )


async def rediscover_and_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Re-discover components and update config entry."""
    try:
        hub_name = entry.data[CONF_NAME]
        hub = hass.data[DOMAIN][hub_name]["hub"]
        
        # Fetch latest data
        await hub.fetch_pellematic_data()
        
        # Discover components
        discovered = hub.get_discovered_components()
        
        if discovered:
            # Update config entry with discovered values
            new_data = {**entry.data}
            new_data.update(discovered)
            
            hass.config_entries.async_update_entry(entry, data=new_data)
            _LOGGER.info("Re-discovered components for %s: %s", hub_name, discovered)
            
            # Reload the entry to apply changes
            await hass.config_entries.async_reload(entry.entry_id)
        else:
            _LOGGER.warning("No components discovered for %s", hub_name)
    except Exception as e:
        _LOGGER.error("Failed to re-discover components: %s", e)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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
        name: str,
        host: str,
        scan_interval: int,
        charset: str = DEFAULT_CHARSET,
    ) -> None:
        """Initialize the hub."""
        self._hass = hass
        self._host = host
        self._charset = charset
        self._lock = asyncio.Lock()
        self._name = name
        self._scan_interval = timedelta(seconds=scan_interval)
        self._unsub_interval_method = None
        self._sensors = []
        self.data = {}

    @callback
    def async_add_pellematic_sensor(self, update_callback) -> None:
        """Listen for data updates."""
        # This is the first sensor, set up interval.
        if not self._sensors:
            self._unsub_interval_method = async_track_time_interval(
                self._hass, self.async_refresh_api_data, self._scan_interval
            )

        self._sensors.append(update_callback)

    @callback
    def async_remove_pellematic_sensor(self, update_callback) -> None:
        """Remove data update."""
        self._sensors.remove(update_callback)

        if not self._sensors:
            # stop the interval timer upon removal of last sensor.
            self._unsub_interval_method()
            self._unsub_interval_method = None
            
    def send_pellematic_data(self, val: any, prefix: str, key: str) -> None:
        """Send data update to API.
        
        Args:
            val: Value to set
            prefix: Component prefix (e.g., 'hk1')
            key: Parameter key
        """
        urlsent = f"{self._host[:-3]}{prefix}_{key}={val}"
        _LOGGER.debug("Sending API update: %s", urlsent)
        result = send_data(urlsent, self._charset)

    async def async_refresh_api_data(self, _now: Optional[int] = None) -> None:
        """Time to update."""
        if not self._sensors:
            return

        try:
            update_result = await self.fetch_pellematic_data()
        except Exception as e:
            _LOGGER.exception("Error reading pellematic data")
            update_result = False

        if update_result:
            for update_callback in self._sensors:
                update_callback()

    @property
    def name(self) -> str:
        """Return the name of this hub."""
        return self._name

    async def fetch_pellematic_data(self) -> bool:
        """Get data from api"""
        try:
            result = await self._hass.async_add_executor_job(
                fetch_data, self._host, self._charset
            )
            self.data = result
            return True
        except Exception as e:
            _LOGGER.error("Failed to fetch Pellematic data: %s", e)
            # Keep existing data if available
            return False
    
    async def async_get_data(self, force_refresh: bool = False) -> Optional[dict]:
        """Get current API data, fetch if not available or forced.
        
        Args:
            force_refresh: If True, always fetch new data even if cached data exists
            
        Returns:
            Current API data dictionary or None if fetch fails
        """
        if force_refresh or not self.data:
            success = await self.fetch_pellematic_data()
            if not success and not self.data:
                # No cached data and fetch failed
                _LOGGER.warning("No data available and fetch failed")
                return None
        return self.data
    
    def get_discovered_components(self) -> dict:
        """Get auto-discovered components from current API data."""
        return discover_components_from_api(self.data)


def fetch_data(url: str, charset: str = DEFAULT_CHARSET) -> dict:
    """Get data from API.
    
    Args:
        url: API endpoint URL
        charset: Character encoding for response
        
    Returns:
        Parsed JSON data from API
    """
    # Strip any leading/trailing whitespace
    url = url.strip()

    # Ensure URL ends with '?' for full API response
    if not url.endswith('?'):
        url += '?'
        
    req = urllib.request.Request(url)
    response = None
    str_response = None

    try:
        response = urllib.request.urlopen(
            req, timeout=3
        )  # Ökofen API recommended timeout is 2.5s
        str_response = response.read().decode(charset, "ignore")
    finally:
        if response is not None:
            response.close()

    # Hotfix for pellematic update 4.02 (invalid json)
    str_response = str_response.replace("L_statetext:", 'L_statetext":')
    result = json.loads(str_response, strict=False)
    return result


def send_data(url: str, charset: str = DEFAULT_CHARSET) -> str:
    """Send data to API.
    
    Args:
        url: API endpoint URL
        charset: Character encoding for response
        
    Returns:
        Response text from API
    """
    # Strip any leading/trailing whitespace
    url = url.strip()

    req = urllib.request.Request(url)
    response = None
    str_response = None
    try:
        response = urllib.request.urlopen(
            req, timeout=3
        )  # Ökofen API recommended timeout is 2.5s
        str_response = response.read().decode(charset, "ignore")
    finally:
        if response is not None:
            response.close()
    return str_response
