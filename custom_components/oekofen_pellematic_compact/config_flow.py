"""Config flow for Ökofen Pellematic Compact integration."""
import voluptuous as vol
import urllib.request
import json

from homeassistant import config_entries
from typing import Any, Dict


from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_SCAN_INTERVAL,
)

from .const import (
    CONF_CHARSET,
    DEFAULT_CHARSET,
    DOMAIN,
    DEFAULT_HOST,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_NUM_OF_HEATING_CIRCUIT,
    DEFAULT_NUM_OF_HOT_WATER,
    CONF_NUM_OF_HOT_WATER,
    DEFAULT_NUM_OF_PELLEMATIC_HEATER,
    CONF_NUM_OF_PELLEMATIC_HEATER,
    CONF_NUM_OF_SMART_PV_SE,
    CONF_NUM_OF_SMART_PV_SK,
    CONF_NUM_OF_HEAT_PUMPS,
    DEFAULT_NUM_OF_HEAT_PUMPS,
    DEFAULT_NUM_OF_SMART_PV_SE,
    DEFAULT_NUM_OF_SMART_PV_SK,
    CONF_NUM_OF_HEATING_CIRCUIT,
    CONF_SOLAR_CIRCUIT,
    CONF_CIRCULATOR,
    CONF_SMART_PV,
    CONF_STIRLING,
    DEFAULT_NUM_OF_WIRELESS_SENSORS,
    CONF_NUM_OF_WIRELESS_SENSORS,
    CONF_NUM_OF_BUFFER_STORAGE,
    DEFAULT_NUM_OF_BUFFER_STORAGE
)

from homeassistant.core import HomeAssistant, callback

# Step 1: Only ask for connection details
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Optional(CONF_CHARSET, default=DEFAULT_CHARSET): str,
    }
)

# Step 2: Show discovered values and allow manual adjustment
def get_advanced_schema(discovered: dict) -> vol.Schema:
    """Generate schema with discovered values as defaults."""
    return vol.Schema(
        {
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            vol.Optional(CONF_NUM_OF_HEATING_CIRCUIT, default=discovered.get(CONF_NUM_OF_HEATING_CIRCUIT, DEFAULT_NUM_OF_HEATING_CIRCUIT)): int,
            vol.Optional(CONF_NUM_OF_HOT_WATER, default=discovered.get(CONF_NUM_OF_HOT_WATER, DEFAULT_NUM_OF_HOT_WATER)): int,
            vol.Optional(CONF_NUM_OF_PELLEMATIC_HEATER, default=discovered.get(CONF_NUM_OF_PELLEMATIC_HEATER, DEFAULT_NUM_OF_PELLEMATIC_HEATER)): int,
            vol.Optional(CONF_SOLAR_CIRCUIT, default=discovered.get(CONF_SOLAR_CIRCUIT, False)): bool,
            vol.Optional(CONF_NUM_OF_SMART_PV_SE, default=discovered.get(CONF_NUM_OF_SMART_PV_SE, DEFAULT_NUM_OF_SMART_PV_SE)): int,
            vol.Optional(CONF_NUM_OF_SMART_PV_SK, default=discovered.get(CONF_NUM_OF_SMART_PV_SK, DEFAULT_NUM_OF_SMART_PV_SK)): int,   
            vol.Optional(CONF_NUM_OF_HEAT_PUMPS, default=discovered.get(CONF_NUM_OF_HEAT_PUMPS, DEFAULT_NUM_OF_HEAT_PUMPS)): int,    
            vol.Optional(CONF_NUM_OF_WIRELESS_SENSORS, default=discovered.get(CONF_NUM_OF_WIRELESS_SENSORS, DEFAULT_NUM_OF_WIRELESS_SENSORS)): int,
            vol.Optional(CONF_NUM_OF_BUFFER_STORAGE, default=discovered.get(CONF_NUM_OF_BUFFER_STORAGE, DEFAULT_NUM_OF_BUFFER_STORAGE)): int,
            vol.Optional(CONF_CIRCULATOR, default=discovered.get(CONF_CIRCULATOR, False)): bool,
            vol.Optional(CONF_SMART_PV, default=discovered.get(CONF_SMART_PV, False)): bool,
            vol.Optional(CONF_STIRLING, default=discovered.get(CONF_STIRLING, False)): bool,
        }
    )


def host_valid(host):
    """Return True if hostname or IP address is valid."""
    return True


