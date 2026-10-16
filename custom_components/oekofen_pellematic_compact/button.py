"""Button platform for Ökofen Pellematic Compact (diagnosis: maintenance done)."""

from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_MANUFACTURER, ATTR_MODEL, DOMAIN
from .diagnosis_entities import create_diagnosis_buttons


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the 'maintenance done' button of each Pellematic."""
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]
    monitor = hass.data[DOMAIN][hub_name].get("diagnosis")

    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
    }

    def create_button_entities(data: Dict[str, Any]) -> list:
        if monitor is None:
            return []
        return create_diagnosis_buttons(hub_name, hub, device_info, monitor, data)

    from . import setup_platform_with_retry

    await setup_platform_with_retry(
        hass, hub, hub_name, device_info, "button", create_button_entities, async_add_entities
    )
