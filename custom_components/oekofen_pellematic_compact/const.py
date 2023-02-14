"""Constants for the Ökofen Pellematic Compact integration."""

from homeassistant.const import (
    UnitOfTime,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfMass,
)

DOMAIN = "oekofen_pellematic_compact"
DEFAULT_NAME = "pellematic"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_NUM_OF_HEATING_CIRCUIT = 1
CONF_SOLAR_CIRCUIT = "solar_circuit"
CONF_CIRCULATOR = "circulator"
CONF_NUM_OF_HEATING_CIRCUIT = "num_of_heating_circuits"
DEFAULT_HOST = "http://192.168.178.91:4321/8n2L/all"
CONF_SOLAREDGE_HUB = "solaredge_hub"
ATTR_STATUS_DESCRIPTION = "status_description"
ATTR_MANUFACTURER = "Ökofen"
ATTR_MODEL = "Pellematic Compact"

SYSTEM_SENSOR_TYPES = {
    "L_ambient": [
        "Outside Temperature",
        "L_ambient",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_errors": [
        "Errors",
        "L_errors",
        None,
        "mdi:alert-circle",
    ],
}

SYSTEM_BINARY_SENSOR_TYPES = {
    "L_usb_stick": [
        "USB Stick",
        "L_usb_stick",
        None,
        "mdi:usb-flash-drive",
    ],
}

