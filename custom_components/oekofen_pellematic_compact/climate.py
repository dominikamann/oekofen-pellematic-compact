import logging
from typing import Optional, Any, Dict
import asyncio

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate import (
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    PRESET_AWAY,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE, 
    PRECISION_HALVES,
    UnitOfTemperature,
)   
from .const import (
    CONF_NUM_OF_HEATING_CIRCUIT,
    DOMAIN,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    get_api_value,
)

from homeassistant.const import (
    CONF_NAME,
)

from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.PRESET_MODE
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
)
SUPPORT_PRESET = [PRESET_AWAY, PRESET_ECO, PRESET_COMFORT, PRESET_NONE]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]
    
    num_heating_circuit = entry.data.get(CONF_NUM_OF_HEATING_CIRCUIT, 1)

    _LOGGER.debug("Setup entry %s %s", hub_name, hub)
    
    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": ATTR_MODEL,
    }
    
    def create_climate_entities(data: Dict[str, Any]) -> list:
        """Factory function to create climate entities from discovery data."""
        entities = []
        
        try:
            climates_to_add = [
                ("hk", num_heating_circuit),
            ]

            for prefix, num_climate in climates_to_add:
                for n in range(1, num_climate + 1):
                    try:
                        climate = PellematicClimate(
                                hub_name,
                                hub,
                                device_info,
                                f"{prefix}{n}",
                                n
                            )
                        climate._entity_id_key = f"{prefix}{n}_climate"
                        entities.append(climate)
                    except Exception as e:
                        _LOGGER.error("Failed to create climate %s%d: %s", prefix, n, e)
            
        except Exception as e:
            _LOGGER.error("Error during climate setup: %s", e)
        
        return entities
    
    # Use common setup logic with retry mechanism
    from . import setup_platform_with_retry
    await setup_platform_with_retry(
        hass, hub, hub_name, device_info, "climate",
        create_climate_entities, async_add_entities
    )

class PellematicClimate(ClimateEntity):
    def __init__(
        self,
        platform_name,
        hub,
        device_info,
        prefix,
        heater_num
    ) -> None:
        self._platform_name = platform_name
        self._hub = hub        
        self._prefix = prefix
        self._heater_num = heater_num
        self._attr_unique_id = f"{self._platform_name.lower()}_{self._prefix}_climate"
        # Use component_key for entity_id instead of long human-readable name
        self._attr_object_id = f"{self._prefix}_climate"
        self._attr_current_option = None
        self._device_info = device_info
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_current_temperature = None
        self._attr_target_temperature_comfort = None
        self._attr_target_temperature_slow = None
        self._attr_target_temperature_auto = None
        self._attr_target_temperature_vacation = None
        self._attr_preset_mode = PRESET_NONE
        self._attr_preset_modes = SUPPORT_PRESET
        self._attr_supported_features = SUPPORT_FLAGS
        self._attr_hvac_mode = HVACMode.AUTO
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF, HVACMode.AUTO]
        self._attr_target_temperature_step = PRECISION_HALVES
                
        _LOGGER.debug(
            "Adding a PellematicClimate : %s, %s, %s, %s, %s, %s",
            str(self._platform_name),
            str(self._hub),
            str(self._prefix),
            str(self._attr_unique_id),
            str(self._attr_current_option),
            str(self._device_info),
        )
    
    @callback
    def _api_data_updated(self):
        self._update_state()
        self.async_write_ha_state()

    @callback
    def _update_state(self):
        if self._prefix not in self._hub.data:
            return
            
        data = self._hub.data[self._prefix]
        if "L_roomtemp_act" in data:
            self._attr_current_temperature = float(get_api_value(data["L_roomtemp_act"], 0)) / 10
            
        # Get the remote override value (if any)
        remote_override = float(get_api_value(data.get("remote_override"), 0)) / 10
            
        if "temp_heat" in data:
            # Base comfort temperature without override
            self._attr_target_temperature_comfort = float(get_api_value(data["temp_heat"], 0)) / 10
            
        if "temp_setback" in data:
            self._attr_target_temperature_slow = float(get_api_value(data["temp_setback"], 0)) / 10
        
        if "temp_vacation" in data:
            self._attr_target_temperature_vacation = float(get_api_value(data["temp_vacation"], 0)) / 10
            
        if "L_roomtemp_set" in data and "temp_heat" in data:
            # For Auto mode, L_roomtemp_set includes the remote_override adjustment
            # We need to subtract remote_override to get the base temperature
            l_roomtemp_set = float(get_api_value(data["L_roomtemp_set"], 0)) / 10
            base_temp = l_roomtemp_set - remote_override
            self._attr_target_temperature_auto = base_temp
            
        if "mode_auto" in data:
            mode_auto_val = int(get_api_value(data["mode_auto"], 1))
            if mode_auto_val == 2:
                self._attr_hvac_mode = HVACMode.HEAT
            elif mode_auto_val == 3:
                self._attr_hvac_mode = HVACMode.OFF
            elif mode_auto_val == 1:
                self._attr_hvac_mode = HVACMode.AUTO
        
        # Read oekomode for preset mode
        # 0:Arrêt|1:Confort|2:Intermédiaire|3:Ecologique
        if "oekomode" in data:
            oekomode_val = int(get_api_value(data["oekomode"], 2))
            if oekomode_val == 0:
                self._attr_preset_mode = PRESET_AWAY  # Arrêt = Away/Vacation
            elif oekomode_val == 1:
                self._attr_preset_mode = PRESET_COMFORT  # Confort
            elif oekomode_val == 2:
                self._attr_preset_mode = PRESET_NONE  # Intermédiaire
            elif oekomode_val == 3:
                self._attr_preset_mode = PRESET_ECO  # Ecologique
            else:
                self._attr_preset_mode = PRESET_NONE

    async def async_added_to_hass(self):
        self._hub.async_add_pellematic_sensor(self._api_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_pellematic_sensor(self._api_data_updated)

    @property
    def name(self):
        return f"Heating Circuit {self._heater_num} Climate"

    @property
    def unique_id(self):
        return f"{self._attr_unique_id}"
    
    @property
    def current_temperature(self) -> float | None:
        return self._attr_current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature based on preset mode."""
        # Preset mode takes precedence over HVAC mode for target temperature
        if self._attr_preset_mode == PRESET_AWAY:
            # Away/Vacation mode uses temp_vacation
            return self._attr_target_temperature_vacation
        elif self._attr_preset_mode == PRESET_ECO:
            # Eco/Ecological mode uses temp_setback (reduced temperature)
            return self._attr_target_temperature_slow
        elif self._attr_preset_mode == PRESET_COMFORT:
            # Comfort mode uses temp_heat
            return self._attr_target_temperature_comfort
        
        # Fallback to HVAC mode if no preset or PRESET_NONE
        if self._attr_hvac_mode == HVACMode.OFF:
            return self._attr_target_temperature_slow
        elif self._attr_hvac_mode == HVACMode.HEAT:
            return self._attr_target_temperature_comfort
        elif self._attr_hvac_mode == HVACMode.AUTO:
            return self._attr_target_temperature_auto
        
        return None
    
    @property
    def hvac_mode(self) -> HVACMode:
        return self._attr_hvac_mode
    
    @property
    def preset_mode(self) -> str:
        """Return current preset mode."""
        return self._attr_preset_mode
    
    @property
    def preset_modes(self) -> list[str]:
        return SUPPORT_PRESET

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def device_info(self) -> Optional[dict[str, Any]]:
        return self._device_info

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE not in kwargs:
            return
            
        temperature = kwargs[ATTR_TEMPERATURE]
        temperature_int = int(temperature * 10)
        
        _LOGGER.info("Setting temperature for %s in mode %s to %s (int: %s)", 
                    self._prefix, self._attr_hvac_mode, temperature, temperature_int)
        
        try:
            if self._attr_hvac_mode == HVACMode.OFF:
                self._attr_target_temperature_slow = temperature
                _LOGGER.info("Sending setback temperature for %s: %s", self._prefix, temperature_int)
                await self.hass.async_add_executor_job(
                    self._hub.send_pellematic_data,
                    temperature_int,
                    self._prefix,
                    "temp_setback"
                )
            elif self._attr_hvac_mode in [HVACMode.HEAT, HVACMode.AUTO]:
                # Both HEAT and AUTO modes use temp_heat for setting the target
                # We don't need to account for remote_override here as we're setting the base temperature
                self._attr_target_temperature_comfort = temperature
                self._attr_target_temperature_auto = temperature  # Keep auto temperature in sync
                _LOGGER.info("Sending heat temperature for %s: %s", self._prefix, temperature_int)
                await self.hass.async_add_executor_job(
                    self._hub.send_pellematic_data,
                    temperature_int,
                    self._prefix,
                    "temp_heat"
                )
            _LOGGER.info("Temperature set successfully")
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error(
                "Failed to set temperature to %s for %s: %s",
                temperature,
                self.entity_id,
                err,
            )
            # Re-raise to let Home Assistant handle it properly
            raise

    async def async_set_hvac_mode(self, hvac_mode):
        self._attr_hvac_mode = hvac_mode
        
        _LOGGER.info("Setting HVAC mode for %s to %s", self._prefix, hvac_mode)
        
        try:
            if hvac_mode == HVACMode.OFF:
                _LOGGER.info("Sending OFF mode (3) for %s", self._prefix)
                await self.hass.async_add_executor_job(
                    self._hub.send_pellematic_data,
                    3,
                    self._prefix,
                    "mode_auto"
                )
            elif hvac_mode == HVACMode.HEAT:
                _LOGGER.info("Sending HEAT mode (2) for %s", self._prefix)
                await self.hass.async_add_executor_job(
                    self._hub.send_pellematic_data,
                    2, 
                    self._prefix,
                    "mode_auto"
                )
            elif hvac_mode == HVACMode.AUTO:
                _LOGGER.info("Sending AUTO mode (1) for %s", self._prefix)
                await self.hass.async_add_executor_job(
                    self._hub.send_pellematic_data,
                    1,   
                    self._prefix,
                    "mode_auto"
                )
            _LOGGER.info("HVAC mode set successfully")
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error(
                "Failed to set HVAC mode to %s for %s: %s",
                hvac_mode,
                self.entity_id,
                err,
            )
            # Re-raise to let Home Assistant handle it properly
            raise

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode in self._attr_preset_modes:
            try:
                self._attr_current_option = preset_mode
                if preset_mode == PRESET_ECO:
                    await self.hass.async_add_executor_job(
                        self._hub.send_pellematic_data,
                        3,  # Eco mode
                        self._prefix,
                        "mode_auto"
                    )
                self.async_write_ha_state()
            except Exception as err:
                _LOGGER.error(
                    "Failed to set preset mode to %s for %s: %s",
                    preset_mode,
                    self.entity_id,
                    err,
                )
                # Re-raise to let Home Assistant handle it properly
                raise
    
    @property
    def supported_features(self) -> ClimateEntityFeature:
        return SUPPORT_FLAGS 
