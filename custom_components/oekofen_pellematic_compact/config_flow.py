"""Config flow for Ökofen Pellematic Compact integration."""
import voluptuous as vol

from homeassistant import config_entries

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
    DEFAULT_NUM_OF_SMART_PV_SE,
    DEFAULT_NUM_OF_SMART_PV_SK,
    CONF_NUM_OF_HEATING_CIRCUIT,
    CONF_SOLAR_CIRCUIT,
    CONF_CIRCULATOR,
    CONF_SMART_PV,
    CONF_STIRLING
)

from homeassistant.core import HomeAssistant, callback

DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        vol.Optional(CONF_NUM_OF_HEATING_CIRCUIT, default=DEFAULT_NUM_OF_HEATING_CIRCUIT): int,
        vol.Optional(CONF_NUM_OF_HOT_WATER, default=DEFAULT_NUM_OF_HOT_WATER): int,
        vol.Optional(CONF_NUM_OF_PELLEMATIC_HEATER, default=DEFAULT_NUM_OF_PELLEMATIC_HEATER): int,
        vol.Optional(CONF_SOLAR_CIRCUIT, default=False): bool,
        vol.Optional(CONF_NUM_OF_SMART_PV_SE, default=DEFAULT_NUM_OF_SMART_PV_SE): int,
        vol.Optional(CONF_NUM_OF_HEAT_PUMPS, default=DEFAULT_NUM_OF_SMART_PV_SE): int,
        vol.Optional(CONF_NUM_OF_SMART_PV_SK, default=DEFAULT_NUM_OF_SMART_PV_SK): int,       
        vol.Optional(CONF_CIRCULATOR, default=False): bool,
        vol.Optional(CONF_SMART_PV, default=False): bool,
        vol.Optional(CONF_STIRLING, default=False): bool,
        vol.Optional(CONF_CHARSET, default=DEFAULT_CHARSET): str,

    }
)


def host_valid(host):
    """Return True if hostname or IP address is valid."""
    return True


@callback
def pellematic_compact_entries(hass: HomeAssistant):
    """Return the hosts already configured."""
    return set(
        entry.data[CONF_HOST] for entry in hass.config_entries.async_entries(DOMAIN)
    )


class OekofenPellematicCompactConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Oekofen Pellematic Compact configflow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def _host_in_configuration_exists(self, host) -> bool:
        """Return True if host exists in configuration."""
        if host in pellematic_compact_entries(self.hass):
            return True
        return False

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            if self._host_in_configuration_exists(host):
                errors[CONF_HOST] = "already_configured"
            elif not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid host IP"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
