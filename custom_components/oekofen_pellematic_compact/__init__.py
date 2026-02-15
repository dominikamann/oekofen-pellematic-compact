"""The Ökofen Pellematic Compact Integration."""
import asyncio
import logging
import re
from datetime import timedelta
from typing import Optional, Callable, Any, Dict, Set
from collections.abc import Awaitable
import json
import urllib

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
from .migration import async_migrate_entity_ids, async_check_and_warn_entity_changes
from .const import (
    CONF_CHARSET,
    DEFAULT_CHARSET,
    CONF_API_SUFFIX,
    DEFAULT_API_SUFFIX,
    CONF_OLD_FIRMWARE,
    DEFAULT_OLD_FIRMWARE,
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


def _api_response_has_metadata(data: dict) -> bool:
    """Check if API response contains metadata (val, unit, factor).
    
    Args:
        data: Parsed JSON data from API
        
    Returns:
        True if response contains metadata, False if simple values only
    """
    for section_key, section_value in data.items():
        if isinstance(section_value, dict):
            for field_key, field_value in section_value.items():
                if isinstance(field_value, dict):
                    if any(key in field_value for key in ['val', 'unit', 'factor', 'format']):
                        return True
    return False


def _detect_api_config(host: str) -> tuple[str, str, bool]:
    """Detect charset and API suffix from API response (blocking function for executor).
    
    Detection logic:
    - Try '?' first and check if response contains metadata (val, unit, factor)
    - If HAS metadata → Modern firmware (v3.52+): use '?', old_firmware=False
    - If NO metadata → Old firmware (v3.10d-): use '??', old_firmware=True
    
    Args:
        host: The API host URL (without ? or ??)
        
    Returns:
        Tuple of (charset, api_suffix, old_firmware)
        
    Raises:
        Exception: If API is unreachable or invalid
    """
    if not host or host == DEFAULT_HOST:
        raise ValueError(f"Invalid host: {host}")
    
    # Remove any existing suffix
    clean_host = host.strip().rstrip('?')
    charset = DEFAULT_CHARSET  # Default fallback
    
    # Try with single ? first (modern firmware)
    url_single = clean_host + '?'
    req = urllib.request.Request(url_single)
    response = None
    
    _LOGGER.debug("Checking API with '?' to detect firmware type...")
    try:
        response = urllib.request.urlopen(req, timeout=10)  # Increased timeout to 10s for slow APIs
        raw_data = response.read()
        
        if not raw_data:
            raise ValueError("Empty API response")
        
        # Detect charset with mixed encoding support
        try:
            decoded_utf8 = raw_data.decode('utf-8')
            if any(ord(char) > 127 for char in decoded_utf8):
                charset = 'utf-8'
            else:
                charset = 'utf-8'
        except UnicodeDecodeError:
            # Try UTF-8 with replace to detect mixed encoding
            decoded_utf8_replace = raw_data.decode('utf-8', errors='replace')
            replacement_count = decoded_utf8_replace.count('�')
            non_ascii_count = sum(1 for char in decoded_utf8_replace if ord(char) > 127)
            
            # If less than 20% of non-ASCII chars are problematic, prefer UTF-8
            # This handles mixed encoding where most content is UTF-8 but some fields have ISO-8859-1 bytes
            # Increased threshold from 10% to 20% to handle smaller responses
            if non_ascii_count > 0 and replacement_count / non_ascii_count < 0.2:
                charset = 'utf-8'
            else:
                charset = 'iso-8859-1'
        
        # Decode and parse
        str_response = raw_data.decode(charset, 'ignore')
        str_response = str_response.replace("L_statetext:", 'L_statetext":')
        data = json.loads(str_response, strict=False)
        
        # Check if metadata exists
        if _api_response_has_metadata(data):
            # Modern firmware - has metadata with single ?
            _LOGGER.info("API response has metadata with '?' - modern firmware detected")
            return charset, '?', False  # old_firmware=False
        else:
            # Old firmware - no metadata with ?
            _LOGGER.info("API response has no metadata with '?' - old firmware detected")
            return charset, '??', True  # old_firmware=True
    except Exception as e:
        # If ? fails completely, raise error
        _LOGGER.error("Failed to fetch with '?': %s", e)
        raise
    finally:
        if response is not None:
            response.close()
    
    # No second request here: the '?' response is enough to determine firmware type.


def _detect_api_charset(host: str) -> str:
    """Detect charset from API response (blocking function for executor).
    
    Args:
        host: The API host URL
        
    Returns:
        Detected charset ('utf-8' or 'iso-8859-1')
        
    Raises:
        Exception: If API is unreachable or invalid
    """
    if not host or host == DEFAULT_HOST:
        # Don't try to connect to placeholder/invalid hosts
        raise ValueError(f"Invalid host: {host}")
    
    url = host.strip()
    if not url.endswith('?'):
        url += '?'
    
    req = urllib.request.Request(url)
    response = None
    
    try:
        response = urllib.request.urlopen(req, timeout=5)
        raw_data = response.read()
        
        if not raw_data:
            raise ValueError("Empty API response")
        
        # Try UTF-8 first with strict decoding and mixed encoding support
        try:
            decoded_utf8 = raw_data.decode('utf-8')
            # Check if it contains any non-ASCII characters
            if any(ord(char) > 127 for char in decoded_utf8):
                return 'utf-8'
            # Only ASCII characters - default to UTF-8 (modern standard)
            return 'utf-8'
        except UnicodeDecodeError:
            # Try UTF-8 with replace to detect mixed encoding
            decoded_utf8_replace = raw_data.decode('utf-8', errors='replace')
            replacement_count = decoded_utf8_replace.count('�')
            non_ascii_count = sum(1 for char in decoded_utf8_replace if ord(char) > 127)
            
            # If less than 20% of non-ASCII chars are problematic, prefer UTF-8
            # This handles mixed encoding where most content is UTF-8 but some fields have ISO-8859-1 bytes
            # Increased threshold from 10% to 20% to handle smaller responses
            if non_ascii_count > 0 and replacement_count / non_ascii_count < 0.2:
                return 'utf-8'
            else:
                return 'iso-8859-1'
    finally:
        if response is not None:
            response.close()


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
        
        # Auto-detect charset and API suffix if not present
        if CONF_CHARSET not in new_data or CONF_API_SUFFIX not in new_data or CONF_OLD_FIRMWARE not in new_data:
            try:
                host = new_data.get(CONF_HOST, DEFAULT_HOST).rstrip('?')
                detected_charset, detected_suffix, detected_old_firmware = await hass.async_add_executor_job(
                    _detect_api_config, host
                )
                new_data[CONF_CHARSET] = detected_charset
                new_data[CONF_API_SUFFIX] = detected_suffix
                new_data[CONF_OLD_FIRMWARE] = detected_old_firmware
                _LOGGER.info(
                    "Migration V1→V2: Auto-detected charset '%s', API suffix '%s', old_firmware=%s for %s",
                    detected_charset, detected_suffix, detected_old_firmware, host
                )
            except Exception as e:
                _LOGGER.warning(
                    "Migration V1→V2: Failed to auto-detect config, using defaults: %s",
                    e
                )
                new_data[CONF_CHARSET] = DEFAULT_CHARSET
                new_data[CONF_API_SUFFIX] = DEFAULT_API_SUFFIX
                new_data[CONF_OLD_FIRMWARE] = DEFAULT_OLD_FIRMWARE
        
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        _LOGGER.info("Migration to version 2 successful")

    return True


# Constants for retry setup
RETRY_INTERVAL_SECONDS = 60
RETRY_WARNING_MESSAGE = (
    "Initial {platform} setup incomplete. Will retry every {interval} seconds until successful. "
    "You can also manually trigger rediscovery using the 'oekofen_pellematic_compact.rediscover_components' service."
)


async def setup_platform_with_retry(
    hass: HomeAssistant,
    hub: 'PellematicHub',
    hub_name: str,
    device_info: Dict[str, Any],
    platform_name: str,
    entity_factory: Callable[[Dict[str, Any]], Any],
    async_add_entities: Callable[[list], None],
) -> None:
    """Common setup logic for all platforms with retry mechanism.
    
    Args:
        hass: Home Assistant instance
        hub: PellematicHub instance
        hub_name: Name of the hub
        device_info: Device information dictionary
        platform_name: Platform name for logging (e.g., "sensor", "number")
        entity_factory: Function that creates entities from discovery data
        async_add_entities: Callback to add entities to Home Assistant
    """
    # Track which entities have been added to avoid duplicates
    added_entity_ids: Set[str] = set()
    
    async def setup_entities_from_data() -> bool:
        """Discover and add entities from current API data."""
        entities = []
        
        # Get API data
        data = await hub.async_get_data()
        
        if not data:
            _LOGGER.debug("No API data available yet for %s discovery", platform_name)
            return False
        
        try:
            # Create entities using the provided factory function
            new_entities = entity_factory(data)
            
            # Track and add only new entities
            for entity in new_entities:
                entity_id = getattr(entity, '_entity_id_key', None)
                if entity_id and entity_id in added_entity_ids:
                    continue
                
                entities.append(entity)
                if entity_id:
                    added_entity_ids.add(entity_id)
            
            if entities:
                _LOGGER.debug("Adding %i new %s entities", len(entities), platform_name)
                async_add_entities(entities)
                return True
            else:
                _LOGGER.debug("No new %s entities to add", platform_name)
                return len(added_entity_ids) > 0  # Success if we added entities before
                
        except Exception as e:
            _LOGGER.error("Error during %s discovery: %s", platform_name, e)
            return False
    
    # Try initial setup
    success = await setup_entities_from_data()
    
    if not success and len(added_entity_ids) == 0:
        _LOGGER.warning(
            RETRY_WARNING_MESSAGE.format(
                platform=platform_name,
                interval=RETRY_INTERVAL_SECONDS
            )
        )
        
        # Set up retry mechanism
        async def retry_setup(now: Any) -> None:
            """Retry entity setup periodically."""
            success = await setup_entities_from_data()
            if success:
                _LOGGER.info("%s entity setup completed successfully after retry", platform_name.capitalize())
                # Cancel further retries
                if hasattr(retry_setup, 'cancel'):
                    retry_setup.cancel()
        
        # Track the interval so we can cancel it later
        retry_setup.cancel = async_track_time_interval(
            hass, retry_setup, timedelta(seconds=RETRY_INTERVAL_SECONDS)
        )


def discover_components_from_api(data: Dict[str, Any]) -> Dict[str, Any]:
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
    host = entry.data[CONF_HOST].rstrip('?')  # Remove any existing suffix
    name = entry.data[CONF_NAME]
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    
    # CRITICAL: Auto-detect and save charset/api_suffix/old_firmware if missing
    # This is a fallback for installations that were migrated before auto-detection was added
    if CONF_CHARSET not in entry.data or CONF_API_SUFFIX not in entry.data or CONF_OLD_FIRMWARE not in entry.data:
        _LOGGER.warning(
            "Setup %s: CONF_CHARSET, CONF_API_SUFFIX, or CONF_OLD_FIRMWARE missing! Attempting auto-detection...",
            name
        )
        try:
            detected_charset, detected_suffix, detected_old_firmware = await hass.async_add_executor_job(
                _detect_api_config, host
            )
            # Update the config entry with detected values
            new_data = {
                **entry.data,
                CONF_CHARSET: detected_charset,
                CONF_API_SUFFIX: detected_suffix,
                CONF_OLD_FIRMWARE: detected_old_firmware
            }
            hass.config_entries.async_update_entry(entry, data=new_data)
            charset = detected_charset
            api_suffix = detected_suffix
            _LOGGER.info(
                "Setup %s: Auto-detected and saved charset '%s', API suffix '%s', old_firmware=%s",
                name, detected_charset, detected_suffix, detected_old_firmware
            )
        except Exception as e:
            _LOGGER.error(
                "Setup %s: Failed to auto-detect config, using defaults: %s",
                name, e
            )
            charset = DEFAULT_CHARSET
            api_suffix = DEFAULT_API_SUFFIX
    else:
        charset = entry.data[CONF_CHARSET]
        api_suffix = entry.data[CONF_API_SUFFIX]

    _LOGGER.debug("Setup Pellematic Hub %s, %s (charset: %s, API suffix: %s)", 
                  DOMAIN, name, charset, api_suffix)
    _LOGGER.info("Setting up Ökofen Pellematic integration '%s' at %s", name, host)

    hub = PellematicHub(hass, name, host, scan_interval, charset, api_suffix)

    # Pre-fetch API data before setting up platforms
    # This ensures all platforms have data available immediately
    try:
        _LOGGER.debug("Pre-fetching API data for %s", name)
        await hub.fetch_pellematic_data()
        _LOGGER.info("Successfully pre-fetched API data for '%s' - %d top-level keys found", 
                    name, len(hub.data) if hub.data else 0)
    except Exception as e:
        _LOGGER.error("Failed to pre-fetch API data for %s: %s", name, e)
        # Continue anyway - platforms will retry later

    # Register the hub.
    hass.data[DOMAIN][name] = {"hub": hub}

    # Run one-time entity ID migration for existing users
    try:
        migrated = await async_migrate_entity_ids(hass, entry.entry_id, name)
        if migrated > 0:
            _LOGGER.info("Migrated %d entity IDs for backwards compatibility", migrated)
    except Exception as e:
        _LOGGER.warning("Entity ID migration failed (non-critical): %s", e)

    # Check and warn about potential entity ID issues
    try:
        warnings = await async_check_and_warn_entity_changes(hass, entry.entry_id, name)
        for warning in warnings:
            _LOGGER.warning(warning)
    except Exception as e:
        _LOGGER.debug("Entity ID check failed (non-critical): %s", e)

    # Register services
    await async_setup_services(hass)

    _LOGGER.info("Ökofen Pellematic '%s': Starting platform setup (sensor, select, number, climate)", name)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Ökofen Pellematic '%s': Setup complete - entities should be available within 1 minute", name)
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
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    _LOGGER.info("Unloading Ökofen Pellematic integration '%s' - entities will become unavailable", name)
    
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if not unload_ok:
        _LOGGER.error("Failed to unload some platforms for '%s'", name)
        return False

    hass.data[DOMAIN].pop(entry.data["name"])
    _LOGGER.info("Successfully unloaded Ökofen Pellematic integration '%s'", name)
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
        api_suffix: str = DEFAULT_API_SUFFIX,
    ) -> None:
        """Initialize the hub."""
        self._hass = hass
        self._host = host
        self._charset = charset
        self._api_suffix = api_suffix
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
            
    def send_pellematic_data(self, val: Any, prefix: str, key: str) -> None:
        """Send data update to API.
        
        Args:
            val: Value to set
            prefix: Component prefix (e.g., 'hk1')
            key: Parameter key
        """
        # Remove '/all' or '/all?' from the end of the host URL
        base_url = self._host.replace('/all?', '/').replace('/all', '/')
        urlsent = f"{base_url}{prefix}_{key}={val}"
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
                fetch_data, self._host, self._charset, self._api_suffix
            )
            self.data = result
            return True
        except Exception as e:
            _LOGGER.error("Failed to fetch Pellematic data: %s", e)
