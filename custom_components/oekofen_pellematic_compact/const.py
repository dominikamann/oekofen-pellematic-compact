"""Constants for the Ökofen Pellematic Compact integration."""

from homeassistant.const import (
    UnitOfTime,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfMass,
    UnitOfPower,
    UnitOfEnergy,
)

DOMAIN = "oekofen_pellematic_compact"
DEFAULT_NAME = "Pellematic"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_NUM_OF_HEATING_CIRCUIT = 1
DEFAULT_NUM_OF_HOT_WATER = 1
DEFAULT_NUM_OF_PELLEMATIC_HEATER = 1
CONF_SOLAR_CIRCUIT = "solar_circuit"
CONF_CIRCULATOR = "circulator"
CONF_SMART_PV = "smart_pv"
CONF_STIRLING = "stirling"
CONF_NUM_OF_HEATING_CIRCUIT = "num_of_heating_circuits"
CONF_NUM_OF_PELLEMATIC_HEATER = "num_of_pellematic_heaters"
CONF_NUM_OF_HOT_WATER = "num_of_hot_water"
DEFAULT_HOST = "http://[YOU_IP]:4321/[YOUR_PASSWORD]/all"
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
        "System Errors",
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

STIRLING_SENSOR_TYPES = {
    "L_temp_1": [
        "Stirling Engine Temperature 1",
        "L_temp_1",
        UnitOfPower.CELSIUS,
        None,
    ],
    "L_temp_2": [
        "Stirling Engine Temperature 2",
        "L_temp_2",
        UnitOfPower.CELSIUS,
        None,
    ],
    "L_temp_diff": [
        "Stirling Engine Temperature Diff",
        "L_temp_diff",
        UnitOfPower.CELSIUS,
        None,
    ],
    "L_temp_flow": [
        "Stirling Engine Temperature Flow",
        "L_temp_flow",
        UnitOfPower.CELSIUS,
        None,
    ],
    "L_temp_ret": [
        "Stirling Engine Temperature Ret",
        "L_temp_ret",
        UnitOfPower.CELSIUS,
        None,
    ],
    "L_temp_amb": [
        "Stirling Engine Temperature Ambient",
        "L_temp_amb",
        UnitOfPower.CELSIUS,
        None,
    ],
    "L_flow": [
        "Stirling Engine Flow",
        "L_flow",
        None,
        "mdi:numeric",
    ],
    "L_voltage": [
        "Stirling Engine Voltage",
        "L_voltage",
        None,
        "mdi:numeric",
    ],
    "L_current": [
        "Stirling Engine Current",
        "L_current",
        None,
        "mdi:numeric",
    ],
    "L_frequency": [
        "Stirling Engine Frequency",
        "L_frequency",
        None,
        "mdi:numeric",
    ],
    "L_phase": [
        "Stirling Engine Phase",
        "L_phase",
        None,
        "mdi:numeric",
    ],
    "L_power": [
        "Stirling Engine Power",
        "L_power",
        UnitOfPower.WATT,
        None,
    ],
    "L_power_totals": [
        "Stirling Engine Power Totals",
        "L_power_totals",
        None,
        "mdi:numeric",
    ],
    "L_power_today": [
        "Stirling Engine Power Today",
        "L_power_today",
        None,
        "mdi:numeric",
    ],
    "L_power_yesterday": [
        "Stirling Engine Power Yesterday",
        "L_power_yesterday",
        None,
        "mdi:numeric",
    ],
    "L_source": [
        "Stirling Engine Source",
        "L_source",
        None,
        "mdi:numeric",
    ],
    "L_st_req": [
        "Stirling Engine St req",
        "L_st_req",
        None,
        "mdi:numeric",
    ],
    "L_state": [
        "Stirling Engine State",
        "L_state",
        None,
        "mdi:numeric",
    ],
    "L_runtime": [
        "Stirling Engine Runtime",
        "L_runtime",
        UnitOfTime.HOURS,
        "mdi:timer",
    ],
    "L_start": [
        "Stirling Engine Start",
        "L_start",
        None,
        "mdi:numeric",
    ],
    "L_safety_shutdown": [
        "Stirling Engine Safety shutdown",
        "L_safety_shutdown",
        None,
        "mdi:numeric",
    ],
    "L_error": [
        "Stirling Engine Runtime",
        "L_error",
        None,
        "mdi:numeric",
    ],
}

