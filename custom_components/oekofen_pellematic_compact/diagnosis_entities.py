"""Entities of the diagnosis module (see diagnosis.py).

Unlike the discovered entities these are computed by the integration. Their
entity IDs are set explicitly and stay language-independent:

    sensor.<hub>_diagnosis                 overall status (enum) + findings
    binary_sensor.<hub>_diagnosis_problem  on from "cleaning_soon" upwards
    sensor.<hub>_last_message / _message_count
    sensor.<hub>_pe1_flue_gas_index, _ignition_time, _burner_starts_per_day,
           _burner_runtime_per_start, _full_load_hours_since_maintenance
    sensor.<hub>_wp1_compressor_starts_per_day, _compressor_runtime_per_cycle
    button.<hub>_pe1_maintenance_done
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.util import slugify

from .diagnosis import STATUS_OPTIONS, DiagnosisMonitor, is_problem, utc_iso


class _DiagnosisEntity:
    """Shared setup: naming, IDs, and updates driven by the hub."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, domain, hub_name, hub, device_info, monitor, component, kind) -> None:
        self._hub = hub
        self._monitor = monitor
        self._component = component
        key = f"{component}_{kind}" if component else kind
        self._entity_id_key = f"diagnosis_{key}"
        self._attr_unique_id = f"{hub_name.lower()}_diagnosis_{key}"
        self.entity_id = f"{domain}.{slugify(hub_name)}_{key}"
        self._attr_translation_key = kind
        if component:
            self._attr_translation_placeholders = {"number": re.sub(r"\D", "", component)}
        self._attr_device_info = device_info

    @property
    def _diagnosis(self):
        return self._monitor.diagnosis

    async def async_added_to_hass(self):
        self._hub.async_add_pellematic_sensor(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_pellematic_sensor(self.async_write_ha_state)


class DiagnosisSensor(_DiagnosisEntity, SensorEntity):
    """Overall diagnosis status with all findings as attributes."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS
    _attr_icon = "mdi:stethoscope"

    def __init__(self, hub_name, hub, device_info, monitor) -> None:
        super().__init__("sensor", hub_name, hub, device_info, monitor, None, "diagnosis")

    @property
    def native_value(self):
        return self._diagnosis.status

    @property
    def extra_state_attributes(self):
        findings = self._diagnosis.findings()
        return {
            "problem": is_problem(self._diagnosis.status),
            "summary": findings[0]["message"] if findings else None,
            "messages": [f["message"] for f in findings],
            "findings": findings,
        }


class DiagnosisProblemSensor(_DiagnosisEntity, BinarySensorEntity):
    """On while the diagnosis needs action (cleaning soon or worse)."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, hub_name, hub, device_info, monitor) -> None:
        super().__init__("binary_sensor", hub_name, hub, device_info, monitor, None, "diagnosis_problem")

    @property
    def is_on(self) -> bool:
        return is_problem(self._diagnosis.status)

    @property
    def extra_state_attributes(self):
        findings = [f for f in self._diagnosis.findings() if is_problem(f["status"])]
        return {"status": self._diagnosis.status, "messages": [f["message"] for f in findings]}


class DiagnosisValueSensor(_DiagnosisEntity, SensorEntity):
    """A figure computed by the diagnosis (index, rate, duration, counter)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hub_name,
        hub,
        device_info,
        monitor,
        component: Optional[str],
        kind: str,
        value: Callable[[Any], Any],
        attributes: Optional[Callable[[Any], dict]] = None,
        unit: Optional[str] = None,
        icon: Optional[str] = None,
        state_class: Optional[str] = SensorStateClass.MEASUREMENT,
        device_class: Optional[str] = None,
    ) -> None:
        super().__init__("sensor", hub_name, hub, device_info, monitor, component, kind)
        self._value = value
        self._attributes = attributes
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        if device_class:
            self._attr_device_class = device_class

    @property
    def native_value(self):
        return self._value(self._diagnosis)

    @property
    def extra_state_attributes(self):
        return self._attributes(self._diagnosis) if self._attributes else None


class MaintenanceDoneButton(_DiagnosisEntity, ButtonEntity):
    """Resets full-load hours and ignition reference after a cleaning."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:broom"

    def __init__(self, hub_name, hub, device_info, monitor, component) -> None:
        super().__init__("button", hub_name, hub, device_info, monitor, component, "maintenance_done")

    async def async_added_to_hass(self):
        """Buttons have no state to refresh."""

    async def async_will_remove_from_hass(self) -> None:
        """Nothing registered."""

    async def async_press(self) -> None:
        self._monitor.maintenance_done(self._component)
        self._hub.async_notify_listeners()


def _components(data: dict, prefix: str) -> list[tuple[str, dict]]:
    return [
        (name, values)
        for name, values in data.items()
        if re.fullmatch(rf"{prefix}\d+", name) and isinstance(values, dict)
    ]


def create_diagnosis_sensors(hub_name, hub, device_info, monitor: DiagnosisMonitor, data) -> list:
    args = (hub_name, hub, device_info, monitor)
    entities: list = [
        DiagnosisSensor(*args),
        DiagnosisValueSensor(
            *args, None, "last_message",
            value=lambda d: d.messages.last["text"][:255] if d.messages.last else None,
            attributes=lambda d: {
                "time": (d.messages.last or {}).get("time"),
                "code": (d.messages.last or {}).get("code"),
                "source": (d.messages.last or {}).get("source"),
                "active": [m["text"] for m in d.messages.active],
                "history": d.messages.history[:20],
            },
            icon="mdi:message-alert-outline", state_class=None,
        ),
        DiagnosisValueSensor(
            *args, None, "message_count",
            value=lambda d: d.messages.count,
            icon="mdi:counter", state_class=SensorStateClass.TOTAL_INCREASING,
        ),
    ]

    for name, pe in _components(data, "pe"):
        monitor.diagnosis.heater(name)
        heater = lambda d, n=name: d.heater(n)  # noqa: E731
        if "L_fluegas" in pe:
            entities.append(DiagnosisValueSensor(
                *args, name, "flue_gas_index",
                value=lambda d, h=heater: h(d).flue_gas_index,
                attributes=lambda d, h=heater: {
                    "baseline": round(h(d).baseline, 1) if h(d).baseline else None,
                    "current_at_full_load": round(h(d).recent, 1) if h(d).recent else None,
                    "learning_progress": h(d).learn_progress,
                },
                unit=PERCENTAGE, icon="mdi:fan-chevron-up",
            ))
        if "L_state" in pe:
            entities.append(DiagnosisValueSensor(
                *args, name, "ignition_time",
                value=lambda d, h=heater: h(d).ignition_last,
                attributes=lambda d, h=heater: {
                    "average": h(d).ignition_avg,
                    "reference": h(d).ignition_reference,
                    "ignitions": h(d).ignition_count,
                    "failed_last_7_days": h(d).failed_ignitions(),
                },
                unit=UnitOfTime.MINUTES, icon="mdi:fire", device_class=SensorDeviceClass.DURATION,
            ))
        if "L_starts" in pe and "L_runtime" in pe:
            entities.append(DiagnosisValueSensor(
                *args, name, "burner_starts_per_day",
                value=lambda d, h=heater: h(d).starts_per_day,
                unit="starts/d", icon="mdi:counter",
            ))
            entities.append(DiagnosisValueSensor(
                *args, name, "burner_runtime_per_start",
                value=lambda d, h=heater: h(d).runtime_per_start,
                unit=UnitOfTime.MINUTES, icon="mdi:timer-outline",
                device_class=SensorDeviceClass.DURATION,
            ))
        entities.append(DiagnosisValueSensor(
            *args, name, "full_load_hours_since_maintenance",
            value=lambda d, h=heater: h(d).full_load_hours,
            attributes=lambda d, h=heater: {
                "since": utc_iso(h(d).maintenance_since),
                "days": h(d).maintenance_days,
            },
            unit=UnitOfTime.HOURS, icon="mdi:wrench-clock",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ))

    for name, wp in _components(data, "wp"):
        monitor.diagnosis.heat_pump(name)
        pump = lambda d, n=name: d.heat_pump(n)  # noqa: E731
        if "L_activation_count" in wp:
            entities.append(DiagnosisValueSensor(
                *args, name, "compressor_starts_per_day",
                value=lambda d, p=pump: p(d).starts_per_day,
                attributes=lambda d: {"experimental": True},
                unit="starts/d", icon="mdi:counter",
            ))
        if "L_compressor_act" in wp:
            entities.append(DiagnosisValueSensor(
                *args, name, "compressor_runtime_per_cycle",
                value=lambda d, p=pump: p(d).cycle_avg,
                attributes=lambda d: {"experimental": True},
                unit=UnitOfTime.MINUTES, icon="mdi:timer-outline",
                device_class=SensorDeviceClass.DURATION,
            ))
    return entities


def create_diagnosis_binary_sensors(hub_name, hub, device_info, monitor) -> list:
    return [DiagnosisProblemSensor(hub_name, hub, device_info, monitor)]


def create_diagnosis_buttons(hub_name, hub, device_info, monitor, data) -> list:
    return [
        MaintenanceDoneButton(hub_name, hub, device_info, monitor, name)
        for name, _ in _components(data, "pe")
    ]
