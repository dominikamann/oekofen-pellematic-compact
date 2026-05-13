# Ökofen Pellematic Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
![commit_activity](https://img.shields.io/github/commit-activity/y/dominikamann/oekofen-pellematic-compact?color=brightgreen&label=Commits&style=flat-square)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/dominikamann/oekofen-pellematic-compact?style=flat-square)
[![downloads](https://img.shields.io/github/downloads/dominikamann/oekofen-pellematic-compact/total)](https://github.com/dominikamann/oekofen-pellematic-compact/releases)
[![dominik support](https://img.shields.io/badge/support-me-ff5e5b?style=flat-square&logo=ko-fi)](https://github.com/sponsors/dominikamann)


Home Assistant integration `oekofen-pellematic-compact` is designed for Ökofen Pellematic Heaters with enabled TCP/JSON-Interface.
It communicates locally with the heater. This is not an official integration by Ökofen.

- 🚀 **Automatic entity discovery** - All sensors automatically detected from API
- 🌍 **Multilingual support** - Names in DE/FR/EN directly from your Ökofen system
- 🐛 **v4.2.10** - Stop flooding the HA log with "Value 00:00-00:00 could not be scaled with factor 1" on newer firmware with GreenMode schedule fields (#184)
- ⚠️ If your heater’s software version is 3.10 (or similarly old), do NOT install an integration version 4.0.0 or newer. Last working version for this old heater software is https://github.com/dominikamann/oekofen-pellematic-compact/releases/tag/v3.6.6. Update: It now also works in many cases with the latest version. Please try and report issues. Thank you.

![grafik](https://github.com/user-attachments/assets/dbc94d82-ca22-4264-8bf6-36b373ce910b)

![grafik](https://github.com/user-attachments/assets/2800924e-7eef-47db-b73c-383a5b483a47)

![grafik](https://github.com/user-attachments/assets/eba66675-940d-4799-b475-afbf0e70f34d)

## Installation

Copy the content of the 'custom_components' folder to your home-assistant folder 'config/custom_components' or install through HACS.
After reboot of Home-Assistant, this integration can be configured through the integration setup UI

Click here to install over HACS:
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dominikamann&repository=oekofen-pellematic-compact&category=integration)

![grafik](https://user-images.githubusercontent.com/29973737/211389542-0800d1cf-6df9-45d4-8607-5f90689a8628.png)

## Enable JSON-Interface on your Ökofen Pellematic

Go to your Ökofen Pellematic 
  -> Touchscreen -> Open General Settings -> Network Settings/"IP Config"
    -> Scroll down -> Activate JSON Interface
    
    IMPORTANT: Do not activate the compatibility mode. This mode is not supported/recommended.

 Use the provided URL as HOST in Component-Configuration (<http://[ip]:[port]/[password]/all>)

## Password or url change

If you upgrade your Ökofen Pellematic firmawre or change your password, you can simply change it in the homessistant configuration by : 
- connecting via ssh to your homeassistant : `ssh root@homeassistant`
- edit your configuration via : `vi /root/config/.storage/core.config_entries`
- search for pellematic configuration and change the url in the "host" key of pellematic configuration
- restart your homeassistant core

OR
 
![401221389-5b7e7316-5a60-4428-93fd-7f5761fa9ed7](https://github.com/user-attachments/assets/7e84f405-fed4-425f-aa96-9504b01bd6ce)

## Tips: derived sensors (e.g. gas-equivalent energy)

The integration exposes the raw sensors needed to derive your own values — for example pellet consumption in kg (`sensor.pellematic_pe1_storage_fill_today`, `sensor.pellematic_pe1_storage_fill_yesterday`, `sensor.pellematic_pe1_l_storage_fill`). Anything that's a fixed-constant calculation on top of those (gas-equivalent volume, CO₂ avoided, cost per day, ...) is best done as a Home Assistant **Template Helper** so you can pick the constants that match your pellet quality and local gas tariff.

### Converting kg of pellets to m³ of natural gas (equivalent energy)

1. Go to **Settings → Devices & services → Helpers → Create helper → Template → Template a sensor**.
2. Use the formula below. Adjust the two constants to match your situation:
   - Pellet heating value: ~4.8 kWh/kg for ENplus A1, ~4.6 kWh/kg for ENplus A2
   - Natural gas heating value (Hi): ~10.0 kWh/m³ in most of Europe (check your local supplier)

```jinja
{% set kg = states('sensor.pellematic_pe1_storage_fill_today') | float(0) %}
{% set pellet_kwh_per_kg = 4.8 %}
{% set gas_kwh_per_m3   = 10.0 %}
{{ (kg * pellet_kwh_per_kg / gas_kwh_per_m3) | round(2) }}
```

Set unit of measurement to `m³` and device class to `Gas` so the result shows up in the HA Energy dashboard.

> Why not ship this as a built-in entity? Pellet energy density varies by grade and natural-gas Wobbe Index varies by country — hard-coding the constants would be wrong for many users. The helper keeps the choice in your hands.


