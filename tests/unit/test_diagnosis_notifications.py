"""Tests for the diagnosis findings shown as persistent notifications."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.oekofen_pellematic_compact.diagnosis import (
    MESSAGES,
    NO_MESSAGES,
    NOTIFICATION_TITLES,
    Diagnosis,
    DiagnosisMonitor,
    notification_for,
)

FAULTED = {"pe1": {"L_state": 11, "L_statetext": "Störung"}}
RUNNING = {"pe1": {"L_state": 4, "L_statetext": "Leistungsbrand"}}

CLEANING_SOON = {
    "component": "pe1",
    "code": "cleaning_soon",
    "status": "cleaning_soon",
    "value": 115.0,
    "message": "Saugzug bei 115.0 % des Normalwerts - Reinigung einplanen",
    "active": True,
}


def test_notification_for_active_finding():
    assert notification_for(CLEANING_SOON, "Pelletheizung", "de") == (
        "oekofen_pellematic_compact_pelletheizung_pe1_cleaning_soon",
        "Pelletheizung: Reinigung bald fällig",
        "Saugzug bei 115.0 % des Normalwerts - Reinigung einplanen",
    )


def test_notification_for_cleared_finding_is_none():
    cleared = {"component": "pe1", "code": "cleaning_soon", "active": False}
    assert notification_for(cleared, "Pelletheizung", "de") is None


def test_notification_for_unknown_language_falls_back_to_english():
    _, title, _ = notification_for(CLEANING_SOON, "Pelletheizung", "xx")
    assert title == "Pelletheizung: Cleaning due soon"


def test_notification_for_unknown_code_uses_code_as_label():
    change = dict(CLEANING_SOON, code="something_new")
    _, title, _ = notification_for(change, "Pelletheizung", "de")
    assert title == "Pelletheizung: something_new"


def test_notification_id_is_the_same_when_a_finding_reappears():
    later = dict(CLEANING_SOON, value=117.1, message="Saugzug bei 117.1 %")
    assert notification_for(later, "Pelletheizung", "de")[0] == notification_for(
        CLEANING_SOON, "Pelletheizung", "de"
    )[0]


@pytest.mark.parametrize("language", sorted(MESSAGES))
def test_every_finding_code_has_a_title(language):
    codes = set(MESSAGES["en"]) - {NO_MESSAGES}
    assert codes <= set(NOTIFICATION_TITLES[language])


def _monitor(notify=True, stored=None):
    hass = MagicMock()
    hass.config.language = "de"
    hub = MagicMock()
    with patch("homeassistant.helpers.storage.Store"):
        monitor = DiagnosisMonitor(hass, hub, "entry", "Pelletheizung", notify=notify)
    monitor.diagnosis = Diagnosis(stored, "de")
    monitor._save_soon = MagicMock()
    return monitor, hub


def _feed(monitor, hub, data):
    hub.data = data
    monitor._handle_update()


@patch("homeassistant.components.persistent_notification.async_create")
def test_monitor_creates_notification_for_new_finding(create):
    monitor, hub = _monitor()
    _feed(monitor, hub, FAULTED)
    create.assert_called_once_with(
        monitor._hass,
        "Kessel in Störung: Störung",
        "Pelletheizung: Störung",
        "oekofen_pellematic_compact_pelletheizung_pe1_fault",
    )


@patch("homeassistant.components.persistent_notification.async_create")
def test_monitor_creates_nothing_when_switched_off(create):
    monitor, hub = _monitor(notify=False)
    _feed(monitor, hub, FAULTED)
    create.assert_not_called()


@patch("homeassistant.components.persistent_notification.async_create")
def test_monitor_does_not_repeat_or_clear(create):
    monitor, hub = _monitor()
    with patch("homeassistant.components.persistent_notification.async_dismiss") as dismiss:
        _feed(monitor, hub, FAULTED)
        _feed(monitor, hub, FAULTED)
        _feed(monitor, hub, RUNNING)
    assert create.call_count == 1
    dismiss.assert_not_called()


@patch("homeassistant.components.persistent_notification.async_create")
def test_monitor_does_not_notify_again_after_restart(create):
    first, hub = _monitor()
    _feed(first, hub, FAULTED)
    restarted, hub = _monitor(stored=first.diagnosis.as_dict())
    _feed(restarted, hub, FAULTED)
    assert create.call_count == 1
