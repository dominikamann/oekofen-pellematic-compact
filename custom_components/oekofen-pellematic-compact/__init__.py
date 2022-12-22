import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_URL, CONF_NAME
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, CONF_UPDATE_INTERVAL, CONF_NAME, CONF_URL

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_URL): vol.Url(),
                vol.Optional(CONF_NAME, default="Pellematic Compact"): cv.string,
                vol.Optional(CONF_UPDATE_INTERVAL, default=60): cv.positive_int,
            },
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["binary_sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the oekofen-pellematic-compact integration."""
    for component in PLATFORMS:
        hass.async_create_task(
            hass.helpers.discovery.async_load_platform(
                component, DOMAIN, config.get(DOMAIN), config
            )
        )
    return True