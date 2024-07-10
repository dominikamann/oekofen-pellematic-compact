"""Demo platform that offers a fake select entity."""

from __future__ import annotations
import logging

from homeassistant.components.select import SelectEntity

from .const import (
    CONF_NUM_OF_HEATING_CIRCUIT,
    CONF_NUM_OF_HOT_WATER,
    HK_SELECT_TYPES,
    WW_SELECT_TYPES,
    DOMAIN,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
)

from homeassistant.const import (
    CONF_NAME,
)
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]
    
    try:
        num_heating_circuit = entry.data[CONF_NUM_OF_HEATING_CIRCUIT]
    except:
        num_heating_circuit = 1
    try:
        num_hot_water = entry.data[CONF_NUM_OF_HOT_WATER]
    except:
        num_hot_water = 1

    _LOGGER.debug("Setup entry %s %s", hub_name, hub)
    
    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
    }
    
    entities = []
    
    for heating_cir_count in range(num_heating_circuit):
        for name, key, trname, options  in HK_SELECT_TYPES.values():
            select = PellematicSelect(
                hub_name,
                hub,
                device_info,
                f"hk{heating_cir_count +1}",
                name.format(" " + str(heating_cir_count + 1)),
                key,
                options,
                trname
            )
            entities.append(select)    
    for hot_water_count in range(num_hot_water):
        for name, key, trname, options in WW_SELECT_TYPES.values():
            select = PellematicSelect(
                hub_name,
                hub,
                device_info,
                f"ww{hot_water_count +1}",
                name.format(" " + str(hot_water_count + 1)),
                key,
                options,
                trname
            )
            entities.append(select)
    
    _LOGGER.debug("Entities added : %i", len(entities))
    
    async_add_entities(entities)


class PellematicSelect(SelectEntity):
    """Representation of a select entity."""
    
    #_attr_has_entity_name = True
    #_attr_name = None
    #_attr_should_poll = False

    def __init__(
        self,
        platform_name,
        hub,
        device_info,
        prefix,
        name,
        key,
        options,
        translation_key,
    ) -> None:
        """Initialize the select."""
        self._platform_name = platform_name
        self._hub = hub        
        self._prefix = prefix
        self._key = key
        self._name = f"{self._platform_name} {name}"
        self._attr_unique_id = f"{self._platform_name.lower()}_{self._prefix}_{self._key}"
        self._attr_current_option = None
        self._attr_options = options
        self._device_info = device_info
        self._attr_translation_key = translation_key
        
        _LOGGER.debug(
            "Adding a PellematicSelect : %s, %s, %s, %s, %s, %s, %s, %s, %s",
            str(self._platform_name),
            str(self._hub),
            str(self._prefix),
            str(self._key),
            str(self._name),
            str(self._attr_unique_id),
            str(self._attr_current_option),
            str(self._attr_options),
            str(self._device_info),
        )

    @callback
    def _api_data_updated(self):
        self._update_state()
        self.async_write_ha_state()        


    async def async_added_to_hass(self):
        """Register callbacks."""
        self._hub.async_add_pellematic_sensor(self._api_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_pellematic_sensor(self._api_data_updated)

    async def async_select_option(self, option) -> None:
        """Update the current selected option."""
        self._attr_current_option = option
        await self.hass.async_add_executor_job(
            self._hub.send_pellematic_data,
            option[:1],
            self._prefix,
            self._key
        )
        self.async_write_ha_state()

    def _update_current_option(self):
        try:
            current_value = self._hub.data[self._prefix][self._key]
            return self._attr_options[int(current_value)]
        except:
            return None

    @callback
    def _update_state(self):
        self._attr_current_option = self._update_current_option()
        
    @property
    def name(self):
        """Return the name."""
        return f"{self._name}"

    @property
    def state(self):
        """Return the entity state."""
        return self._attr_current_option

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return False
    
    @property
    def device_info(self) -> Optional[dict[str, Any]]:
        return self._device_info

    @property
    def options(self) -> list[str]:
        """Return a set of selectable options."""
        return self._attr_options
        raise AttributeError

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""                
        return self._attr_current_option