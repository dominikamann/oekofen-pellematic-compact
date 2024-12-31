# Ökofen Pellematic Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
![commit_activity](https://img.shields.io/github/commit-activity/y/dominikamann/oekofen-pellematic-compact?color=brightgreen&label=Commits&style=flat-square)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/dominikamann/oekofen-pellematic-compact?style=flat-square)
[![downloads](https://img.shields.io/github/downloads/dominikamann/oekofen-pellematic-compact/total)](https://github.com/dominikamann/oekofen-pellematic-compact/releases)
[![dominik support](https://img.shields.io/badge/support-me-ff5e5b?style=flat-square&logo=ko-fi)](https://github.com/sponsors/dominikamann)


Home Assistant integration `oekofen-pellematic-compact` is designed for Ökofen Pellematic Heaters with enabled TCP/JSON-Interface.
It communicates locally with the heater. This is not an official integration by Ökofen.

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