def charset_valid(charset: str) -> bool:
    """Return True if charset is a valid Python codec.
    
    Args:
        charset: Character encoding name
        
    Returns:
        True if charset is valid, False otherwise
    """
    import codecs
    try:
        codecs.lookup(charset)
        return True
    except LookupError:
        return False


def detect_charset_from_response(raw_data: bytes) -> str:
    """Detect the most likely charset from API response data.
    
    This function analyzes the raw bytes from the API response and detects
    common encoding issues to suggest the correct charset.
    
    Args:
        raw_data: Raw bytes from API response
        
    Returns:
        Suggested charset ('utf-8' or 'iso-8859-1')
    """
    # Try UTF-8 first with strict decoding (no ignore)
    try:
        decoded_utf8 = raw_data.decode('utf-8')
        # Successfully decoded as UTF-8
        # Check if it contains any non-ASCII characters (multi-byte UTF-8)
        # This works for all languages: German, French, Italian, Spanish, Polish, etc.
        if any(ord(char) > 127 for char in decoded_utf8):
            # Contains non-ASCII characters and decodes cleanly - it's UTF-8
            return 'utf-8'
        # Only ASCII characters - could be either, default to UTF-8 (modern standard)
        return 'utf-8'
    except UnicodeDecodeError:
        # Can't decode as UTF-8 - it's ISO-8859-1 or another single-byte encoding
        return 'iso-8859-1'


@callback
def pellematic_compact_entries(hass: HomeAssistant):
    """Return the hosts already configured."""
    return set(
        entry.data[CONF_HOST] for entry in hass.config_entries.async_entries(DOMAIN)
    )


class OekofenPellematicCompactConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Oekofen Pellematic Compact configflow."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the config flow."""
        self._discovered_data = {}
        self._user_input = {}
        self._charset = DEFAULT_CHARSET

    def _normalize_url(self, host: str) -> str:
        """Normalize the URL by ensuring it ends with '?' for full API response.
        
        Args:
            host: The host URL
            
        Returns:
            Normalized URL with '?' appended if not present
        """
        url = host.strip()
        if not url.endswith('?'):
            url += '?'
        return url

    async def _async_discover_components(self, host: str) -> dict:
        """Try to discover components from the API.
        
        Args:
            host: The host URL to connect to
            
        Returns:
            Dictionary with discovered component counts
        """
        try:
            # Fetch data from API
            data = await self.hass.async_add_executor_job(self._fetch_api_data, host)
            
            if not data:
                return {}
            
            # Use the discovery function from __init__.py
            from . import discover_components_from_api
            discovered = discover_components_from_api(data)
            
            return discovered
        except Exception as e:
            import logging
            _LOGGER = logging.getLogger(__name__)
            _LOGGER.error("Failed to discover components: %s", e)
            return {}
    
    def _fetch_api_data(self, host: str, detect_charset: bool = False) -> dict | tuple[dict, str]:
        """Fetch data from the Pellematic API (blocking).
        
        Args:
            host: The host URL to connect to
            detect_charset: If True, return (data, suggested_charset) tuple
            
        Returns:
            Parsed JSON data from the API, or (data, suggested_charset) if detect_charset=True
        """
        url = self._normalize_url(host)
        
        req = urllib.request.Request(url)
        response = None
        
        try:
            response = urllib.request.urlopen(req, timeout=5)
            raw_data = response.read()
            
            # Detect optimal charset if requested
            if detect_charset:
                suggested_charset = detect_charset_from_response(raw_data)
                str_response = raw_data.decode(suggested_charset, 'ignore')
            else:
                suggested_charset = None
                str_response = raw_data.decode(self._charset, 'ignore')
            
            # Apply hotfix for invalid JSON
            str_response = str_response.replace("L_statetext:", 'L_statetext":')
            data = json.loads(str_response, strict=False)
            
            if detect_charset:
                return data, suggested_charset
            return data
        finally:
            if response is not None:
                response.close()

    def _host_in_configuration_exists(self, host) -> bool:
        """Return True if host exists in configuration."""
        if host in pellematic_compact_entries(self.hass):
            return True
        return False

    async def async_step_user(self, user_input=None):
        """Handle the initial step - connection details."""
        errors = {}
        description_placeholders = {
            "example_url": "http://192.168.178.91:4321/8n2L/all",
            "charset_warning": ""  # Empty by default
        }

        if user_input is not None:
            host = user_input[CONF_HOST]

            # Validate charset
            charset = user_input.get(CONF_CHARSET, DEFAULT_CHARSET)
            if not charset_valid(charset):
                errors[CONF_CHARSET] = "invalid_charset"
            # Check if already configured
            elif self._host_in_configuration_exists(host):
                errors[CONF_HOST] = "already_configured"
            elif not host_valid(host):
                errors[CONF_HOST] = "invalid_host_ip"
            else:
                # Normalize URL (add '?' if needed)
                normalized_host = self._normalize_url(host)
                
                # Auto-detect optimal charset
                try:
                    data, suggested_charset = await self.hass.async_add_executor_job(
                        self._fetch_api_data, normalized_host, True
                    )
                    
                    # Use the detected charset instead of user input
                    charset = suggested_charset
                    user_input[CONF_CHARSET] = suggested_charset
                    
                    # Log if we changed the charset
                    if suggested_charset != user_input.get(CONF_CHARSET, DEFAULT_CHARSET):
                        import logging
                        _LOGGER = logging.getLogger(__name__)
                        _LOGGER.info(
                            "Auto-detected charset '%s' (user selected '%s')",
                            suggested_charset, user_input.get(CONF_CHARSET, DEFAULT_CHARSET)
                        )
                    
                    if not errors:
                        # Store the detected charset
                        self._charset = charset
                        user_input[CONF_HOST] = normalized_host
                        
                        # Try to discover components
                        from . import discover_components_from_api
                        discovered = discover_components_from_api(data)
                        
                        if not discovered:
                            errors["base"] = "cannot_connect"
                        else:
                            # Store initial user input and discovered data
                            self._user_input = user_input
                            self._discovered_data = discovered
                            
                            import logging
                            _LOGGER = logging.getLogger(__name__)
                            _LOGGER.info("Auto-discovered components: %s", discovered)
                            
                            # Move to advanced configuration step
                            return await self.async_step_advanced()
                        
                except Exception as e:
                    import logging
                    _LOGGER = logging.getLogger(__name__)
                    _LOGGER.error("Failed to connect or discover: %s", e)
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA, 
            errors=errors,
            description_placeholders=description_placeholders
        )
    
    async def async_step_advanced(self, user_input=None):
        """Handle advanced configuration step - show discovered values and allow adjustments."""
        errors = {}
        
        if user_input is not None:
            # Merge all configuration: base input + discovered + user adjustments
            final_config = {
                **self._user_input,
                **self._discovered_data,
                **user_input,
            }
            
            # Set unique ID and create entry
            await self.async_set_unique_id(final_config[CONF_HOST])
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=final_config[CONF_NAME], 
                data=final_config
            )
        
        # Generate schema with discovered values as defaults
        advanced_schema = get_advanced_schema(self._discovered_data)
        
        # Create description with discovered components summary
        discovered_summary = []
        if self._discovered_data.get(CONF_NUM_OF_HEATING_CIRCUIT, 0) > 0:
            discovered_summary.append(f"Heating circuits: {self._discovered_data[CONF_NUM_OF_HEATING_CIRCUIT]}")
        if self._discovered_data.get(CONF_NUM_OF_HOT_WATER, 0) > 0:
            discovered_summary.append(f"Hot water: {self._discovered_data[CONF_NUM_OF_HOT_WATER]}")
        if self._discovered_data.get(CONF_NUM_OF_PELLEMATIC_HEATER, 0) > 0:
            discovered_summary.append(f"Heaters: {self._discovered_data[CONF_NUM_OF_PELLEMATIC_HEATER]}")
        
        summary_text = "\n".join(discovered_summary) if discovered_summary else "No components discovered"
        
        return self.async_show_form(
            step_id="advanced",
            data_schema=advanced_schema,
            errors=errors,
            description_placeholders={
                "discovered": summary_text
            }
        )
        
    async def async_step_reconfigure(self, user_input: Dict[str, Any] | None = None):
        """Handle reconfiguration."""
        errors = {}
        description_placeholders = {
            "charset_warning": ""  # Empty by default
        }
    
        # Ensure the context contains the entry ID
        if "entry_id" not in self.context:
            return self.async_abort(reason="missing_entry_id")
    
        # Get the current configuration entry
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if not config_entry:
            return self.async_abort(reason="entry_not_found")
    
        # Load current configuration as defaults for the form
        current_config = config_entry.data
    
        if user_input is not None:
            # Validate and save the new configuration
            host = user_input[CONF_HOST]
            charset = user_input.get(CONF_CHARSET, DEFAULT_CHARSET)
    
            if not charset_valid(charset):
                errors[CONF_CHARSET] = "invalid_charset"
            elif not host_valid(host):
                errors[CONF_HOST] = "invalid_host_ip"
            else:
                # Normalize URL (add '?' if needed)
                normalized_host = self._normalize_url(host)
                
                # Auto-detect optimal charset and use it
                try:
                    data, suggested_charset = await self.hass.async_add_executor_job(
                        self._fetch_api_data, normalized_host, True
                    )
                    
                    # Use the detected charset instead of user input
                    user_input[CONF_CHARSET] = suggested_charset
                    
                    # Log if we changed the charset
                    if suggested_charset != charset:
                        import logging
                        _LOGGER = logging.getLogger(__name__)
                        _LOGGER.info(
                            "Reconfigure: Auto-detected charset '%s' (user selected '%s')",
                            suggested_charset, charset
                        )
                    
                    if not errors:
                        # No error - proceed with update
                        user_input[CONF_HOST] = normalized_host
                        # Merge new input with current config
                        updated_config = {**current_config, **user_input}
                        self.hass.config_entries.async_update_entry(
                            config_entry,
                            data=updated_config,
                        )
                        await self.hass.config_entries.async_reload(config_entry.entry_id)
                        return self.async_abort(reason="reconfiguration_successful")
                        
                except Exception as e:
                    import logging
                    _LOGGER = logging.getLogger(__name__)
                    _LOGGER.error("Failed to connect during reconfigure: %s", e)
                    errors["base"] = "cannot_connect"
    
        # Create a schema with current configuration as defaults
        data_schema = vol.Schema(
            {
                #vol.Optional(CONF_NAME, default=current_config.get(CONF_NAME, DEFAULT_NAME)): str, Do not add as it has changes in sensor names
                vol.Optional(CONF_HOST, default=current_config.get(CONF_HOST, DEFAULT_HOST)): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=current_config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
                vol.Optional(CONF_NUM_OF_HEATING_CIRCUIT, default=current_config.get(CONF_NUM_OF_HEATING_CIRCUIT, DEFAULT_NUM_OF_HEATING_CIRCUIT)): int,
                vol.Optional(CONF_NUM_OF_HOT_WATER, default=current_config.get(CONF_NUM_OF_HOT_WATER, DEFAULT_NUM_OF_HOT_WATER)): int,
                vol.Optional(CONF_NUM_OF_PELLEMATIC_HEATER, default=current_config.get(CONF_NUM_OF_PELLEMATIC_HEATER, DEFAULT_NUM_OF_PELLEMATIC_HEATER)): int,
                vol.Optional(CONF_SOLAR_CIRCUIT, default=current_config.get(CONF_SOLAR_CIRCUIT, False)): bool,
                vol.Optional(CONF_NUM_OF_SMART_PV_SE, default=current_config.get(CONF_NUM_OF_SMART_PV_SE, DEFAULT_NUM_OF_SMART_PV_SE)): int,
                vol.Optional(CONF_NUM_OF_SMART_PV_SK, default=current_config.get(CONF_NUM_OF_SMART_PV_SK, DEFAULT_NUM_OF_SMART_PV_SK)): int,
                vol.Optional(CONF_NUM_OF_HEAT_PUMPS, default=current_config.get(CONF_NUM_OF_HEAT_PUMPS, DEFAULT_NUM_OF_HEAT_PUMPS)): int,
                vol.Optional(CONF_NUM_OF_WIRELESS_SENSORS, default=DEFAULT_NUM_OF_WIRELESS_SENSORS): int,
                vol.Optional(CONF_NUM_OF_BUFFER_STORAGE, default=DEFAULT_NUM_OF_BUFFER_STORAGE): int,
                vol.Optional(CONF_CIRCULATOR, default=current_config.get(CONF_CIRCULATOR, False)): bool,
                vol.Optional(CONF_SMART_PV, default=current_config.get(CONF_SMART_PV, False)): bool,
                vol.Optional(CONF_STIRLING, default=current_config.get(CONF_STIRLING, False)): bool,
                vol.Optional(CONF_CHARSET, default=current_config.get(CONF_CHARSET, DEFAULT_CHARSET)): str,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )
