"""Constants for the Ökofen Pellematic Compact integration."""

from homeassistant.const import (
    UnitOfTime,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfMass,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfElectricPotential,
    UnitOfVolumeFlowRate,
    UnitOfPressure
)
from homeassistant.components.number import NumberDeviceClass, NumberMode


DOMAIN = "oekofen_pellematic_compact"
DEFAULT_NAME = "Pellematic"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_NUM_OF_HEATING_CIRCUIT = 1
DEFAULT_NUM_OF_HOT_WATER = 1
DEFAULT_NUM_OF_PELLEMATIC_HEATER = 1
DEFAULT_NUM_OF_SMART_PV_SE = 0
DEFAULT_NUM_OF_SMART_PV_SK = 0
DEFAULT_NUM_OF_HEAT_PUMPS = 0
DEFAULT_NUM_OF_WIRELESS_SENSORS = 0
DEFAULT_NUM_OF_BUFFER_STORAGE = 1 # Important 1 not 0
CONF_SOLAR_CIRCUIT = "solar_circuit"
CONF_CIRCULATOR = "circulator"
CONF_SMART_PV = "smart_pv"
CONF_STIRLING = "stirling"
CONF_CHARSET = "charset"
CONF_NUM_OF_HEATING_CIRCUIT = "num_of_heating_circuits"
CONF_NUM_OF_PELLEMATIC_HEATER = "num_of_pellematic_heaters"
CONF_NUM_OF_SMART_PV_SE = "num_of_smart_pv_se_count"
CONF_NUM_OF_HEAT_PUMPS = "num_of_heat_pumps_count"
CONF_NUM_OF_SMART_PV_SK = "num_of_smart_pv_sk_count"
CONF_NUM_OF_HOT_WATER = "num_of_hot_water"
CONF_NUM_OF_WIRELESS_SENSORS = "num_of_wireless_sensors"
CONF_NUM_OF_BUFFER_STORAGE = "num_of_buffer_storage"
DEFAULT_HOST = "http://[YOU_IP]:4321/[YOUR_PASSWORD]/all"
DEFAULT_CHARSET = "iso-8859-1"
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
    "L_existing_boiler": [
        "Existing Boiler Temperature",
        "L_existing_boiler",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "mode": [
        "Operating mode",
        "mode",
        None,
        "mdi:numeric",
    ],
}