PE1_SENSOR_TYPES = {
    "L_storage_max": [
        "Pellet Storage Level Max",
        "L_storage_max",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "L_storage_fill": [
        "Pellet Storage Level",
        "L_storage_fill",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "storage_fill_yesterday": [
        "Pellet Usage Yesterday",
        "storage_fill_yesterday",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "storage_fill_today": [
        "Pellet Usage Today",
        "storage_fill_today",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "L_storage_popper": [
        "Pellet Hopper Tank",
        "L_storage_popper",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "L_temp_act": [
        "Heater Temperature",
        "L_temp_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_set": [
        "Heater Temperature set",
        "L_temp_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_frt_temp_act": [
        "Heater Combustion Chamber Temperature",
        "L_frt_temp_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_frt_temp_set": [
        "Heater Combustion Chamber Temperature set",
        "L_frt_temp_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_frt_temp_end": [
        "Heater Combustion Chamber Temperature end",
        "L_frt_temp_end",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_modulation": [
        "Heater Modulation",
        "L_modulation",
        PERCENTAGE,
        "mdi:speedometer",
    ],
    "L_runtimeburner": [
        "Heater Burner Insertion Time",
        "L_runtimeburner",
        UnitOfTime.MILLISECONDS,
        "mdi:history",
    ],
    "L_resttimeburner": [
        "Heater Burner Break Time",
        "L_resttimeburner",
        UnitOfTime.MILLISECONDS,
        "mdi:history",
    ],
    "L_starts": [
        "Heater Starts",
        "L_starts",
        None,
        "mdi:fire",
    ],
    "L_runtime": [
        "Heater Runtime",
        "L_runtime",
        UnitOfTime.HOURS,
        "mdi:timer",
    ],
    "L_avg_runtime": [
        "Heater Runtime AVG",
        "L_avg_runtime",
        UnitOfTime.MINUTES,
        "mdi:timer",
    ],
    "L_uw": [
        "Heater UW Rotational speed",
        "L_uw",
        PERCENTAGE,
        "mdi:rotate-3d-variant",
    ],
    "L_uw_release": [
        "Heater UW Release",
        "L_uw_release",
        None,
        "mdi:numeric",
    ],
    "L_uw_speed": [
        "Heater UW Speed",
        "L_uw_speed",
        None,
        "mdi:speedometer",
    ],
    "L_fluegas": [
        "Heater Flue Gas Rotational speed",
        "L_fluegas",
        PERCENTAGE,
        "mdi:rotate-3d-variant",
    ],
    "L_currentairflow": [
        "Heater Airflow Current",
        "L_currentairflow",
        None,
        "mdi:numeric",
    ],
    "L_lowpressure": [
        "Heater Pressure Low",
        "L_lowpressure",
        None,
        "mdi:numeric",
    ],
    "L_lowpressure_set": [
        "Heater Pressure Low set",
        "L_lowpressure_set",
        None,
        "mdi:numeric",
    ],
    "L_statetext": ["Pellematic State", "L_statetext", None, "mdi:fire-circle"],
}

SE1_SENSOR_TYPES = {
    "L_flow_temp": [
        "Solar Gain Flow Temperature",
        "L_flow_temp",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_ret_temp": [
        "Solar Gain Return Temperature",
        "L_ret_temp",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_counter": [
        "Solar Gain Counter",
        "L_counter",
        None,
        "mdi:solar-power-variant",
    ],
    "L_total": [
        "Solar Gain Total",
        "L_total",
        None,
        "mdi:solar-power-variant",
    ],
    "L_day": [
        "Solar Gain Today",
        "L_day",
        None,
        "mdi:solar-power-variant",
    ],
    "L_yesterday": [
        "Solar Gain Yesterday",
        "L_yesterday",
        None,
        "mdi:solar-power-variant",
    ],
}

CIRC1_SENSOR_TYPES = {
    "L_ret_temp": [
        "Circulator Return Temperature",
        "L_ret_temp",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_release_temp": [
        "Circulator Release Temperature",
        "L_release_temp",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "pump_release": [
        "Circulator Pump Release Temperature",
        "pump_release",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "return_set": [
        "Circulator Return Temperature set",
        "return_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_pummp": [
        "Circulator Pump",
        "L_pummp",
        None,
        "mdi:numeric",
    ],
    "mode": [
        "Circulator Mode",
        "mode",
        None,
        "mdi:numeric",
    ],
    "name": [
        "Circulator Name",
        "name",
        None,
        "mdi:autorenew",
    ],   
}


SK1_SENSOR_TYPES = {
    "L_koll_temp": [
        "Solar Thermal Collector Temperature",
        "L_koll_temp",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_spu": [
        "Solar Thermal Buffer Storage Temperature lower area",
        "L_spu",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "spu_max": [
        "Solar Thermal Buffer Storage Temperature Max",
        "spu_max",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_statetext": [
        "Solar Thermal Collector Circuit State",
        "L_statetext",
        None,
        "mdi:solar-power-variant",
    ],
    "name": [
        "Solar Thermal Collector Circuit Name",
        "name",
        None,
        "mdi:solar-power-variant",
    ],
}

SK1_BINARY_SENSOR_TYPES = {
    "L_pump": [
        "Solar Thermal Collector Circuit Pump",
        "L_pump",
        None,
        "mdi:pump",
    ],
}

HK_SENSOR_TYPES = {
    "L_roomtemp_act": [
        "Heating Circuit{0} Room Temperature",
        "L_roomtemp_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_roomtemp_set": [
        "Heating Circuit{0} Room Temperature set",
        "L_roomtemp_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_flowtemp_act": [
        "Heating Circuit{0} Flow Temperature",
        "L_flowtemp_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_flowtemp_set": [
        "Heating Circuit{0} Flow Temperature set",
        "L_flowtemp_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "temp_setback": [
        "Heating Circuit{0} Temperature Setback",
        "temp_setback",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "temp_heat": [
        "Heating Circuit{0} Flow Temperature Heat",
        "temp_heat",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "temp_vacation": [
        "Heating Circuit{0} Flow Temperature Vacation",
        "temp_vacation",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "oekomode": [
        "Heating Circuit{0} Oekomode",
        "oekomode",
        None,
        "mdi:nature",
    ],
    "L_statetext": [
        "Heating Circuit{0} State",
        "L_statetext",
        None,
        "mdi:heating-coil",
    ],
    "name": [
        "Heating Circuit{0} Name",
        "name",
        None,
        "mdi:heating-coil",
    ],
}

HK_BINARY_SENSOR_TYPES = {
    "L_pump": [
        "Heating Circuit{0} Pump",
        "L_pump",
        None,
        "mdi:pump",
    ],
}

PU1_SENSOR_TYPES = {
    "L_tpo_act": [
        "Buffer Storage Temperature upper area",
        "L_tpo_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_tpo_set": [
        "Buffer Storage Temperature upper area set",
        "L_tpo_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_tpm_act": [
        "Buffer Storage Temperature middle area",
        "L_tpm_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_tpm_set": [
        "Buffer Storage Temperature middle area set",
        "L_tpm_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "mintemp_off": [
        "Buffer Storage Temperature minimum off",
        "mintemp_off",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "mintemp_on": [
        "Buffer Storage Temperature minimum on",
        "mintemp_on",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_pump_release": [
        "Buffer Storage Pump Release",
        "L_pump_release",
        None,
        "mdi:numeric",
    ],
    "L_statetext": [
        "Buffer Storage State",
        "L_statetext",
        None,
        "mdi:storage-tank",
    ],
}

PU1_BINARY_SENSOR_TYPES = {
    "L_pump": [
        "Buffer Storage Pump",
        "L_pump",
        None,
        "mdi:pump",
    ],
}

WW1_SENSOR_TYPES = {
    "L_temp_set": [
        "Hot Water Circuit Temperature set ",
        "L_temp_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_ontemp_act": [
        "Hot Water Circuit Temperature on",
        "L_ontemp_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_offtemp_act": [
        "Hot Water Circuit Temperature off",
        "L_offtemp_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "temp_min_set": [
        "Hot Water Circuit Temperature minimum set",
        "temp_min_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "temp_max_set": [
        "Hot Water Circuit Temperature maximum set",
        "temp_max_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "oekomode": [
        "Hot Water Circuit Oekomode",
        "oekomode",
        None,
        "mdi:nature",
    ],
    "L_statetext": [
        "Hot Water Circuit State",
        "L_statetext",
        None,
        "mdi:water-sync",
    ],
    "name": [
        "Hot Water Circuit Name",
        "name",
        None,
        "mdi:water-sync",
    ],
}

WW1_BINARY_SENSOR_TYPES = {
    "L_pump": [
        "Hot Water Circuit Pump",
        "L_pump",
        None,
        "mdi:pump",
    ]
}
