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
    CONF_API_SUFFIX,
    DEFAULT_API_SUFFIX,
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
    
    This function handles mixed-encoding scenarios where the Ökofen API
    may send UTF-8 for most fields but ISO-8859-1 bytes in some values
    (e.g., location names with umlauts).
    
    Args:
        raw_data: Raw bytes from API response
        
    Returns:
        Suggested charset ('utf-8' or 'iso-8859-1')
    """
    # Try UTF-8 first with strict decoding
    try:
        decoded_utf8 = raw_data.decode('utf-8')
        # Successfully decoded as UTF-8 - this is the modern standard
        # Check if it contains any non-ASCII characters
        if any(ord(char) > 127 for char in decoded_utf8):
            # Contains non-ASCII characters and decodes cleanly - it's UTF-8
            return 'utf-8'
        # Only ASCII characters - could be either, default to UTF-8 (modern standard)
        return 'utf-8'
    except UnicodeDecodeError:
        # UTF-8 strict decode failed - could be ISO-8859-1 or mixed encoding
        # Try UTF-8 with replace to see how many characters are problematic
        decoded_utf8_replace = raw_data.decode('utf-8', errors='replace')
        replacement_count = decoded_utf8_replace.count('�')
        
        # Count non-ASCII characters
        non_ascii_count = sum(1 for char in decoded_utf8_replace if ord(char) > 127)
        
        # If replacement characters are less than 20% of non-ASCII chars,
        # it's likely mixed encoding with mostly UTF-8 → prefer UTF-8
        # Increased threshold from 10% to 20% to handle smaller responses
        if non_ascii_count > 0 and replacement_count / non_ascii_count < 0.2:
            # Mixed encoding detected: mostly UTF-8 with some ISO-8859-1 bytes
            # Prefer UTF-8 as it handles the majority of the content correctly
            # Individual ISO-8859-1 bytes will show as � which is acceptable
            # for rare fields like location names
            return 'utf-8'
        
        # Too many problematic characters - it's likely all ISO-8859-1
        return 'iso-8859-1'


def api_response_has_metadata(data: dict) -> bool:
    """Check if API response contains metadata (val, unit, factor).    
    Modern firmware (with ?) returns: {"L_ambient": {"val": "98", "unit": "°C", "factor": "0.1", ...}}
    Old firmware (needs ??) returns: {"L_ambient": "98"}
    
    Args:
        data: Parsed JSON data from API
        
    Returns:
        True if response contains metadata, False if simple values only
    """
    # Check a few common fields to see if they contain metadata
    # Look for nested dictionaries with 'val', 'unit', or 'factor' keys
    for section_key, section_value in data.items():
        if isinstance(section_value, dict):
            # Check fields within this section
            for field_key, field_value in section_value.items():
                if isinstance(field_value, dict):
                    # Check if this looks like metadata structure
                    if any(key in field_value for key in ['val', 'unit', 'factor', 'format']):
                        return True
                    # Found dict but no metadata keys - might be old format
                elif isinstance(field_value, (str, int, float, bool)):
                    # Found simple value - this might be old firmware
                    # But continue checking in case it's mixed
                    continue
    
    # No metadata found in any field
    return False


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
        self._api_suffix = DEFAULT_API_SUFFIX

    def _normalize_url(self, host: str, suffix: str = "?") -> str:
        """Normalize the URL by ensuring it ends with the correct API suffix.
        
        Args:
            host: The host URL
            suffix: API suffix to use ("?" or "??")
            
        Returns:
            Normalized URL with suffix appended
        """
        url = host.strip()
        # Remove any existing ? or ?? at the end
        url = url.rstrip('?')
        # Add the specified suffix
        url += suffix
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
    
    def _fetch_api_data(self, host: str, detect_charset: bool = False, detect_api_suffix: bool = False):
        """Fetch data from the Pellematic API (blocking).
        
        Args:
            host: The host URL to connect to (without ? or ??)
            detect_charset: If True, detect charset from response
            detect_api_suffix: If True, detect optimal API suffix (? or ??)
            
        Returns:
            - dict: Parsed JSON data if detect_charset=False and detect_api_suffix=False
            - tuple[dict, str]: (data, charset) if detect_charset=True and detect_api_suffix=False
            - tuple[dict, str, str]: (data, charset, api_suffix) if both detect flags are True
        """
        # Try with current suffix first, or use default
        suffix_to_try = self._api_suffix if hasattr(self, '_api_suffix') else DEFAULT_API_SUFFIX
        
        # If detecting API suffix, try both ? and ??
        if detect_api_suffix:
            # Try modern firmware first (single ?)
            try:
                data_single, charset_single = self._fetch_with_suffix(host, "?", detect_charset=True)
                
                # Check if response contains metadata
                if api_response_has_metadata(data_single):
                    # Modern firmware - has metadata with single ?
                    if detect_charset:
                        return data_single, charset_single, "?"
                    return data_single, "?"
                else:
                    # Old firmware - try with ??
                    import logging
                    _LOGGER = logging.getLogger(__name__)
                    _LOGGER.info("API response has no metadata with '?', trying '??' for old firmware compatibility")
                    
                    data_double, charset_double = self._fetch_with_suffix(host, "??", detect_charset=True)
                    if detect_charset:
                        return data_double, charset_double, "??"
                    return data_double, "??"
                    
            except Exception as e:
                import logging
                _LOGGER = logging.getLogger(__name__)
                _LOGGER.error("Failed to fetch with both ? and ??: %s", e)
                raise
        else:
            # Not detecting suffix - use existing one
            if detect_charset:
                data, charset = self._fetch_with_suffix(host, suffix_to_try, detect_charset=True)
                return data, charset
            else:
                return self._fetch_with_suffix(host, suffix_to_try, detect_charset=False)
    
    def _fetch_with_suffix(self, host: str, suffix: str, detect_charset: bool = False):
        """Fetch data with specific API suffix (blocking).
        
        Args:
            host: The host URL to connect to (without ? or ??)
            suffix: API suffix to use ("?" or "??")
            detect_charset: If True, return tuple (data, charset)
            
        Returns:
            Parsed JSON data, or tuple (data, charset) if detect_charset=True
        """
        url = self._normalize_url(host, suffix)
        
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
                # Clean host URL (remove any existing ? or ??)
                clean_host = host.strip().rstrip('?')
                
                # Auto-detect optimal charset and API suffix
                # If user provided a charset different from default, respect their choice
                user_provided_charset = user_input.get(CONF_CHARSET, DEFAULT_CHARSET)
                try:
                    # Detect both charset and API suffix (? vs ??)
                    data, suggested_charset, suggested_suffix = await self.hass.async_add_executor_job(
                        self._fetch_api_data, clean_host, True, True
                    )
                    
                    # Only override charset if user didn't explicitly change it from default
                    # This allows users to manually override auto-detection if needed
                    if user_provided_charset == DEFAULT_CHARSET:
                        charset = suggested_charset
                        user_input[CONF_CHARSET] = suggested_charset
                        
                        import logging
                        _LOGGER = logging.getLogger(__name__)
                        _LOGGER.info(
                            "Auto-detected charset '%s' and API suffix '%s'",
                            suggested_charset, suggested_suffix
                        )
                    else:
                        # User explicitly set a charset - respect their choice
                        charset = user_provided_charset
                        import logging
                        _LOGGER = logging.getLogger(__name__)
                        _LOGGER.info(
                            "Using user-provided charset '%s', auto-detected API suffix '%s'",
                            user_provided_charset, suggested_suffix
                        )
                    
                    if not errors:
                        # Store the charset and API suffix
                        self._charset = charset
                        self._api_suffix = suggested_suffix
                        user_input[CONF_HOST] = clean_host
                        user_input[CONF_API_SUFFIX] = suggested_suffix
                        
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
                    # Ensure charset has a fallback value
                    user_input.setdefault(CONF_CHARSET, DEFAULT_CHARSET)

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
                # Clean host URL (remove any existing ? or ??)
                clean_host = host.strip().rstrip('?')
                
                # Check if user manually changed charset from current config
                current_charset = current_config.get(CONF_CHARSET, DEFAULT_CHARSET)
                current_host = current_config.get(CONF_HOST, DEFAULT_HOST).rstrip('?')
                user_charset = user_input.get(CONF_CHARSET, DEFAULT_CHARSET)
                charset_manually_changed = (user_charset != current_charset)
                host_changed = (clean_host != current_host)
                
                # Auto-detect optimal charset and API suffix
                try:
                    # Detect both charset and API suffix
                    data, suggested_charset, suggested_suffix = await self.hass.async_add_executor_job(
                        self._fetch_api_data, clean_host, True, True
                    )
                    
                    # Only override charset if user didn't manually change it
                    # BUT: Always auto-detect if host changed (might be different API)
                    if charset_manually_changed:
                        # User explicitly changed charset - respect their choice
                        import logging
                        _LOGGER = logging.getLogger(__name__)
                        _LOGGER.info(
                            "Reconfigure: Using user-selected charset '%s', auto-detected API suffix '%s'",
                            user_charset, suggested_suffix
                        )
                        # Keep user's choice
                        user_input[CONF_CHARSET] = user_charset
                    elif host_changed:
                        # Host changed - auto-detect for new API
                        import logging
                        _LOGGER = logging.getLogger(__name__)
                        _LOGGER.info(
                            "Reconfigure: Host changed, auto-detected charset '%s' and API suffix '%s'",
                            suggested_charset, suggested_suffix
                        )
                        user_input[CONF_CHARSET] = suggested_charset
                    else:
                        # User didn't change charset or host - use auto-detection
                        import logging
                        _LOGGER = logging.getLogger(__name__)
                        _LOGGER.info(
                            "Reconfigure: Auto-detected charset '%s' and API suffix '%s'",
                            suggested_charset, suggested_suffix
                        )
                        user_input[CONF_CHARSET] = suggested_charset
                    
                    # Always save the detected API suffix
                    user_input[CONF_API_SUFFIX] = suggested_suffix
                    
                    if not errors:
                        # No error - proceed with update
                        user_input[CONF_HOST] = clean_host
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
                    # Ensure charset and API suffix have fallback values
                    user_input.setdefault(CONF_CHARSET, current_config.get(CONF_CHARSET, DEFAULT_CHARSET))
                    user_input.setdefault(CONF_API_SUFFIX, current_config.get(CONF_API_SUFFIX, DEFAULT_API_SUFFIX))
    
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
