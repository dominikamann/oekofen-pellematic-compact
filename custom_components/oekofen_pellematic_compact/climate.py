import logging
from typing import Optional, Any, Dict
import asyncio

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate import (
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    PRESET_HOME,
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
# Vacation/Away mode is controlled separately via L_state, not oekomode
SUPPORT_PRESET = [PRESET_NONE, PRESET_COMFORT, PRESET_HOME, PRESET_ECO]

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
        self._attr_object_id = f"{self._prefix}_climate".lower()
        self._attr_current_option = None
        self._device_info = device_info
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_current_temperature = None
        self._attr_target_temperature_comfort = None
        self._attr_target_temperature_slow = None
        self._attr_target_temperature_auto = None
        self._attr_target_temperature_vacation = None
        self._pending_target_temperature = None  # Optimistic value after a write, cleared on next poll
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
        # Clear optimistic pending temperature – actual device state is now available
        self._pending_target_temperature = None
        self._update_state()
        self.async_write_ha_state()

    @callback
    def _update_state(self):
        if self._prefix not in self._hub.data:
            return
            
        data = self._hub.data[self._prefix]
        if "L_roomtemp_act" in data:
            # Convert to float, handling both numeric and string values
            try:
                self._attr_current_temperature = float(get_api_value(data["L_roomtemp_act"], 0)) / 10
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid L_roomtemp_act value: %s", data["L_roomtemp_act"])
            
        if "temp_heat" in data:
            # Base comfort temperature without override
            try:
                self._attr_target_temperature_comfort = float(get_api_value(data["temp_heat"], 0)) / 10
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid temp_heat value: %s", data["temp_heat"])
            
        if "temp_setback" in data:
            try:
                self._attr_target_temperature_slow = float(get_api_value(data["temp_setback"], 0)) / 10
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid temp_setback value: %s", data["temp_setback"])
        
        if "temp_vacation" in data:
            try:
                self._attr_target_temperature_vacation = float(get_api_value(data["temp_vacation"], 0)) / 10
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid temp_vacation value: %s", data["temp_vacation"])
            
        if "L_roomtemp_set" in data:
            # L_roomtemp_set is the actual temperature the system is currently targeting
            # (accounts for time program, oekomode eco reduction, etc.)
            try:
                self._attr_target_temperature_auto = float(get_api_value(data["L_roomtemp_set"], 0)) / 10
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid L_roomtemp_set value: %s", data["L_roomtemp_set"])
            
        if "mode_auto" in data:
            try:
                # Convert to int, handling both numeric and string values
                mode_auto_val = int(get_api_value(data["mode_auto"], 1))
                if mode_auto_val == 2:
                    self._attr_hvac_mode = HVACMode.HEAT
                elif mode_auto_val == 3:
                    self._attr_hvac_mode = HVACMode.OFF
                elif mode_auto_val == 1:
                    self._attr_hvac_mode = HVACMode.AUTO
                elif mode_auto_val == 0:
                    self._attr_hvac_mode = HVACMode.OFF
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid mode_auto value: %s", data["mode_auto"])
        
        # Read oekomode for preset mode
        # Format: "0:Aus|1:Komfort (-0.5K)|2:Minimum (-1.0K)|3:Ökologisch (-1.5K)"
        # Note: Vacation mode is NOT controlled by oekomode - it's detected via L_state==128
        if "oekomode" in data:
            try:
                # Convert to int, handling both numeric and string values
                oekomode_val = int(get_api_value(data["oekomode"], 0))
                if oekomode_val == 0:
                    self._attr_preset_mode = PRESET_NONE  # Aus (no eco reduction)
                elif oekomode_val == 1:
                    self._attr_preset_mode = PRESET_COMFORT  # Komfort (-0.5K)
                elif oekomode_val == 2:
                    self._attr_preset_mode = PRESET_HOME  # Minimum (-1.0K)
                elif oekomode_val == 3:
                    self._attr_preset_mode = PRESET_ECO  # Ökologisch (-1.5K)
                else:
                    self._attr_preset_mode = PRESET_NONE
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid oekomode value: %s", data["oekomode"])

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
        """Return the actual target temperature.

        Returns an optimistic value immediately after a write so the UI does not
        appear to revert.  Once the next poll arrives, _api_data_updated clears
        the optimistic value and the live hub.data reading takes over.

        L_roomtemp_set is the temperature the system is currently targeting –
        it already accounts for the active time-program slot, oekomode eco
        reduction and any physical remote-panel offset.
        """
        # Return the optimistic value we set during the last write until the
        # next poll confirms the device's updated state.
        if self._pending_target_temperature is not None:
            return self._pending_target_temperature

        if self._prefix in self._hub.data:
            data = self._hub.data[self._prefix]
            if "L_roomtemp_set" in data:
                try:
                    return float(get_api_value(data["L_roomtemp_set"], 0)) / 10
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "Invalid L_roomtemp_set value in live read for %s",
                        self._prefix,
                    )
        # Fall back to cached value during initialisation or if hub data is absent
        return self._attr_target_temperature_auto
    
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

        _LOGGER.info("Setting temperature for %s in mode %s to %s", 
                    self._prefix, self._attr_hvac_mode, temperature)
        
        try:
            if self._attr_hvac_mode == HVACMode.OFF:
                temperature_int = int(round(temperature * 10))
                self._attr_target_temperature_slow = temperature
                _LOGGER.info("Sending setback temperature for %s: %s", self._prefix, temperature_int)
                await self.hass.async_add_executor_job(
                    self._hub.send_pellematic_data,
                    temperature_int,
                    self._prefix,
                    "temp_setback"
                )
            elif self._attr_hvac_mode in [HVACMode.HEAT, HVACMode.AUTO]:
                # The device's effective target is:
                #   L_roomtemp_set = temp_heat + L_comfort + remote_override
                #
                # We only compensate for L_comfort (autocomfort algorithm – stable,
                # device-managed):
                #   temp_heat = desired - L_comfort
                #
                # We deliberately do NOT compensate for remote_override because it
                # is a physical remote-panel offset (HK Fernbedienung) that the
                # device's time programs can reset at any time.  Compensating for a
                # snapshot value that changes seconds later would produce the wrong
                # result.  A non-zero remote_override is a user-controlled physical
                # override; HA should respect it rather than cancel it.
                l_comfort = 0.0
                if self._prefix in self._hub.data:
                    data = self._hub.data[self._prefix]
                    try:
                        l_comfort = float(get_api_value(data.get("L_comfort"), 0)) / 10
                    except (ValueError, TypeError):
                        l_comfort = 0.0
                    # Log a warning when remote_override is active so users can debug
                    try:
                        ro = float(get_api_value(data.get("remote_override"), 0)) / 10
                        if ro != 0.0:
                            _LOGGER.warning(
                                "remote_override is %.1f°C for %s – this shifts "
                                "L_roomtemp_set away from the desired target. "
                                "Set 'remote_override' (HK Fernbedienung / cf1 Télécommande) to 0 to disable it.",
                                ro, self._prefix,
                            )
                    except (ValueError, TypeError):
                        pass

                adjusted_temp_heat = temperature - l_comfort
                temperature_int = int(round(adjusted_temp_heat * 10))
                self._attr_target_temperature_comfort = adjusted_temp_heat
                self._attr_target_temperature_auto = temperature  # reflect the desired L_roomtemp_set
                _LOGGER.info(
                    "Offset-corrected temp_heat for %s: desired=%.1f, "
                    "L_comfort=%.1f → temp_heat=%.1f (int=%d)",
                    self._prefix, temperature, l_comfort,
                    adjusted_temp_heat, temperature_int,
                )
                _LOGGER.info("Sending heat temperature for %s: %s", self._prefix, temperature_int)
                await self.hass.async_add_executor_job(
                    self._hub.send_pellematic_data,
                    temperature_int,
                    self._prefix,
                    "temp_heat"
                )
            # Optimistically reflect the new value in the UI immediately.
            # _api_data_updated will clear this once the next poll confirms the
            # device's actual state.
            self._pending_target_temperature = temperature
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
        """Set new preset mode."""
        if preset_mode not in self._attr_preset_modes:
            _LOGGER.error("Invalid preset mode: %s", preset_mode)
            return
        
        try:
            # Map Home Assistant preset to oekomode value
            # Format: "0:Aus|1:Komfort (-0.5K)|2:Minimum (-1.0K)|3:Ökologisch (-1.5K)"
            # Note: Vacation/Away is NOT controlled via oekomode
            oekomode_map = {
                PRESET_NONE: 0,      # Aus (no eco reduction)
                PRESET_COMFORT: 1,   # Komfort (-0.5K)
                PRESET_HOME: 2,      # Minimum (-1.0K)
                PRESET_ECO: 3,       # Ökologisch (-1.5K)
            }
            
            if preset_mode not in oekomode_map:
                _LOGGER.error("Preset mode %s not in map", preset_mode)
                return
            
            oekomode_value = oekomode_map[preset_mode]
            
            # Send to API
            await self.hass.async_add_executor_job(
                self._hub.send_pellematic_data,
                oekomode_value,
                self._prefix,
                "oekomode"
            )
            
            # Update local state
            self._attr_preset_mode = preset_mode
            self.async_write_ha_state()
            
            _LOGGER.debug(
                "Set preset mode to %s (oekomode=%d) for %s",
                preset_mode,
                oekomode_value,
                self.entity_id
            )
            
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