POWER_SENSOR_TYPES = {
    "L_usage": [
        "Power - Usage",
        "L_usage",
        UnitOfPower.WATT,
        None,
    ],
    "L_pv_1": [
        "Power - PV 1",
        "L_pv_1",
        UnitOfPower.WATT,
        None,
    ],
    "L_pv_2": [
        "Power - PV 1",
        "L_pv_2",
        UnitOfPower.WATT,
        None,
    ],
    "L_from_grid": [
        "Power - From grid",
        "L_from_grid",
        UnitOfPower.WATT,
        None,
    ],
    "L_to_grid": [
        "Power - To grid",
        "L_to_grid",
        UnitOfPower.WATT,
        None,
    ],
    "L_p1": [
        "Power - P1",
        "L_p1",
        UnitOfPower.WATT,
        None,
    ],
    "L_p1": [
        "Power - P2",
        "L_p1",
        UnitOfPower.WATT,
        None,
    ],
    "L_p1": [
        "Power - P3",
        "L_p1",
        UnitOfPower.WATT,
        None,
    ],
    "L_batt_in": [
        "Power - Battery in",
        "L_batt_in",
        UnitOfPower.WATT,
        None,
    ],
    "L_batt_out": [
        "Power - Battery out",
        "L_batt_out",
        UnitOfPower.WATT,
        None,
    ],
    "L_batt_chg": [
        "Power - Battery chg",
        "L_batt_chg",
        UnitOfPower.WATT,
        None,
    ],
    "L_batt_chg": [
        "Power - Battery charged",
        "L_batt_chg",
        PERCENTAGE,
        None,
    ],
    "L_batt_enabled": [
        "Power - Battery enabled",
        "L_batt_enabled",
        None,
        "mdi:numeric",
    ],
    "L_pwr_out_per": [
        "Power - Precentage power out",
        "L_pwr_out_per",
        PERCENTAGE,
        None,
    ],
    "L_pwr_out": [
        "Power - Power out",
        "L_pwr_out",
        UnitOfPower.WATT,
        None,
    ],
    "L_power2car": [
        "Power - Power to car",
        "L_power2car",
        UnitOfPower.WATT,
        None,
    ],
    "L_today_total": [
        "Power - Power today total",
        "L_today_total",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_today_in": [
        "Power - Power today in",
        "L_today_in",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_today_out": [
        "Power - Power today out",
        "L_today_out",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_state": [
        "Power - State",
        "L_state",
        None,
        "mdi:numeric",
    ],
    "L_total": [
        "Power - Total",
        "L_total",
        None,
        "mdi:numeric",
    ],
    "L_yesterday": [
        "Power - Yesterday",
        "L_yesterday",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_total_tyristor": [
        "Power - Total tyristor",
        "L_total_tyristor",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_yesterday_tyristor": [
        "Power - Yesterday total tyristor",
        "L_yesterday_tyristor",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_total_car": [
        "Power - Total car",
        "L_total_car",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_yesterday_car": [
        "Power - Yesterday total car",
        "L_yesterday_car",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_total_pv": [
        "Power - Total pv",
        "L_total_pv",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_yesterday_pv": [
        "Power - Yesterday total pv",
        "L_yesterday_pv",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_today_batt_in": [
        "Power - Today battery in",
        "L_today_batt_in",
        None,
        "mdi:numeric",
    ],
    "L_today_batt_out": [
        "Power - Today battery out",
        "L_today_batt_out",
        None,
        "mdi:numeric",
    ],
    "L_yesterday_batt_in": [
        "Power - Yesterday battery in",
        "L_yesterday_batt_in",
        None,
        "mdi:numeric",
    ],
    "L_yesterday_batt_out": [
        "Power - Yesterday battery out",
        "L_yesterday_batt_out",
        None,
        "mdi:numeric",
    ],
    "L_output_mode": [
        "Power - Output mode",
        "L_output_mode",
        None,
        "mdi:numeric",
    ],
    "L_range": [
        "Power - Range",
        "L_range",
        UnitOfPower.WATT,
        None,
    ],
    "L_offset": [
        "Power - Offset",
        "L_offset",
        UnitOfPower.WATT,
        None,
    ],
    "L_total_in": [
        "Power - Total in",
        "L_total_in",
        None,
        "mdi:numeric",
    ],
    "L_total_out": [
        "Power - Total out",
        "L_total_out",
        None,
        "mdi:numeric",
    ],
    "L_yesterday_in": [
        "Power - Yesterday in",
        "L_yesterday_in",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_yesterday_out": [
        "Power - Yesterday out",
        "L_yesterday_out",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "offtemp": [
        "Power - Temperature off",
        "offtemp",
        UnitOfTemperature.CELSIUS,
        None,
    ],
}

PE_SENSOR_TYPES = {
    "L_storage_max": [
        "Pellet{0} Storage Level Max",
        "L_storage_max",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "L_storage_fill": [
        "Pellet{0} Storage Level",
        "L_storage_fill",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "storage_fill_yesterday": [
        "Pellet{0} Usage Yesterday",
        "storage_fill_yesterday",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "storage_fill_today": [
        "Pellet{0} Usage Today",
        "storage_fill_today",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "L_storage_popper": [
        "Pellet{0} Hopper Tank",
        "L_storage_popper",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "L_temp_act": [
        "Heater{0} Temperature",
        "L_temp_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_set": [
        "Heater{0} Temperature set",
        "L_temp_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_frt_temp_act": [
        "Heater{0} Combustion Chamber Temperature",
        "L_frt_temp_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_frt_temp_set": [
        "Heater{0} Combustion Chamber Temperature set",
        "L_frt_temp_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_frt_temp_end": [
        "Heater{0} Combustion Chamber Temperature end",
        "L_frt_temp_end",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_modulation": [
        "Heater{0} Modulation",
        "L_modulation",
        PERCENTAGE,
        "mdi:speedometer",
    ],
    "L_runtimeburner": [
        "Heater{0} Burner Insertion Time",
        "L_runtimeburner",
        UnitOfTime.MILLISECONDS,
        "mdi:history",
    ],
    "L_resttimeburner": [
        "Heater{0} Burner Break Time",
        "L_resttimeburner",
        UnitOfTime.MILLISECONDS,
        "mdi:history",
    ],
    "L_starts": [
        "Heater{0} Starts",
        "L_starts",
        None,
        "mdi:fire",
    ],
    "L_runtime": [
        "Heater{0} Runtime",
        "L_runtime",
        UnitOfTime.HOURS,
        "mdi:timer",
    ],
    "L_avg_runtime": [
        "Heater{0} Runtime AVG",
        "L_avg_runtime",
        UnitOfTime.MINUTES,
        "mdi:timer",
    ],
    "L_uw": [
        "Heater{0} UW Rotational speed",
        "L_uw",
        PERCENTAGE,
        "mdi:rotate-3d-variant",
    ],
    "L_uw_release": [
        "Heater{0} UW Release",
        "L_uw_release",
        None,
        "mdi:numeric",
    ],
    "L_uw_speed": [
        "Heater{0} UW Speed",
        "L_uw_speed",
        None,
        "mdi:speedometer",
    ],
    "L_fluegas": [
        "Heater{0} Flue Gas Rotational speed",
        "L_fluegas",
        PERCENTAGE,
        "mdi:rotate-3d-variant",
    ],
    "L_currentairflow": [
        "Heater{0} Airflow Current",
        "L_currentairflow",
        None,
        "mdi:numeric",
    ],
    "L_lowpressure": [
        "Heater{0} Pressure Low",
        "L_lowpressure",
        None,
        "mdi:numeric",
    ],
    "L_lowpressure_set": [
        "Heater{0} Pressure Low set",
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
        "Circulator Pump (obsolete)",
        "L_pummp",
        None,
        "mdi:numeric",
    ],
    "L_pump": [
        "Circulator Pump",
        "L_pump",
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

WW_SENSOR_TYPES = {
    "L_temp_set": [
        "Hot Water Circuit{0} Temperature set ",
        "L_temp_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_ontemp_act": [
        "Hot Water Circuit{0} Temperature on",
        "L_ontemp_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_offtemp_act": [
        "Hot Water Circuit{0} Temperature off",
        "L_offtemp_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "temp_min_set": [
        "Hot Water Circuit{0} Temperature minimum set",
        "temp_min_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "temp_max_set": [
        "Hot Water Circuit{0} Temperature maximum set",
        "temp_max_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "oekomode": [
        "Hot Water Circuit{0} Oekomode",
        "oekomode",
        None,
        "mdi:nature",
    ],
    "L_statetext": [
        "Hot Water Circuit{0} State",
        "L_statetext",
        None,
        "mdi:water-sync",
    ],
    "name": [
        "Hot Water Circuit{0} Name",
        "name",
        None,
        "mdi:water-sync",
    ],
}

WW_BINARY_SENSOR_TYPES = {
    "L_pump": [
        "Hot Water Circuit{0} Pump",
        "L_pump",
        None,
        "mdi:pump",
    ]
}
