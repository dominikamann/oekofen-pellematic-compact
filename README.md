# Ökofen Pellematic Compact Integration for Home Assistant

Home Assistant integration `oekofen-pellematic-compact` is designed for Ökofen Pellematic Compact Heaters with enabled TCP/JSON-Interface.
It communicates locally with the heater. This is not an official integration by Ökofen.

![grafik](https://user-images.githubusercontent.com/29973737/211399791-75865ef4-72be-4601-9c34-764a5f4198a2.png)

# Installation

Copy the content of the 'custom_components' folder to your home-assistant folder 'config/custom_components' or install through HACS.
After reboot of Home-Assistant, this integration can be configured through the integration setup UI

![grafik](https://user-images.githubusercontent.com/29973737/211389542-0800d1cf-6df9-45d4-8607-5f90689a8628.png)


# Enable JSON-Interface on your Ökofen Pellematic Compact

Go to your Ökofen Pellematic Compact 
  -> Touchscreen -> Open General Settings -> Network Settings 
    -> Scroll down -> Activate JSON Interface 
 
 Use the provide URL as HOST in Component-Configuration (http://[ip]:[port]/[password]/all)
