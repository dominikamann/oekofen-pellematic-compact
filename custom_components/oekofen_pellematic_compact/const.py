"""Constants for the Ökofen Pellematic Compact integration."""

from homeassistant.const import (
    UnitOfTemperature,
    UnitOfMass,
)

DOMAIN = "oekofen_pellematic_compact"
DEFAULT_NAME = "pellematic"
DEFAULT_SCAN_INTERVAL = 30
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
        "Heater Flame Chamber Temperature",
        "L_frt_temp_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_frt_temp_set": [
        "Heater Flame Chamber Temperature set",
        "L_frt_temp_set",
        UnitOfTemperature.CELSIUS,
        None,
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
        "mdi:numeric",
    ],
    "L_total": [
        "Solar Gain Total",
        "L_total",
        None,
        "mdi:numeric",
    ],
    "L_day": [
        "Solar Gain Today",
        "L_day",
        None,
        "mdi:numeric",
    ],
    "L_yesterday": [
        "Solar Gain Yesterday",
        "L_yesterday",
        None,
        "mdi:numeric",
    ],
}

SK1_SENSOR_TYPES = {
    "L_koll_temp": [
        "Solar Thermal Collector Circuit Temperature",
        "L_koll_temp",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_statetext": ["Solar Thermal Collector Circuit State", "L_statetext", None, "mdi:fire-circle"],
    "name": ["Solar Thermal Collector Circuit Name", "name", None, "mdi:fire-circle"],
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
    "L_statetext": ["Heating Circuit{0} State", "L_statetext", None, "mdi:fire-circle"],
    "name": ["Heating Circuit{0} Name", "name", None, "mdi:fire-circle"],
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
        "Buffer Storage Temperature lower area",
        "L_tpm_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_tpm_set": [
        "Buffer Storage Temperature lower area set",
        "L_tpm_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_statetext": ["Buffer Storage State", "L_statetext", None, "mdi:water-circle"],
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
    "L_statetext": ["Hot Water Circuit State", "L_statetext", None, "mdi:fire-circle"],
    "name": ["Hot Water Circuit Name", "name", None, "mdi:fire-circle"],
}

WW1_BINARY_SENSOR_TYPES = {
    "L_pump": [
        "Hot Water Circuit Pump",
        "L_pump",
        None,
        "mdi:pump",
    ]
}
