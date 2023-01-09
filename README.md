# Ökofen Pellematic Compact for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

Home Assistant integration `oekofen-pellematic-compact` is designed for Ökofen Pellematic Compact Heaters with enabled TCP/JSON-Interface.
It communicates locally with the Heater using HTTP/TCP.

![grafik](https://user-images.githubusercontent.com/29973737/211389282-c20125d7-c2d0-4177-9706-a069c22c5dd1.png)

# Installation

Copy contents of custom_components folder to your home-assistant config/custom_components folder or install through HACS.
After reboot of Home-Assistant, this integration can be configured through the integration setup UI

![grafik](https://user-images.githubusercontent.com/29973737/211389542-0800d1cf-6df9-45d4-8607-5f90689a8628.png)


# Enable JSON-Interface on your Ökofen Pellematic Compact

Go to your Ökofen Pellematic Compact 
  -> Touchscreen -> Open General Settings -> Network Settings 
    -> Scroll down -> Activate JSON Interface 
 
 Use the provide URL as HOST in Component-Configuration (http://[ip]:[port]/[password]/all)