SYSTEM_SELECT_TYPES = {
    "mode": [
        "Operating mode",
        "mode",
        "mode",
        ["0_off","1_auto","2_hotwater"]
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

WIRELESS_SENSOR_TYPES = {
    "L_wireless_temp": [
        "Wireless Sensor {0} Temperature",
        "L_wireless_temp",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_wireless_hum": [
        "Wireless Sensor {0} Humidity",
        "L_wireless_hum",
        PERCENTAGE,
        "mdi:water-percent",
    ],
    "L_wireless_batt": [
        "Wireless Sensor {0} Battery",
        "L_wireless_batt",
        PERCENTAGE,
        "mdi:water-percent",
    ],
    "L_wireless_name": [
        "Wireless Sensor {0} Name",
        "L_wireless_name",
        None,
        None,
    ],
    "L_wireless_id": [
        "Wireless Sensor {0} Id",
        "L_wireless_id",
        None,
        "mdi:numeric",
    ],
}

STIRLING_SENSOR_TYPES = {
    "L_temp_1": [
        "Stirling Engine Temperature 1",
        "L_temp_1",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_2": [
        "Stirling Engine Temperature 2",
        "L_temp_2",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_diff": [
        "Stirling Engine Temperature Diff",
        "L_temp_diff",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_flow": [
        "Stirling Engine Temperature Flow",
        "L_temp_flow",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_ret": [
        "Stirling Engine Temperature Ret",
        "L_temp_ret",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_amb": [
        "Stirling Engine Temperature Ambient",
        "L_temp_amb",
        UnitOfTemperature.CELSIUS,
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
        UnitOfElectricPotential.VOLT,
        None,
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
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_power_today": [
        "Stirling Engine Power Today",
        "L_power_today",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
    ],
    "L_power_yesterday": [
        "Stirling Engine Power Yesterday",
        "L_power_yesterday",
        UnitOfEnergy.KILO_WATT_HOUR,
        None,
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
    "L_pellets_yesterday": [
        "Pellet{0} Usage Yesterday (new)",
        "L_pellets_yesterday",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "storage_fill_today": [
        "Pellet{0} Usage Today",
        "storage_fill_today",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "L_pellets_today": [
        "Pellet{0} Usage Today (new)",
        "L_pellets_today",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "L_storage_popper": [
        "Pellet{0} Hopper Tank",
        "L_storage_popper",
        UnitOfMass.KILOGRAMS,
        None,
    ],
    "L_storage_hopper": [
        "Pellet{0} Hopper Tank (new)",
        "L_storage_hopper",
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
    "L_state": [
        "Pellematic State Int",
        "L_state",
        None,
        "mdi:fire-circle",
    ],
}

PE_SELECT_TYPES = {
    "mode": [
        "Pellematic{0} Mode",
        "mode",
        "mode",
        ["0_off","1_auto","2_force"]
    ],
}

SE1_SENSOR_TYPES = {
    "L_flow_temp": [
        "Solar{0} Gain Flow Temperature",
        "L_flow_temp",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_ret_temp": [
        "Solar{0} Gain Return Temperature",
        "L_ret_temp",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_counter": [
        "Solar{0} Gain Counter",
        "L_counter",
        None,
        "mdi:solar-power-variant",
    ],
    "L_total": [
        "Solar{0} Gain Total",
        "L_total",
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:solar-power-variant",
    ],
    "L_day": [
        "Solar{0} Gain Today",
        "L_day",
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:solar-power-variant",
    ],
    "L_yesterday": [
        "Solar Gain{0} Yesterday",
        "L_yesterday",
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:solar-power-variant",
    ],
    "L_pwr": [
        "Solar Gain{0} Current",
        "L_pwr",
        UnitOfPower.KILO_WATT,
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
    "time_prg": [
        "Time program",
        "time_prg",
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
        "Solar Thermal{0} Collector Temperature",
        "L_koll_temp",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_spu": [
        "Solar Thermal{0} Buffer Storage Temperature lower area",
        "L_spu",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "spu_max": [
        "Solar Thermal{0} Buffer Storage Temperature Max",
        "spu_max",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_statetext": [
        "Solar Thermal{0} Collector Circuit State",
        "L_statetext",
        None,
        "mdi:solar-power-variant",
    ],
    "name": [
        "Solar Thermal{0} Collector Circuit Name",
        "name",
        None,
        "mdi:solar-power-variant",
    ],
    "L_pump": [
        "Solar Thermal{0} Collector Circuit Pump %",
        "L_pump#2",
        PERCENTAGE,
        "mdi:pump",
    ],
}

SK1_BINARY_SENSOR_TYPES = {
    "L_pump": [
        "Solar Thermal{0} Collector Circuit Pump",
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
    "L_state": [
        "Heating Circuit{0} State numeric",
        "L_state",
        None,
        "mdi:heating-coil",
    ],
    "name": [
        "Heating Circuit{0} Name",
        "name",
        None,
        "mdi:heating-coil",
    ],
    "mode_auto": [
        "Heating Circuit{0} Mode Auto",
        "mode_auto",
        None,
        "mdi:heating-coil",
    ],
    "time_prg": [
        "Time program",
        "time_prg",
        None,
        "mdi:numeric",
    ],
    "L_pump": [
        "Heating Circuit{0} Pump %",
        "L_pump#2",
        PERCENTAGE,
        "mdi:pump",
    ],
}

HK_SELECT_TYPES = {
    "mode_auto": [
        "Heating Circuit{0} Mode Auto",
        "mode_auto",
        "heater",
        ["0_off","1_auto","2_comfort","3_slow"]
    ],
}

HK_NUMBER_TYPES = {
    "temp_heat": [
        "Heating Circuit{0} Heat Temp",
        "temp_heat",
        NumberDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        10,
        40,
        0.5
    ],
    "temp_setback": [
        "Heating Circuit{0} Set Down Temp",
        "temp_setback",
        NumberDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        10,
        40,
        0.5
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
        "Buffer Storage{0} Temperature upper area",
        "L_tpo_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_tpo_set": [
        "Buffer Storage{0} Temperature upper area set",
        "L_tpo_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_tpm_act": [
        "Buffer Storage{0} Temperature middle area",
        "L_tpm_act",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_tpm_set": [
        "Buffer Storage{0} Temperature middle area set",
        "L_tpm_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "mintemp_off": [
        "Buffer Storage{0} Temperature minimum off",
        "mintemp_off",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "mintemp_on": [
        "Buffer Storage{0} Temperature minimum on",
        "mintemp_on",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "ext_mintemp_off": [
        "Buffer Storage{0} Ext. Temperature minimum off",
        "ext_mintemp_off",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "ext_mintemp_on": [
        "Buffer Storage{0} Ext. Temperature minimum on",
        "ext_mintemp_on",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_pump_release": [
        "Buffer Storage{0} Pump Release",
        "L_pump_release",
        None,
        "mdi:numeric",
    ],
    "L_statetext": [
        "Buffer Storage{0} State",
        "L_statetext",
        None,
        "mdi:storage-tank",
    ],
    "L_pump": [
        "Buffer Storage{0} Pump %",
        "L_pump#2",
        PERCENTAGE,
        "mdi:pump",
    ],
}

PU1_BINARY_SENSOR_TYPES = {
    "L_pump": [
        "Buffer Storage{0} Pump",
        "L_pump",
        None,
        "mdi:pump",
    ],
}

WP_SENSOR_TYPES = {
    "L_state": [
        "Heat Pump{0} State",
        "L_state",
        None,
        "mdi:heat-pump",
    ],
    "L_statetext": [
        "Heat Pump{0} State Text",
        "L_statetext",
        None,
        "mdi:heat-pump",
    ],
    "L_sg_ready": [
        "Heat Pump{0} SG Ready",
        "L_sg_ready",
        None,
        "mdi:heat-pump",
    ],
    "L_cop": [
        "Heat Pump{0} COP",
        "L_cop",
        None,
        "mdi:heat-pump",
    ],
    "L_uwp": [
        "Heat Pump{0} UWP Compressor",
        "L_uwp",
        PERCENTAGE,
        None,
    ],
    "L_fan": [
        "Heat Pump{0} Fan",
        "L_fan",
        PERCENTAGE,
        None,
    ],
    "L_highpressure": [
        "Heat Pump{0} High pressure",
        "L_highpressure",
        UnitOfPressure.BAR,
        "mdi:heat-pump",
    ],
    "L_lowpressure": [
        "Heat Pump{0} Low pressure",
        "L_lowpressure",
        UnitOfPressure.BAR,
        "mdi:heat-pump",
    ],
    "L_overheat_is": [
        "Heat Pump{0} Overheat is",
        "L_overheat_is",
        None,
        "mdi:heat-pump",
    ],
    "L_overheat_set": [
        "Heat Pump{0} Overheat set",
        "L_overheat_set",
        None,
        "mdi:heat-pump",
    ],
    "L_eev": [
        "Heat Pump{0} EEV",
        "L_eev",
        None,
        "mdi:heat-pump",
    ],
    "L_overheat": [
        "Heat Pump{0} Overheat",
        "L_overheat",
        None,
        "mdi:heat-pump",
    ],
    "L_compressor_in": [
         "Heat Pump{0} Compressor in",
        "L_compressor_in",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_compressor_out": [
        "Heat Pump{0} Compressor out",
        "L_compressor_out",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_src_in": [
        "Heat Pump{0} Fan in",
        "L_temp_src_in",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_src_out": [
        "Heat Pump{0} Fan out",
        "L_temp_src_out",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_flow_is": [
        "Heat Pump{0} Flow is",
        "L_temp_flow_is",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_flow_set": [
        "Heat Pump{0} Flow set",
        "L_temp_flow_set",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_return_is": [
        "Heat Pump{0} Flow return",
        "L_temp_return_is",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_flowrate": [
        "Heat Pump{0} Flow rate",
        "L_flowrate",
        UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        None,
    ], 
    "L_temp_vap": [
        "Heat Pump{0} Evaporation temperature",
        "L_temp_vap",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_condens": [
        "Heat Pump{0} Condensation  temperature",
        "L_temp_condens",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "L_temp_heater": [
        "Heat Pump{0} Heating power",
        "L_temp_heater",
        UnitOfPower.WATT,
        None,
    ],
    "L_temp_cooler": [
        "Heat Pump{0} Cooling power",
        "L_temp_cooler",
        UnitOfPower.WATT,
        None,
    ],
    "L_el_energy": [
        "Heat Pump{0} Electrical power",
        "L_el_energy",
        UnitOfPower.WATT,
        None,
    ],
    "L_total_runtime": [
        "Heat Pump{0} Runtime Total",
        "L_total_runtime",
        UnitOfTime.HOURS,
        "mdi:timer",
    ],
    "L_min_runtime": [
        "Heat Pump{0} Runtime Min",
        "L_min_runtime",
        UnitOfTime.HOURS,
        "mdi:timer",
    ],
    "L_max_runtime": [
        "Heat Pump{0} Runtime Max",
        "L_max_runtime",
        UnitOfTime.HOURS,
        "mdi:timer",
    ],
    "L_activation_count": [
        "Heat Pump{0} Activation counts",
        "L_activation_count",
        None,
        "mdi:numeric",
    ],
    "L_jaz_all": [
        "Heat Pump{0} JAZ",
        "L_jaz_all",
        None,
        "mdi:numeric",
    ],
    "L_jaz_heat": [
        "Heat Pump{0} JAZ Heat",
        "L_jaz_heat",
        None,
        "mdi:numeric",
    ],
    "L_jaz_cool": [
        "Heat Pump{0} JAZ Cool",
        "L_jaz_cool",
        None,
        "mdi:numeric",
    ],
    "L_az_all": [
        "Heat Pump{0} AZ",
        "L_az_all",
        None,
        "mdi:numeric",
    ],
    "L_az_heat": [
        "Heat Pump{0} AZ Heat",
        "L_az_heat",
        None,
        "mdi:numeric",
    ],
    "L_az_cool": [
        "Heat Pump{0} AZ Cool",
        "L_az_cool",
        None,
        "mdi:numeric",
    ],
    "mode": [
        "Heat Pump{0} Mode",
        "mode",
        None,
        "mdi:heat-pump",
    ],
    "ambient_mode": [
        "Heat Pump{0} Ambient mode",
        "ambient_mode",
        None,
        "mdi:heat-pump",
    ],
    "ambient_dhw_add_pwr": [
        "Heater{0} Ambient DHW add pwr",
        "ambient_dhw_add_pwr",
        PERCENTAGE,
        None,
    ],
    "ambient_pwr": [
        "Heater{0} Ambient pwr",
        "ambient_pwr",
        PERCENTAGE,
        None,
    ],
    "ambient_min_pwr_over": [
        "Heat Pump{0} Ambient min pwr over",
        "ambient_min_pwr_over",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "ambient_max_pwr_below": [
        "Heat Pump{0} Ambient max pwr below",
        "ambient_max_pwr_below",
        UnitOfTemperature.CELSIUS,
        None,
    ],
    "night_mode": [
        "Heat Pump{0} Night mode",
        "night_mode",
        None,
        "mdi:heat-pump",
    ],
    "heater": [
        "Heat Pump{0} Heating rod mode",
        "heater",
        None,
        "mdi:heat-pump",
    ]
}

WP_DATA_SENSOR_TYPES = {
    "L_jaz_all": [
        "Heat Pump Data{0} JAZ",
        "L_jaz_all",
        None,
        "mdi:numeric",
    ],
    "L_jaz_heat": [
        "Heat Pump Data{0} JAZ Heat",
        "L_jaz_heat",
        None,
        "mdi:numeric",
    ],
    "L_jaz_cool": [
        "Heat Pump Data{0} JAZ Cool",
        "L_jaz_cool",
        None,
        "mdi:numeric",
    ],
    "L_az_all": [
        "Heat Pump Data{0} AZ",
        "L_az_all",
        None,
        "mdi:numeric",
    ],
    "L_az_heat": [
        "Heat Pump Data{0} AZ Heat",
        "L_az_heat",
        None,
        "mdi:numeric",
    ],
    "L_az_cool": [
        "Heat Pump Data{0} AZ Cool",
        "L_az_cool",
        None,
        "mdi:numeric",
    ]
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
    "mode_auto": [
        "Hot Water Circuit{0} Mode Auto",
        "mode_auto",
        None,
        "mdi:water-sync",
    ],
    "L_pump": [
        "Hot Water Circuit{0} Pump %",
        "L_pump#2",
        None,
        "mdi:pump",
    ]
}

WW_SELECT_TYPES = {
    "mode_auto": [
        "Hot Water Circuit{0} Mode Auto",
        "mode_auto",
        "mode",
        ["0_off","1_auto","2_force"]
    ],
    "heat_once": [
        "Hot Water Circuit{0} Heat Once",
        "heat_once",
        "heat_once",
        ["0_off","1_on"]
    ],
}

WW_NUMBER_TYPES = {
    "temp_min_set": [
        "Hot Water Circuit{0} Min Temp",
        "temp_min_set",
        NumberDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        8,
        80,
        1
    ],
    "temp_max_set": [
        "Hot Water Circuit{0} Max Temp",
        "temp_max_set",
        NumberDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        8,
        80,
        1
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
