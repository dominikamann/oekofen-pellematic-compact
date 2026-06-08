"""Binary sensor platform for Ökofen Pellematic Compact."""

import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_MANUFACTURER, ATTR_MODEL, DOMAIN
from .dynamic_discovery import discover_all_entities
from .sensor import PellematicBinarySensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors using dynamic discovery."""
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
    }

    def create_binary_sensor_entities(data: Dict[str, Any]) -> list:
        entities = []
        discovered = discover_all_entities(data)

        _LOGGER.info(
            "Dynamically discovered %d binary sensors",
            len(discovered["binary_sensors"]),
        )

        for sensor_def in discovered["binary_sensors"]:
            try:
                sensor = PellematicBinarySensor(
                    hub_name=hub_name,
                    hub=hub,
                    device_info=device_info,
                    sensor_definition=sensor_def,
                )
                sensor._entity_id_key = f"{sensor_def['component']}_{sensor_def['key']}"
                entities.append(sensor)
            except Exception as e:
                _LOGGER.error(
                    "Failed to create binary sensor %s_%s: %s",
                    sensor_def["component"],
                    sensor_def["key"],
                    e,
                )

        return entities

    from . import setup_platform_with_retry

    await setup_platform_with_retry(
        hass,
        hub,
        hub_name,
        device_info,
        "binary_sensor",
        create_binary_sensor_entities,
        async_add_entities,
    )