# Keep existing data if available
            return False
    
    async def async_get_data(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
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


def fetch_data(url: str, charset: str = DEFAULT_CHARSET, api_suffix: str = DEFAULT_API_SUFFIX) -> Dict[str, Any]:
    """Get data from API.
    
    Args:
        url: API endpoint URL (without ? or ??)
        charset: Character encoding for response
        api_suffix: API suffix to use ("?" for modern firmware, "??" for old firmware)
        
    Returns:
        Parsed JSON data from API
    """
    # Strip any leading/trailing whitespace and existing suffix
    url = url.strip().rstrip('?')

    # Append the API suffix
    url += api_suffix
        
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
    
    # Fix for control characters (newlines, tabs) in string values from Ökofen API
    # The API sometimes returns error messages with actual newlines in JSON strings
    # which is invalid JSON. We need to escape them before parsing.
    # Find all string values and escape control characters within them
    def escape_control_chars(match):
        string_content = match.group(1)
        # Escape newlines, tabs, carriage returns
        string_content = string_content.replace('\n', '\\n')
        string_content = string_content.replace('\r', '\\r')
        string_content = string_content.replace('\t', '\\t')
        return f'"{string_content}"'
    
    # Match strings in JSON (handling escaped quotes)
    str_response = re.sub(r'"((?:[^"\\]|\\.)*)(?<!\\)"', escape_control_chars, str_response)
    
    result = json.loads(str_response, strict=False)
    return result


def send_data(url: str, charset: str = DEFAULT_CHARSET) -> str:
    """Send data to API.
    
    Args:
        url: API endpoint URL
        charset: Character encoding for response
        
    Returns:
        Response text from API
        
    Raises:
        urllib.error.HTTPError: When API returns an error (e.g., 401 Unauthorized)
        Exception: For other network or communication errors
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
    except urllib.error.HTTPError as err:
        _LOGGER.error(
            "HTTP Error %s when sending data to %s: %s",
            err.code,
            url,
            err.reason,
        )
        raise
    except Exception as err:
        _LOGGER.error("Error sending data to %s: %s", url, err)
        raise
    finally:
        if response is not None:
            response.close()
    return str_response
