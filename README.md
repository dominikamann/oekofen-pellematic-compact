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
- 🩺 **Diagnosis module** - Detects fouling, due maintenance, ignition problems, short cycling and more before the boiler fails, with ready-to-use entities and events for automations - see [Diagnosis module](#-diagnosis-module-know-before-your-heater-breaks)
- ✨ **Do you want to get more out of this integration and your heater?** ~90 extra values (heating curve, burner settings, ash level, ...) with no firmware change - check [Discussion #194](https://github.com/dominikamann/oekofen-pellematic-compact/discussions/194)

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

## Want more values? Heating curve, burner settings, ash level

The standard JSON interface leaves a lot out: the heating curve and heating limits, the
burner hysteresis and minimum runtimes, the ash box level, and more. It turns out the
Pelletronic Touch can expose them - a `json.properties` file on a USB stick in the Touch
adds about **90 additional values** to `/all?`, and no firmware change is needed.

Since v4 builds all entities from the API, the extra values appear in Home Assistant after
a reload of the integration - no changes to this integration required.

➡️ **[How to set it up: Discussion #194](https://github.com/dominikamann/oekofen-pellematic-compact/discussions/194)** (thanks to @zakx for working this out
and sharing the file!)

Two things to keep in mind: use **read-only `L_` keys only** - a key without the `L_` prefix
becomes writable over the network, protected only by the short JSON password - and the file
is tested on Touch V4.02b, so check your own `/all?` output afterwards.

## 🩺 Diagnosis module: know before your heater breaks

Your boiler only reports a fault once it gives up. Long before that it starts working around
problems: it spins the flue-gas fan harder as the heat exchanger fouls, it starts twenty times a
day because the buffer settings are off, it heats with a wrong outside temperature because the
sensor sits in the sun. None of that shows up on the touch display.

The diagnosis module watches the values your heater already sends, compares them with learned
normal values and published reference values, and tells you **what is wrong, how urgent it is
and what to check**. Everything runs locally, needs no configuration and only uses the values your
firmware actually delivers.

> **Tested against reality.** Replayed against three winters of one installation's history, the
> module reported *Cleaning due soon* on 9 January 2025, a month before the boiler stopped with a
> fault on 11 February (it had to be taken apart and cleaned). It caught the next fouling on
> 27 December 2025, days before faults started on New Year's Eve, and raised no false alarm in
> three years.

### What it detects

| Check | How | Status when found |
|---|---|---|
| **Fouling / cleaning needed** | Flue-gas fan speed at full load against the learned normal value of your boiler: +15 % *cleaning soon*, +30 % *cleaning due* | `cleaning_soon`, `cleaning_due` |
| **Maintenance due** | Full-load hours since the last maintenance (Ökofen: 1800 h) or one year | `maintenance_due` |
| **Ignition problems** | 3 or more failed ignitions within 7 days | `warning` |
| **Slow ignition** | Ignition takes 50 % longer than the boiler's own reference (worn igniter, dirty burner plate) | `notice` |
| **Short cycling** | Burner starts per day and minutes per start (7-day average). Reference: 1-3 starts a day, about an hour or more per start. Notice from >10 starts or <60 min, inefficient from >15 starts or <30 min | `notice`, `inefficient` |
| **Flow temperature not reached** | A heating circuit stays more than 5 K below its set point for 4 hours with the pump running (mixer, pump, boiler) | `warning` |
| **Outside sensor in the sun** | Readings above 45 °C or jumps of more than 6 K within an hour, on 3 days within a month | `notice` |
| **Heat pump cycling** *(experimental)* | Compressor starts per day and minutes per run. Reference: Fraunhofer field test, 90 % of systems below ~15 starts a day; runs under 6-10 min cost efficiency | `notice`, `inefficient` |
| **Boiler messages and faults** | Every message (`error_1` ... `error_5`) and every fault state is logged permanently | `warning`, `fault` |

Checks whose values your firmware does not send are skipped silently.

### Entities

| Entity | Purpose |
|---|---|
| `sensor.<name>_diagnosis` | **The one to use.** Overall status: `ok`, `learning`, `notice`, `inefficient`, `cleaning_soon`, `maintenance_due`, `cleaning_due`, `warning`, `fault` (translated in the UI). Attributes: `summary` (most important finding as a sentence), `messages`, `findings`, `problem` |
| `binary_sensor.<name>_diagnosis_problem` | `on` when you should act (`cleaning_soon` or worse). Perfect for notifications and dashboard badges |
| `sensor.<name>_last_message` / `_message_count` | Permanent log of boiler messages with time, code and the last 20 entries, survives restarts and the recorder purge |
| `sensor.<name>_pe1_flue_gas_index` | Flue-gas fan at full load in % of normal (100 % = clean) |
| `sensor.<name>_pe1_burner_starts_per_day` / `_burner_runtime_per_start` | Cycling figures, 7-day average |
| `sensor.<name>_pe1_ignition_time` | Last ignition in minutes; average, reference and failed ignitions as attributes |
| `sensor.<name>_pe1_full_load_hours_since_maintenance` | Counts towards the next maintenance |
| `button.<name>_pe1_maintenance_done` | **Press it after a cleaning or service.** Resets the maintenance counter and clears a cleaning warning right away |
| `sensor.<name>_wp1_compressor_starts_per_day` / `_compressor_runtime_per_cycle` | Heat pump cycling (experimental) |

All numeric sensors keep long-term statistics, so you can follow the trend over years.

Each finding in the `findings` attribute looks like this:

```yaml
- code: cleaning_soon          # stable, language-independent
  component: pe1               # pe1, hk1, wp1, system, error
  status: cleaning_soon
  value: 116.2
  message: Flue-gas fan at 116.2 % of normal - plan a cleaning   # in your HA language
```

### Automations

Get a push notification as soon as the heater needs attention:

```yaml
alias: Heater needs attention
triggers:
  - trigger: state
    entity_id: binary_sensor.pellematic_diagnosis_problem
    to: "on"
actions:
  - action: notify.notify
    data:
      title: Heating
      message: "{{ state_attr('sensor.pellematic_diagnosis', 'summary') }}"
```

React to individual findings, also the mild ones, with the event
`oekofen_pellematic_compact_finding`. It fires once when a finding appears (`active: true`) and once
when it clears (`active: false`), with `hub`, `component`, `code`, `status`, `value` and `message`:

```yaml
alias: Heater finding
triggers:
  - trigger: event
    event_type: oekofen_pellematic_compact_finding
    event_data:
      active: true
conditions:
  - condition: template
    value_template: "{{ trigger.event.data.code in ['cleaning_due', 'ignition_failures', 'flow_temperature_low'] }}"
actions:
  - action: notify.notify
    data:
      title: Heating
      message: "{{ trigger.event.data.message }}"
```

Every new boiler message fires `oekofen_pellematic_compact_message` (`hub`, `time`, `text`, `code`,
`source`), for example to log it or forward it to your installer:

```yaml
triggers:
  - trigger: event
    event_type: oekofen_pellematic_compact_message
actions:
  - action: notify.notify
    data:
      message: "{{ trigger.event.data.text }}"
```

Show the diagnosis on a dashboard:

```yaml
type: markdown
content: >
  **{{ state_translated('sensor.pellematic_diagnosis') }}**
  {% for m in state_attr('sensor.pellematic_diagnosis', 'messages') or [] %}
  - {{ m }}
  {% endfor %}
```

### Good to know

- **Learning:** the normal flue-gas fan speed is learned during the first 20 hours of full-load
  operation; until then the status is `learning`. In winter that takes a few days. The value adapts
  slowly to seasonal drift but never to a fouling boiler.
- **Maintenance counter:** counting starts when you install this version. Press
  *Maintenance done* after your next service so it runs from there.
- **Heat pumps:** the heat pump checks are marked experimental. They are built on reference values
  and test data from a few installations; feedback and anonymized `/all?` responses are very welcome.
- The reference values come from Ökofen's operating manual, the Fraunhofer heat pump field test, the
  German heat pump association (BWP) and installer experience from heizungsforum.de and Paradigma.

## Password or url change

If you upgrade your Ökofen Pellematic firmawre or change your password, you can simply change it in the homessistant configuration by : 
- connecting via ssh to your homeassistant : `ssh root@homeassistant`
- edit your configuration via : `vi /root/config/.storage/core.config_entries`
- search for pellematic configuration and change the url in the "host" key of pellematic configuration
- restart your homeassistant core

OR
 
![401221389-5b7e7316-5a60-4428-93fd-7f5761fa9ed7](https://github.com/user-attachments/assets/7e84f405-fed4-425f-aa96-9504b01bd6ce)

## Entity names and language

Entity names combine a **component prefix** (e.g. "Heating Circuit", "Hot Water") with the
field label reported by the boiler's API. The prefix is localized to your Home Assistant UI
language (English, German and French are shipped); the field label comes from the boiler in
its own configured language. If you change the Home Assistant language, reload the
integration entry for the prefixes to update. Entity IDs never change — only display names.

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

---

<p align="center">Proudly provided by <a href="https://amannlabs.eu">amannlabs.eu</a></p>
