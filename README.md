# Ökofen Pellematic Compact Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

Home Assistant integration `oekofen-pellematic-compact` is designed for Ökofen Pellematic Compact Heaters with enabled TCP/JSON-Interface.
It communicates locally with the heater. This is not an official integration by Ökofen.

![grafik](https://user-images.githubusercontent.com/29973737/214123527-3ae3e842-2f4e-49e0-b18f-e6c2fa4160a2.png)

![grafik](https://user-images.githubusercontent.com/29973737/214123458-af495562-fb5e-491e-843c-c9d7a52ac11a.png)

# Installation

Copy the content of the 'custom_components' folder to your home-assistant folder 'config/custom_components' or install through HACS.
After reboot of Home-Assistant, this integration can be configured through the integration setup UI

![grafik](https://user-images.githubusercontent.com/29973737/211389542-0800d1cf-6df9-45d4-8607-5f90689a8628.png)


# Enable JSON-Interface on your Ökofen Pellematic Compact

Go to your Ökofen Pellematic Compact 
  -> Touchscreen -> Open General Settings -> Network Settings 
    -> Scroll down -> Activate JSON Interface 
 
 Use the provide URL as HOST in Component-Configuration (http://[ip]:[port]/[password]/all)
