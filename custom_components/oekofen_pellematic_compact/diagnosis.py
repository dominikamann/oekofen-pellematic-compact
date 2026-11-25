"""Diagnosis module: detects faults, coming problems and inefficient operation.

The boiler only raises a fault once it gives up. Before that it compensates —
a fouled heat exchanger shows up as a flue-gas fan spinning ever harder for the
same output (one installation: ~41 % → 97.5 % at full load over five weeks
before it stopped with "Störung"). Other problems never raise a fault at all:
a boiler that starts 20 times a day, an outside sensor in the morning sun, a
mixer that never reaches its flow temperature.

Every check runs on values the API already delivers and only where they exist.
The findings are combined into one status, published as entities and fired as
events. Reference values:

* Flue-gas fan at full load: learned per boiler; +15 % cleaning soon, +30 % due.
* Burner cycling: a well set up system starts 1-3 times a day and burns ~1 h or
  more per start; below 30 min per start counts as short cycling
  (heizungsforum.de, Paradigma).
* Maintenance: Ökofen asks for a cleaning after 1800 full-load hours, at least
  once a year (operating manual).
* Heat pump (experimental): 90 % of the Fraunhofer field test stayed below ~15
  compressor starts a day; runs shorter than ~6-10 min cost efficiency (BWP).
* Heating curve (experimental, figures only, no finding): the controller sets
  `flow set = room set + offset + slope * (room set - outdoor)`, so slope and
  offset can be read back from the set points alone. One installation over a
  heating season: slope 0.998 and offset 10.04 K against "Heizkurve 1.0" on the
  controller. Below a room set of 15 °C the set point leaves the curve (-6 to
  +17 K). A curve cut off at the flow limits fits a straight line with little
  scatter but different slopes in the lower and upper half of the weather
  (0.99 / 0.33 when cut at 50 °C), which is what the half-slope check catches.
  A curve cut off in the coldest weeks only shows as scatter (0.36 K when cut
  at 58 °C, slope already 5 % low) while an intact one stays below 0.2 K.
  A circuit without a mixer simply gets the source temperature: with the buffer
  8 K or more above the set point the flow sat 9.7 K above it on average and
  never below 3.4 K over any 48 such hours; a mixer holds it near the set point.

`*Health` classes and `MessageLog` are plain Python (no Home Assistant imports)
so they can be unit-tested; `DiagnosisMonitor` wires them to the hub, a `Store`
and the event bus.
"""

from __future__ import annotations

import logging
import math
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from .const import DOMAIN, get_api_value

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
# Store.async_delay_save restarts its timer on every call, and the hub polls
# more often than any sensible delay - so the monitor saves on its own clock.
SAVE_INTERVAL_SECONDS = 300
EVENT_MESSAGE = f"{DOMAIN}_message"
EVENT_FINDING = f"{DOMAIN}_finding"
DAY = 86400.0

# Boiler state indices, as listed in the `format` of `pe.L_state` on firmware
# that ships one ("0:Dauerlauf|1:Start|2:Zuendung|...|11:Störung|..."). Newer
# firmware sends the same indices as a bit mask instead (16 = bit 4 =
# Leistungsbrand, 2048 = bit 11 = Störung) and drops the `format`.
STATE_START = 1
STATE_IGNITION = 2
STATE_SOFTSTART = 3
STATE_FULL_BURN = 4
STATE_SUCTION = 7
STATE_ASH = 8
STATE_PELLETS = 9
STATE_FAULT = 11
_MAX_STATE_INDEX = 101

MAX_SAMPLE_SECONDS = 300  # cap the weight of a sample after a polling gap

# Flue-gas fan index: samples only at (near) full load, so they are comparable.
FULL_LOAD_MODULATION = 95
RECENT_TAU_SECONDS = 8 * 3600  # EWMA time constant, counted in full-load time
BASELINE_LEARN_SECONDS = 5 * 3600  # full-load time before a baseline exists
BASELINE_TAU_SECONDS = 300 * 3600  # slow drift adaption once learned
BASELINE_ADAPT_BELOW = 105.0  # never learn a fouling boiler as the new normal
BASELINE_TAU_DOWN_SECONDS = 50 * 3600  # a cleaner boiler than learned is adopted faster
BASELINE_DOWN_BELOW = 95.0
# The recorder's hourly statistics give a baseline at once, even if the boiler
# is already fouling: a low quantile of a year of full-load hours stays at the
# clean level (one installation: 40.0-41.2 % at any date, also at 65 % fouled).
HISTORY_DAYS = 365
HISTORY_MIN_HOURS = 20
HISTORY_QUANTILE = 0.2
HISTORY_RECENT_HOURS = 3  # the latest full-load hours seed the current reading
HISTORY_RECENT_MAX_AGE = 7 * 86400
HISTORY_REPLACE_BELOW = 0.95  # a learned baseline only yields to a clearly lower one
INDEX_SOON = 115.0
INDEX_DUE = 130.0
INDEX_HYSTERESIS = 5.0

# Ignition
MAX_IGNITION_MINUTES = 60  # longer means a polling gap, not an ignition
IGNITION_AVG_ALPHA = 0.1
IGNITION_REFERENCE_COUNT = 20  # ignitions averaged into the reference
IGNITION_SLOW_FACTOR = 1.5
IGNITION_FAILURES_WARN = 3  # failed ignitions within the window
WINDOW_DAYS = 7

# Burner cycling (rolling WINDOW_DAYS average)
MIN_WINDOW_DAYS = 2  # before a cycling finding is raised
MIN_DISPLAY_DAYS = 0.5  # before the rate is shown at all
MIN_STARTS_FOR_RUNTIME = 3
STARTS_NOTICE = 10
STARTS_INEFFICIENT = 15
RUNTIME_NOTICE_MIN = 60
RUNTIME_INEFFICIENT_MIN = 30

# Maintenance (Ökofen: after 1800 full-load hours, at least yearly)
MAINTENANCE_HOURS = 1800
MAINTENANCE_DAYS = 365

# Heating circuit: flow temperature clearly below its set point for hours
FLOW_DEFICIT_K = 5
FLOW_DEFICIT_SECONDS = 4 * 3600
FLOW_MIN_SET = 20

# Heating curve (experimental): read back from the set points, per circuit
CURVE_MIN_ROOM_SET = 15  # below, the set point follows frost protection, not the curve
CURVE_BIN_K = 2  # width of a class of (room set - outdoor)
CURVE_TAU_SECONDS = 14 * DAY  # counted in heating time, so summer does not erase it
CURVE_MIN_SECONDS = 24 * 3600
CURVE_MIN_BIN_SECONDS = 3600
CURVE_MIN_BINS = 4
CURVE_MIN_SPREAD_K = 6
CURVE_MAX_SCATTER_K = 0.3  # the set points are computed, not measured: a real curve fits almost exactly
CURVE_MAX_HALF_SLOPE_DIFF = 0.15  # lower vs. upper half: a curve cut off at a flow limit
CURVE_MIN_SLOPE = 0.1
CURVE_HISTORY_DAYS = 90
# Mixed or not: what the flow does while the source is clearly hotter than asked for
SOURCE_HOT_K = 8
MIXED_MAX_SURPLUS_K = 2
UNMIXED_MIN_SURPLUS_K = 5

# Outside sensor in the sun
AMBIENT_MAX_PLAUSIBLE = 45
AMBIENT_MAX_RISE_PER_HOUR = 6
AMBIENT_SUN_DAYS = 3  # days with implausible readings within AMBIENT_WINDOW_DAYS
AMBIENT_WINDOW_DAYS = 30

# Heat pump (experimental)
WP_STARTS_NOTICE = 15
WP_STARTS_INEFFICIENT = 30
WP_RUNTIME_NOTICE_MIN = 10
WP_RUNTIME_INEFFICIENT_MIN = 6
MAX_CYCLE_SECONDS = 24 * 3600

HISTORY_SIZE = 50
SEEN_KEYS_SIZE = 200

# Diagnosis status, ordered from harmless to severe. Findings carry one of
# these; the overall status is the most severe one. From PROBLEM_FROM on the
# problem binary sensor turns on.
STATUS_OK = "ok"
STATUS_LEARNING = "learning"
STATUS_NOTICE = "notice"
STATUS_INEFFICIENT = "inefficient"
STATUS_CLEANING_SOON = "cleaning_soon"
STATUS_MAINTENANCE_DUE = "maintenance_due"
STATUS_CLEANING_DUE = "cleaning_due"
STATUS_WARNING = "warning"
STATUS_FAULT = "fault"
STATUS_OPTIONS = [
    STATUS_OK,
    STATUS_LEARNING,
    STATUS_NOTICE,
    STATUS_INEFFICIENT,
    STATUS_CLEANING_SOON,
    STATUS_MAINTENANCE_DUE,
    STATUS_CLEANING_DUE,
    STATUS_WARNING,
    STATUS_FAULT,
]
PROBLEM_FROM = STATUS_CLEANING_SOON

# Finding codes
FAULT = "fault"
BOILER_MESSAGE = "boiler_message"
CLEANING_SOON = "cleaning_soon"
CLEANING_DUE = "cleaning_due"
MAINTENANCE_DUE = "maintenance_due"
IGNITION_FAILURES = "ignition_failures"
IGNITION_SLOW = "ignition_slow"
SHORT_CYCLING = "short_cycling"
FLOW_TEMPERATURE_LOW = "flow_temperature_low"
OUTSIDE_SENSOR_SUN = "outside_sensor_sun"
HEAT_PUMP_SHORT_CYCLING = "heat_pump_short_cycling"
NO_MESSAGES = "no_messages"  # text of the last-message sensor before the first one

CURVE_LEARNING = "learning"
CURVE_DETERMINED = "determined"
CURVE_UNDETERMINABLE = "undeterminable"
CIRCUIT_MIXED = "mixed"
CIRCUIT_UNMIXED = "unmixed"
CIRCUIT_UNKNOWN = "unknown"
# "unknown" is not offered as a sensor state: Home Assistant already has one of that name.
CIRCUIT_TYPES = [CIRCUIT_MIXED, CIRCUIT_UNMIXED]

MESSAGES = {
    "en": {
        FAULT: "Boiler in fault state: {value}",
        BOILER_MESSAGE: "Boiler message: {value}",
        CLEANING_SOON: "Flue-gas fan at {value} % of normal - plan a cleaning",
        CLEANING_DUE: "Flue-gas fan at {value} % of normal - clean the boiler soon to avoid a breakdown",
        MAINTENANCE_DUE: "Maintenance due ({value}) - press 'Maintenance done' afterwards",
        IGNITION_FAILURES: "{value} failed ignitions in 7 days - check igniter, pellet feed and ash",
        IGNITION_SLOW: "Ignition takes {value} min, much longer than usual - check igniter and burner plate",
        SHORT_CYCLING: "Short cycling ({value}) - check buffer hysteresis, minimum runtime and heating curve",
        FLOW_TEMPERATURE_LOW: "Flow temperature {value} K below set point for hours - check mixer, pump and boiler",
        OUTSIDE_SENSOR_SUN: "Outside sensor implausible on {value} days (sun?) - shade it or move it to the north side",
        HEAT_PUMP_SHORT_CYCLING: "Compressor cycling ({value}) - check flow rate, buffer and heating curve (experimental)",
        NO_MESSAGES: "No messages",
    },
    "de": {
        FAULT: "Kessel in Störung: {value}",
        BOILER_MESSAGE: "Kesselmeldung: {value}",
        CLEANING_SOON: "Saugzug bei {value} % des Normalwerts - Reinigung einplanen",
        CLEANING_DUE: "Saugzug bei {value} % des Normalwerts - Kessel bald reinigen, sonst droht ein Ausfall",
        MAINTENANCE_DUE: "Wartung fällig ({value}) - danach 'Wartung erledigt' drücken",
        IGNITION_FAILURES: "{value} Fehlzündungen in 7 Tagen - Zünder, Pelletzufuhr und Asche prüfen",
        IGNITION_SLOW: "Zündung dauert {value} min, deutlich länger als üblich - Zünder und Brennerteller prüfen",
        SHORT_CYCLING: "Kessel taktet ({value}) - Puffer-Hysterese, Mindestlaufzeit und Heizkurve prüfen",
        FLOW_TEMPERATURE_LOW: "Vorlauf seit Stunden {value} K unter Soll - Mischer, Pumpe und Kessel prüfen",
        OUTSIDE_SENSOR_SUN: "Außenfühler an {value} Tagen unplausibel (Sonne?) - beschatten oder an die Nordseite versetzen",
        HEAT_PUMP_SHORT_CYCLING: "Verdichter taktet ({value}) - Durchfluss, Puffer und Heizkurve prüfen (experimentell)",
        NO_MESSAGES: "Keine Meldungen",
    },
    "fr": {
        FAULT: "Chaudière en défaut : {value}",
        BOILER_MESSAGE: "Message de la chaudière : {value}",
        CLEANING_SOON: "Extracteur de fumées à {value} % de la normale - prévoir un nettoyage",
        CLEANING_DUE: "Extracteur de fumées à {value} % de la normale - nettoyer bientôt pour éviter une panne",
        MAINTENANCE_DUE: "Entretien nécessaire ({value}) - appuyer ensuite sur 'Entretien effectué'",
        IGNITION_FAILURES: "{value} allumages ratés en 7 jours - vérifier l'allumeur, l'alimentation et les cendres",
        IGNITION_SLOW: "L'allumage dure {value} min, bien plus que d'habitude - vérifier l'allumeur et le brûleur",
        SHORT_CYCLING: "Cycles courts ({value}) - vérifier l'hystérésis du ballon, la durée minimale et la courbe de chauffe",
        FLOW_TEMPERATURE_LOW: "Départ {value} K sous la consigne depuis des heures - vérifier vanne, circulateur et chaudière",
        OUTSIDE_SENSOR_SUN: "Sonde extérieure incohérente {value} jours (soleil ?) - l'ombrager ou la déplacer au nord",
        HEAT_PUMP_SHORT_CYCLING: "Cycles courts du compresseur ({value}) - vérifier débit, ballon et courbe (expérimental)",
        NO_MESSAGES: "Aucun message",
    },
}

# Titles of the persistent notifications, one short label per finding code.
NOTIFICATION_TITLES = {
    "en": {
        FAULT: "Fault",
        BOILER_MESSAGE: "Boiler message",
        CLEANING_SOON: "Cleaning due soon",
        CLEANING_DUE: "Cleaning due",
        MAINTENANCE_DUE: "Maintenance due",
        IGNITION_FAILURES: "Ignition problems",
        IGNITION_SLOW: "Slow ignition",
        SHORT_CYCLING: "Short cycling",
        FLOW_TEMPERATURE_LOW: "Flow temperature too low",
        OUTSIDE_SENSOR_SUN: "Outside sensor in the sun",
        HEAT_PUMP_SHORT_CYCLING: "Heat pump short cycling",
    },
    "de": {
        FAULT: "Störung",
        BOILER_MESSAGE: "Kesselmeldung",
        CLEANING_SOON: "Reinigung bald fällig",
        CLEANING_DUE: "Reinigung fällig",
        MAINTENANCE_DUE: "Wartung fällig",
        IGNITION_FAILURES: "Zündprobleme",
        IGNITION_SLOW: "Langsame Zündung",
        SHORT_CYCLING: "Kessel taktet",
        FLOW_TEMPERATURE_LOW: "Vorlauf zu niedrig",
        OUTSIDE_SENSOR_SUN: "Außenfühler in der Sonne",
        HEAT_PUMP_SHORT_CYCLING: "Wärmepumpe taktet",
    },
    "fr": {
        FAULT: "Défaut",
        BOILER_MESSAGE: "Message de la chaudière",
        CLEANING_SOON: "Nettoyage bientôt nécessaire",
        CLEANING_DUE: "Nettoyage nécessaire",
        MAINTENANCE_DUE: "Entretien nécessaire",
        IGNITION_FAILURES: "Problèmes d'allumage",
        IGNITION_SLOW: "Allumage lent",
        SHORT_CYCLING: "Cycles courts",
        FLOW_TEMPERATURE_LOW: "Température de départ trop basse",
        OUTSIDE_SENSOR_SUN: "Sonde extérieure au soleil",
        HEAT_PUMP_SHORT_CYCLING: "Cycles courts de la pompe à chaleur",
    },
}

_MESSAGE_RE = re.compile(
    r"^\s*(?P<time>\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})\s*\|(?P<text>.*?)(?:\[(?P<code>\d+)\])?\s*$",
    re.DOTALL,
)


def _number(raw: Any) -> Optional[float]:
    """Scaled numeric value of an API field (applies `factor`), or None."""
    value = get_api_value(raw)
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value <= -32766 or 32765 <= value <= 32767 and isinstance(raw, dict) and "max" in raw:
        return None  # int16 "not available" markers
    factor = raw.get("factor") if isinstance(raw, dict) else None
    try:
        return value * float(factor) if factor is not None else value
    except (TypeError, ValueError):
        return value


def _has_metadata(raw: Any) -> bool:
    """Modern firmware: the value comes with its `factor`, so it can be scaled."""
    return isinstance(raw, dict) and "val" in raw


def _is_on(raw: Any) -> Optional[bool]:
    """A switch state of the API: 0/1 or "true"/"false", bare or as `val`. None if absent."""
    value = raw.get("val") if isinstance(raw, dict) else raw
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "on"):
            return True
        if text in ("false", "off", ""):
            return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= -32766 or number >= 32765:
        return None  # int16 "not available" markers
    return number != 0


def decode_state(raw: Any) -> set[int]:
    """Return the set of state indices encoded in `pe.L_state`.

    A metadata dict with a `format` carries a plain index; one without carries
    a bit mask. Bare values (old firmware, no metadata) are indices. Anything
    beyond the highest documented index can only be a bit mask.
    """
    value = get_api_value(raw)
    try:
        value = int(float(value))
    except (TypeError, ValueError):
        return set()
    if value < 0:
        return set()
    bitmask = isinstance(raw, dict) and "format" not in raw
    if bitmask or value > _MAX_STATE_INDEX:
        return {bit for bit in range(value.bit_length()) if value >> bit & 1}
    return {value}


def parse_message(raw: Any) -> Optional[dict]:
    """Parse one `error.error_N` entry: "29-01-2026 18:21:32|PE 1 Pellets Warnung [5054]"."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    match = _MESSAGE_RE.match(raw)
    if not match:
        return {"time": None, "text": " ".join(raw.split()), "code": None}
    try:
        when = datetime.strptime(match["time"], "%d-%m-%Y %H:%M:%S").isoformat()
    except ValueError:
        when = None
    return {
        "time": when,
        "text": " ".join(match["text"].split()),
        "code": int(match["code"]) if match["code"] else None,
    }


def baseline_from_history(
    fan_rows: list[tuple[float, float]], modulation_rows: list[tuple[float, float]], now: float
) -> Optional[tuple[float, Optional[float], int]]:
    """(baseline, recent, hours) from hourly means (start, mean) of fan and modulation.

    Only hours with a mean modulation at full load count. None with too few of them.
    """
    modulation = dict(modulation_rows)
    hours = sorted(
        (start, fan)
        for start, fan in fan_rows
        if fan and fan > 0 and (modulation.get(start) or 0) >= FULL_LOAD_MODULATION
    )
    if len(hours) < HISTORY_MIN_HOURS:
        return None
    values = sorted(fan for _, fan in hours)
    position = HISTORY_QUANTILE * (len(values) - 1)
    low, high = values[math.floor(position)], values[math.ceil(position)]
    baseline = low + (high - low) * (position - math.floor(position))
    latest = hours[-HISTORY_RECENT_HOURS:]
    recent = (
        sum(fan for _, fan in latest) / len(latest)
        if now - latest[-1][0] <= HISTORY_RECENT_MAX_AGE
        else None
    )
    return baseline, recent, len(hours)


def _finding(code: str, status: str, value: Any = None, **extra) -> dict:
    return {"code": code, "status": status, "value": value, **extra}


class CounterRate:
    """Per-day rate of monotonic counters over a rolling window.

    Keeps the first reading of each day for WINDOW_DAYS + 1 days and compares
    the current reading against the oldest one inside the window.
    """

    def __init__(self, stored: Optional[list] = None) -> None:
        self.snapshots: list[list[float]] = stored or []  # [t, counter1, counter2, ...]

    def update(self, now: float, *values: Optional[float]) -> None:
        if any(v is None for v in values):
            return
        # A counter that went backwards (board swap, reset) restarts the window.
        if self.snapshots and any(v < old for v, old in zip(values, self.snapshots[-1][1:])):
            self.snapshots = []
        if not self.snapshots or int(now // DAY) != int(self.snapshots[-1][0] // DAY):
            self.snapshots.append([now, *values])
        self.snapshots = [s for s in self.snapshots if now - s[0] <= (WINDOW_DAYS + 1) * DAY]
        self._current = [now, *values]

    @property
    def current(self) -> Optional[list[float]]:
        return getattr(self, "_current", None)

    def deltas(
        self, now: float, min_days: float = MIN_WINDOW_DAYS
    ) -> Optional[tuple[float, list[float]]]:
        """(days, [delta per counter]) over the window, or None while too short."""
        current = getattr(self, "_current", None)
        if current is None:
            return None
        inside = [s for s in self.snapshots if now - s[0] <= WINDOW_DAYS * DAY]
        if not inside:
            return None
        oldest = inside[0]
        days = (current[0] - oldest[0]) / DAY
        if days < min_days:
            return None
        return days, [c - o for c, o in zip(current[1:], oldest[1:])]


def _rate(window) -> Optional[float]:
    return round(window[1][0] / window[0], 1) if window else None


def _minutes_per_start(window) -> Optional[float]:
    if not window or window[1][0] < MIN_STARTS_FOR_RUNTIME:
        return None
    return round(60.0 * window[1][1] / window[1][0])


class HeaterHealth:
    """Health of one Pellematic (`pe1`, `pe2`, ...)."""

    def __init__(self, stored: Optional[dict] = None) -> None:
        stored = stored or {}
        # Flue-gas fan
        self.baseline: Optional[float] = stored.get("baseline")
        self.learn_seconds: float = stored.get("learn_seconds", 0.0)
        self.learn_sum: float = stored.get("learn_sum", 0.0)
        self.recent: Optional[float] = stored.get("recent")
        self.flue_level: int = stored.get("flue_level", 0)
        self.baseline_source: Optional[str] = stored.get(
            "baseline_source", "learned" if self.baseline else None
        )
        self.history_checked: bool = stored.get("history_checked", False)
        # Ignition
        self.ignition_last: Optional[float] = stored.get("ignition_last")
        self.ignition_avg: Optional[float] = stored.get("ignition_avg")
        self.ignition_count: int = stored.get("ignition_count", 0)
        self.ignition_reference: Optional[float] = stored.get("ignition_reference")
        self._ignition_ref_samples: list[float] = stored.get("ignition_ref_samples", [])
        self.ignition_failures: list[float] = stored.get("ignition_failures", [])
        # Cycling
        self.cycling = CounterRate(stored.get("cycling"))
        # Maintenance
        self.maintenance_since: Optional[float] = stored.get("maintenance_since")
        self.full_load_seconds: float = stored.get("full_load_seconds", 0.0)

        self.has_flue_gas = False
        self.has_counters = False
        self.states: set[int] = set()
        self._ignition_start: Optional[float] = None
        # Set when an ignition was cut short by a pellet suction; the outcome
        # is decided by what the boiler does once the hopper is refilled.
        self._ignition_interrupted: Optional[float] = None
        self._last_update: Optional[float] = None
        self._now: float = 0.0

    def as_dict(self) -> dict:
        return {
            "baseline": self.baseline,
            "learn_seconds": self.learn_seconds,
            "learn_sum": self.learn_sum,
            "recent": self.recent,
            "flue_level": self.flue_level,
            "baseline_source": self.baseline_source,
            "history_checked": self.history_checked,
            "ignition_last": self.ignition_last,
            "ignition_avg": self.ignition_avg,
            "ignition_count": self.ignition_count,
            "ignition_reference": self.ignition_reference,
            "ignition_ref_samples": self._ignition_ref_samples,
            "ignition_failures": self.ignition_failures,
            "cycling": self.cycling.snapshots,
            "maintenance_since": self.maintenance_since,
            "full_load_seconds": self.full_load_seconds,
        }

    # -- figures -----------------------------------------------------------

    @property
    def flue_gas_index(self) -> Optional[float]:
        """Fan speed at full load relative to the learned baseline, in %."""
        if not self.baseline or self.recent is None:
            return None
        return round(100.0 * self.recent / self.baseline, 1)

    @property
    def learn_progress(self) -> float:
        if self.baseline:
            return 100.0
        return round(min(100.0, 100.0 * self.learn_seconds / BASELINE_LEARN_SECONDS), 1)

    @property
    def starts_per_day(self) -> Optional[float]:
        """Starts per day over the window; None until it is long enough to judge."""
        return _rate(self.cycling.deltas(self._now))

    @property
    def runtime_per_start(self) -> Optional[float]:
        """Average burner minutes per start over the window."""
        return _minutes_per_start(self.cycling.deltas(self._now))

    @property
    def starts_per_day_display(self) -> Optional[float]:
        """Shown earlier than it is judged, so the sensor is not 'unknown' for days."""
        return _rate(self.cycling.deltas(self._now, MIN_DISPLAY_DAYS))

    @property
    def runtime_per_start_display(self) -> tuple[Optional[float], Optional[str]]:
        """(minutes, basis): the window once available, the lifetime counters before."""
        window = _minutes_per_start(self.cycling.deltas(self._now, MIN_DISPLAY_DAYS))
        if window is not None:
            return window, "7_days"
        current = self.cycling.current
        if current and current[1] > 0:
            return round(60.0 * current[2] / current[1]), "lifetime"
        return None, None

    @property
    def full_load_hours(self) -> float:
        return round(self.full_load_seconds / 3600.0, 1)

    @property
    def maintenance_days(self) -> Optional[int]:
        if self.maintenance_since is None:
            return None
        return int((self._now - self.maintenance_since) // DAY)

    def failed_ignitions(self) -> int:
        return sum(1 for t in self.ignition_failures if self._now - t <= WINDOW_DAYS * DAY)

    # -- updates -----------------------------------------------------------

    def update(self, pe: dict, now: float) -> None:
        """Feed one API response of this heater, taken at `now` (seconds)."""
        previous_states, self.states = self.states, decode_state(pe.get("L_state"))
        previous_update, self._last_update, self._now = self._last_update, now, now
        weight = (
            min(max(now - previous_update, 0.0), MAX_SAMPLE_SECONDS)
            if previous_update is not None
            else 0.0
        )
        if self.maintenance_since is None:
            self.maintenance_since = now

        self._track_ignition(previous_states, now)
        self.has_flue_gas = "L_fluegas" in pe
        modulation = _number(pe.get("L_modulation"))
        self._track_flue_gas(_number(pe.get("L_fluegas")), modulation, weight)
        if modulation and STATE_FULL_BURN in self.states:
            self.full_load_seconds += weight * min(modulation, 100.0) / 100.0

        starts, runtime = _number(pe.get("L_starts")), _number(pe.get("L_runtime"))
        self.has_counters = starts is not None and runtime is not None
        self.cycling.update(now, starts, runtime)

    def seed_from_history(self, baseline: float, recent: Optional[float]) -> bool:
        """Use a baseline from the recorder history; True if it was taken.

        Replaces live learning in progress, and a learned baseline only when the
        history shows a clearly cleaner boiler (it was learned while fouling).
        """
        self.history_checked = True
        if self.baseline and baseline >= self.baseline * HISTORY_REPLACE_BELOW:
            return False
        self.baseline = baseline
        self.baseline_source = "history"
        if self.recent is None and recent is not None:
            self.recent = recent
        self._update_flue_level()
        return True

    def maintenance_done(self, now: float) -> None:
        """Reset the maintenance counters (button 'Maintenance done').

        The fan reading after a cleaning starts afresh, so a cleaning warning
        clears with the next full-load samples instead of decaying for weeks.
        The learned baseline stays: it describes the clean boiler.
        """
        self.maintenance_since = now
        self.full_load_seconds = 0.0
        self.recent = None
        self.flue_level = 0
        self.ignition_reference = None
        self._ignition_ref_samples = []
        self.ignition_failures = []

    def _track_ignition(self, previous: set[int], now: float) -> None:
        igniting = STATE_IGNITION in self.states
        if igniting and STATE_IGNITION not in previous:
            self._ignition_start = now
            self._ignition_interrupted = None
            return
        if self._ignition_interrupted is not None and not igniting:
            self._resolve_interrupted_ignition(now)
            return
        if igniting or self._ignition_start is None:
            return
        minutes = (now - self._ignition_start) / 60.0
        self._ignition_start = None
        if not 0 < minutes <= MAX_IGNITION_MINUTES:
            return
        burning = self.states & {STATE_SOFTSTART, STATE_FULL_BURN}
        if STATE_SUCTION in self.states and not burning:
            # The boiler paused the ignition to refill its hopper. That is not
            # a failure: the flame often catches during the suction, or the
            # boiler ignites again afterwards. Decide once the suction is over.
            self._ignition_interrupted = now
            return
        if not burning:
            self._record_ignition_failure(now)
            return
        self.ignition_last = round(minutes, 1)
        self.ignition_avg = round(
            minutes
            if self.ignition_avg is None
            else self.ignition_avg + IGNITION_AVG_ALPHA * (minutes - self.ignition_avg),
            2,
        )
        self.ignition_count += 1
        if self.ignition_reference is None:
            self._ignition_ref_samples.append(minutes)
            if len(self._ignition_ref_samples) >= IGNITION_REFERENCE_COUNT:
                self.ignition_reference = round(
                    sum(self._ignition_ref_samples) / len(self._ignition_ref_samples), 2
                )
                self._ignition_ref_samples = []

    def _resolve_interrupted_ignition(self, now: float) -> None:
        """Judge an ignition that a pellet suction interrupted.

        A flame that caught (softstart or full burn) is a success; refilling
        or preparing a fresh ignition keeps the verdict open (a new ignition
        is judged on its own). Anything else is a failed ignition. No ignition
        time is recorded: it would include the suction.
        """
        since = self._ignition_interrupted
        if since is None:
            return
        if self.states & {STATE_SOFTSTART, STATE_FULL_BURN}:
            self._ignition_interrupted = None
            return
        within = now - since <= MAX_IGNITION_MINUTES * 60
        if within and self.states & {STATE_SUCTION, STATE_START}:
            return
        self._ignition_interrupted = None
        if within:
            self._record_ignition_failure(now)

    def _record_ignition_failure(self, now: float) -> None:
        self.ignition_failures.append(now)
        self.ignition_failures = [
            t for t in self.ignition_failures if now - t <= WINDOW_DAYS * DAY
        ]

    def _track_flue_gas(
        self, fan: Optional[float], modulation: Optional[float], weight: float
    ) -> None:
        if (
            fan is None
            or fan <= 0
            or modulation is None
            or modulation < FULL_LOAD_MODULATION
            or STATE_FULL_BURN not in self.states
            or weight <= 0
        ):
            return
        if self.recent is None:
            self.recent = fan
        else:
            self.recent += (1 - math.exp(-weight / RECENT_TAU_SECONDS)) * (fan - self.recent)

        if not self.baseline:
            self.learn_seconds += weight
            self.learn_sum += fan * weight
            if self.learn_seconds >= BASELINE_LEARN_SECONDS:
                self.baseline = self.learn_sum / self.learn_seconds
                self.baseline_source = "learned"
        elif self.flue_gas_index is not None and self.flue_gas_index < BASELINE_ADAPT_BELOW:
            tau = (
                BASELINE_TAU_DOWN_SECONDS
                if self.flue_gas_index < BASELINE_DOWN_BELOW
                else BASELINE_TAU_SECONDS
            )
            self.baseline += (1 - math.exp(-weight / tau)) * (fan - self.baseline)

        self._update_flue_level()

    def _update_flue_level(self) -> None:
        """Raise at the thresholds, drop only once clearly below (no flapping)."""
        index = self.flue_gas_index
        if index is None:
            return
        if index >= INDEX_DUE or (self.flue_level == 2 and index >= INDEX_DUE - INDEX_HYSTERESIS):
            self.flue_level = 2
        elif index >= INDEX_SOON or (self.flue_level >= 1 and index >= INDEX_SOON - INDEX_HYSTERESIS):
            self.flue_level = 1
        else:
            self.flue_level = 0

    # -- findings ----------------------------------------------------------

    @property
    def learning(self) -> bool:
        return self.has_flue_gas and not self.baseline

    def findings(self, state_text: str = "") -> list[dict]:
        found = []
        if STATE_FAULT in self.states:
            found.append(_finding(FAULT, STATUS_FAULT, state_text or "Störung"))
        if self.states & {STATE_ASH, STATE_PELLETS}:
            found.append(_finding(BOILER_MESSAGE, STATUS_WARNING, state_text))
        if self.flue_level == 2:
            found.append(_finding(CLEANING_DUE, STATUS_CLEANING_DUE, self.flue_gas_index))
        elif self.flue_level == 1:
            found.append(_finding(CLEANING_SOON, STATUS_CLEANING_SOON, self.flue_gas_index))

        due = []
        if self.full_load_hours >= MAINTENANCE_HOURS:
            due.append(f"{self.full_load_hours:.0f} h")
        if (self.maintenance_days or 0) >= MAINTENANCE_DAYS:
            due.append(f"{self.maintenance_days} d")
        if due:
            found.append(_finding(MAINTENANCE_DUE, STATUS_MAINTENANCE_DUE, ", ".join(due)))

        failures = self.failed_ignitions()
        if failures >= IGNITION_FAILURES_WARN:
            found.append(_finding(IGNITION_FAILURES, STATUS_WARNING, failures))
        if (
            self.ignition_reference
            and self.ignition_avg
            and self.ignition_avg >= IGNITION_SLOW_FACTOR * self.ignition_reference
        ):
            found.append(_finding(IGNITION_SLOW, STATUS_NOTICE, round(self.ignition_avg, 1)))

        starts, runtime = self.starts_per_day, self.runtime_per_start
        status = None
        if (starts or 0) > STARTS_INEFFICIENT or (
            runtime is not None and runtime < RUNTIME_INEFFICIENT_MIN
        ):
            status = STATUS_INEFFICIENT
        elif (starts or 0) > STARTS_NOTICE or (runtime is not None and runtime < RUNTIME_NOTICE_MIN):
            status = STATUS_NOTICE
        if status:
            runtime_text = f", {runtime:.0f} min/start" if runtime is not None else ""
            found.append(_finding(SHORT_CYCLING, status, f"{starts:.1f}/d{runtime_text}"))
        return found


class CircuitHealth:
    """Heating circuit (`hk1`, ...): flow temperature that never gets there."""

    def __init__(self) -> None:
        self.below_since: Optional[float] = None
        self.deficit: Optional[float] = None
        self._now = 0.0

    def update(self, hk: dict, now: float) -> None:
        self._now = now
        # Firmware without metadata sends tenths of a degree: 5 K would be 0.5 K there.
        scalable = _has_metadata(hk.get("L_flowtemp_act")) and _has_metadata(hk.get("L_flowtemp_set"))
        actual = _number(hk.get("L_flowtemp_act")) if scalable else None
        target = _number(hk.get("L_flowtemp_set")) if scalable else None
        pump = _is_on(hk.get("L_pump"))  # 1 or "true", depending on the firmware
        if (
            actual is not None
            and target is not None
            and pump
            and target >= FLOW_MIN_SET
            and actual < target - FLOW_DEFICIT_K
        ):
            if self.below_since is None:
                self.below_since = now
            self.deficit = round(target - actual, 1)
        else:
            self.below_since = None
            self.deficit = None

    def findings(self) -> list[dict]:
        if self.below_since is not None and self._now - self.below_since >= FLOW_DEFICIT_SECONDS:
            return [_finding(FLOW_TEMPERATURE_LOW, STATUS_WARNING, self.deficit)]
        return []


def has_curve_inputs(hk: Any, system: Any) -> bool:
    """Whether a circuit delivers what the curve analysis needs, in scalable form.

    Firmware without metadata sends unscaled values in mixed scales (flow set
    371 next to a heat pump flow of 12.2), so it is left out altogether.
    """
    if not isinstance(hk, dict) or not isinstance(system, dict):
        return False
    return _has_metadata(system.get("L_ambient")) and all(
        _has_metadata(hk.get(key)) for key in ("L_flowtemp_set", "L_flowtemp_act", "L_roomtemp_set")
    )


def source_temperature(data: dict) -> Optional[float]:
    """Temperature available to the heating circuits, on the safe (cool) side.

    The API does not say which source feeds which circuit. With buffers the
    circuits draw from a buffer, and the boiler charging it is hotter than what
    reaches them - so only buffers count, and of several the coolest: if even
    that one is hot, the real source is too. Without a buffer the generators
    feed the circuits directly.
    """

    def readings(prefix: str, key: str) -> tuple[bool, list[float]]:
        present, values = False, []
        for name, component in data.items():
            if not isinstance(component, dict) or not re.fullmatch(rf"{prefix}\d+", name):
                continue
            present = True
            if _has_metadata(component.get(key)):
                value = _number(component[key])
                if value is not None:
                    values.append(value)
        return present, values

    has_buffer, buffers = readings("pu", "L_tpo_act")
    if has_buffer:
        return min(buffers) if buffers else None
    generators = readings("pe", "L_temp_act")[1] + readings("wp", "L_temp_flow_is")[1]
    return min(generators) if generators else None


def _line(points: list[tuple[float, float, float]]) -> tuple[float, float]:
    """Weighted least-squares line through (weight, x, y): (slope, offset)."""
    total = sum(w for w, _, _ in points)
    mean_x = sum(w * x for w, x, _ in points) / total
    mean_y = sum(w * y for w, _, y in points) / total
    spread = sum(w * (x - mean_x) ** 2 for w, x, _ in points)
    if spread <= 0:
        return 0.0, mean_y
    slope = sum(w * (x - mean_x) * (y - mean_y) for w, x, y in points) / spread
    return slope, mean_y - slope * mean_x


class CurveHealth:
    """Heating circuit (`hk1`, ...): the heating curve in effect, mixed or not, flow surplus.

    Experimental and figures only. With x = room set - outdoor and
    y = flow set - room set the controller's curve is the line
    y = offset + slope * x; the samples are collected in classes of x and fade
    with the heating time, so a changed curve takes over within weeks.
    """

    def __init__(self, stored: Optional[dict] = None) -> None:
        stored = stored or {}
        # class of x -> [seconds, sum of x, sum of y, sum of outdoor], all time-weighted
        self._bins: dict[int, list[float]] = {int(k): list(v) for k, v in stored.get("bins", {}).items()}
        self._surplus: list[float] = list(stored.get("surplus", [0.0, 0.0]))  # seconds, sum
        self._hot: list[float] = list(stored.get("hot", [0.0, 0.0]))  # seconds, sum of surplus
        self._room_set: Optional[float] = stored.get("room_set")
        self._mixer_config: Optional[bool] = stored.get("mixer_config")
        self.configured_slope: Optional[float] = stored.get("configured_slope")
        self.history_checked: bool = stored.get("history_checked", False)
        self._last: Optional[float] = None
        self._fit_cache: Optional[tuple] = None

    def as_dict(self) -> dict:
        return {
            "bins": {str(k): [round(v, 3) for v in values] for k, values in self._bins.items()},
            "surplus": [round(v, 3) for v in self._surplus],
            "hot": [round(v, 3) for v in self._hot],
            "room_set": self._room_set,
            "mixer_config": self._mixer_config,
            "configured_slope": self.configured_slope,
            "history_checked": self.history_checked,
        }

    def update(self, hk: dict, ambient: Optional[float], source: Optional[float], now: float) -> None:
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), MAX_SAMPLE_SECONDS)
        self._last = now
        self._mixer_config = _is_on(hk.get("L_cfg_mixer"))
        self.configured_slope = _number(hk.get("L_cfg_curve_slope"))
        self.add_sample(
            seconds,
            ambient,
            _number(hk.get("L_roomtemp_set")),
            _number(hk.get("L_flowtemp_set")),
            _number(hk.get("L_flowtemp_act")),
            source,
            hk.get("L_pump"),
        )

    def add_sample(
        self,
        seconds: float,
        ambient: Optional[float],
        room_set: Optional[float],
        flow_set: Optional[float],
        flow_act: Optional[float],
        source: Optional[float],
        pump: Any = None,
    ) -> bool:
        """Count `seconds` of operation at these values; False if the circuit is not heating."""
        if ambient is None or room_set is None or flow_set is None or flow_act is None:
            return False
        if _is_on(pump) is False:  # an absent pump state leaves it to the set points
            return False
        if flow_set < FLOW_MIN_SET or flow_set <= room_set or room_set < CURVE_MIN_ROOM_SET:
            return False
        self._room_set = room_set
        if seconds <= 0:
            return True
        self._fit_cache = None
        keep = math.exp(-seconds / CURVE_TAU_SECONDS)
        for values in self._bins.values():
            for index in range(len(values)):
                values[index] *= keep
        x, y = room_set - ambient, flow_set - room_set
        entry = self._bins.setdefault(math.floor(x / CURVE_BIN_K), [0.0, 0.0, 0.0, 0.0])
        for index, value in enumerate((1.0, x, y, ambient)):
            entry[index] += seconds * value
        surplus = flow_act - flow_set
        self._surplus = [self._surplus[0] * keep + seconds, self._surplus[1] * keep + seconds * surplus]
        if source is not None and source >= flow_set + SOURCE_HOT_K:
            self._hot = [self._hot[0] * keep + seconds, self._hot[1] * keep + seconds * surplus]
        return True

    # --- heating curve

    def _fit(self) -> tuple[str, Optional[float], Optional[float], Optional[float]]:
        """(status, slope, offset, scatter) from the classes that hold enough time."""
        if self._fit_cache is not None:
            return self._fit_cache
        points = sorted(
            (values[1] / values[0], values[0], values[2] / values[0])
            for values in self._bins.values()
            if values[0] >= CURVE_MIN_BIN_SECONDS
        )
        points = [(w, x, y) for x, w, y in points]
        result: tuple = (CURVE_LEARNING, None, None, None)
        if (
            self._surplus[0] >= CURVE_MIN_SECONDS
            and len(points) >= CURVE_MIN_BINS
            and points[-1][1] - points[0][1] >= CURVE_MIN_SPREAD_K
        ):
            slope, offset = _line(points)
            total = sum(w for w, _, _ in points)
            scatter = math.sqrt(sum(w * (y - offset - slope * x) ** 2 for w, x, y in points) / total)
            middle = len(points) // 2
            lower, upper = _line(points[: middle + 1])[0], _line(points[middle:])[0]
            if (
                scatter > CURVE_MAX_SCATTER_K
                or abs(lower - upper) > CURVE_MAX_HALF_SLOPE_DIFF
                or slope < CURVE_MIN_SLOPE
            ):
                result = (CURVE_UNDETERMINABLE, None, None, None)
            else:
                result = (CURVE_DETERMINED, slope, offset, scatter)
        self._fit_cache = result
        return result

    @property
    def curve_status(self) -> str:
        return self._fit()[0]

    @property
    def slope(self) -> Optional[float]:
        return self._fit()[1]

    @property
    def offset(self) -> Optional[float]:
        return self._fit()[2]

    @property
    def scatter(self) -> Optional[float]:
        return self._fit()[3]

    @property
    def heating_hours(self) -> float:
        """Heating time the figures rest on (fading, so at most ~14 days' worth)."""
        return self._surplus[0] / 3600

    @property
    def outdoor_range(self) -> Optional[tuple[float, float]]:
        outdoor = [v[3] / v[0] for v in self._bins.values() if v[0] >= CURVE_MIN_BIN_SECONDS]
        return (min(outdoor), max(outdoor)) if outdoor else None

    def flow_at(self, outdoor: float) -> Optional[float]:
        """Flow set point of the curve at this outdoor temperature, for the current room set."""
        _, slope, offset, _ = self._fit()
        if slope is None or self._room_set is None:
            return None
        return self._room_set + offset + slope * (self._room_set - outdoor)

    # --- mixed or not, flow surplus

    @property
    def hot_source_hours(self) -> float:
        return self._hot[0] / 3600

    @property
    def surplus_with_hot_source(self) -> Optional[float]:
        return self._hot[1] / self._hot[0] if self._hot[0] > 0 else None

    @property
    def circuit_type_source(self) -> Optional[str]:
        if self._mixer_config is not None:
            return "config"
        return "learned" if self.circuit_type != CIRCUIT_UNKNOWN else None

    @property
    def circuit_type(self) -> str:
        if self._mixer_config is not None:
            return CIRCUIT_MIXED if self._mixer_config else CIRCUIT_UNMIXED
        if self._hot[0] < CURVE_MIN_SECONDS:
            return CIRCUIT_UNKNOWN
        surplus = self._hot[1] / self._hot[0]
        if abs(surplus) <= MIXED_MAX_SURPLUS_K:  # far below is a fault or a stopped pump, not a mixer
            return CIRCUIT_MIXED
        if surplus >= UNMIXED_MIN_SURPLUS_K:
            return CIRCUIT_UNMIXED
        return CIRCUIT_UNKNOWN

    @property
    def flow_surplus(self) -> Optional[float]:
        """Mean of flow actual - set while heating."""
        if self._surplus[0] < CURVE_MIN_SECONDS:
            return None
        return self._surplus[1] / self._surplus[0]


def seed_curve_from_history(curve: CurveHealth, rows: dict[str, list[tuple[float, float]]]) -> int:
    """Feed hourly means (`ambient`, `room_set`, `flow_set`, `flow_act`, optional `source`).

    Each list holds (hour start in seconds, mean). An hour only counts between
    two neighbours with the same room set: the mean over a set-point change is
    not a point of the curve. Returns the hours that counted as heating.
    """
    series = {key: dict(values) for key, values in rows.items()}
    room_sets = series.get("room_set", {})
    used = 0
    for start in sorted(series.get("flow_set", {})):
        room_set = room_sets.get(start)
        before, after = room_sets.get(start - 3600), room_sets.get(start + 3600)
        if room_set is None or before is None or after is None:
            continue
        if abs(before - room_set) > 0.05 or abs(after - room_set) > 0.05:
            continue
        used += curve.add_sample(
            3600.0,
            series.get("ambient", {}).get(start),
            room_set,
            series["flow_set"][start],
            series.get("flow_act", {}).get(start),
            series.get("source", {}).get(start),
        )
    return used


class AmbientHealth:
    """Outside sensor (`system.L_ambient`): readings no weather can produce."""

    def __init__(self, stored: Optional[dict] = None) -> None:
        stored = stored or {}
        self.sun_days: list[int] = stored.get("sun_days", [])
        self._samples: list[tuple[float, float]] = []
        self._now = 0.0

    def as_dict(self) -> dict:
        return {"sun_days": self.sun_days}

    def update(self, system: dict, now: float) -> None:
        self._now = now
        temp = _number(system.get("L_ambient"))
        if temp is None or temp < -60:
            return
        self._samples = [(t, v) for t, v in self._samples if now - t <= 3600] + [(now, temp)]
        lowest = min(v for _, v in self._samples)
        if temp > AMBIENT_MAX_PLAUSIBLE or temp - lowest > AMBIENT_MAX_RISE_PER_HOUR:
            day = int(now // DAY)
            if day not in self.sun_days:
                self.sun_days.append(day)
        today = int(now // DAY)
        self.sun_days = [d for d in self.sun_days if today - d < AMBIENT_WINDOW_DAYS]

    def findings(self) -> list[dict]:
        if len(self.sun_days) >= AMBIENT_SUN_DAYS:
            return [_finding(OUTSIDE_SENSOR_SUN, STATUS_NOTICE, len(self.sun_days))]
        return []


class HeatPumpHealth:
    """Heat pump (`wp1`, ...): compressor cycling. Experimental."""

    def __init__(self, stored: Optional[dict] = None) -> None:
        stored = stored or {}
        self.cycling = CounterRate(stored.get("cycling"))
        self.cycle_avg: Optional[float] = stored.get("cycle_avg")
        self._running_since: Optional[float] = None
        self._was_running: Optional[bool] = None
        self._now = 0.0

    def as_dict(self) -> dict:
        return {"cycling": self.cycling.snapshots, "cycle_avg": self.cycle_avg}

    @property
    def starts_per_day(self) -> Optional[float]:
        return _rate(self.cycling.deltas(self._now))

    @property
    def starts_per_day_display(self) -> Optional[float]:
        return _rate(self.cycling.deltas(self._now, MIN_DISPLAY_DAYS))

    def update(self, wp: dict, now: float) -> None:
        self._now = now
        self.cycling.update(now, _number(wp.get("L_activation_count")))
        compressor = _number(wp.get("L_compressor_act"))
        if compressor is None:
            return
        running = compressor > 0
        if running and self._was_running is False:
            self._running_since = now
        elif not running and self._running_since is not None:
            seconds = now - self._running_since
            self._running_since = None
            if 0 < seconds <= MAX_CYCLE_SECONDS:
                minutes = seconds / 60.0
                self.cycle_avg = round(
                    minutes
                    if self.cycle_avg is None
                    else self.cycle_avg + IGNITION_AVG_ALPHA * (minutes - self.cycle_avg),
                    1,
                )
        self._was_running = running

    def findings(self) -> list[dict]:
        starts, runtime = self.starts_per_day, self.cycle_avg
        status = None
        if (starts or 0) > WP_STARTS_INEFFICIENT or (
            runtime is not None and runtime < WP_RUNTIME_INEFFICIENT_MIN
        ):
            status = STATUS_INEFFICIENT
        elif (starts or 0) > WP_STARTS_NOTICE or (
            runtime is not None and runtime < WP_RUNTIME_NOTICE_MIN
        ):
            status = STATUS_NOTICE
        if not status:
            return []
        parts = [f"{starts:.1f}/d"] if starts is not None else []
        if runtime is not None:
            parts.append(f"{runtime:.0f} min/run")
        return [_finding(HEAT_PUMP_SHORT_CYCLING, status, ", ".join(parts), experimental=True)]


class MessageLog:
    """Persistent log of boiler messages and fault states, with dedup."""

    def __init__(self, stored: Optional[dict] = None) -> None:
        stored = stored or {}
        self.history: list[dict] = stored.get("history", [])
        self.count: int = stored.get("count", 0)
        self._seen: list[str] = stored.get("seen", [])
        self.active: list[dict] = []
        # Heaters in fault at the last update; persisted so a restart during a
        # fault does not log it a second time.
        self._faulted: set[str] = set(stored.get("faulted", []))

    def as_dict(self) -> dict:
        return {
            "history": self.history,
            "count": self.count,
            "seen": self._seen,
            "faulted": sorted(self._faulted),
        }

    @property
    def last(self) -> Optional[dict]:
        return self.history[0] if self.history else None

    def update(
        self, errors: Any, heaters: dict[str, HeaterHealth], state_texts: dict[str, str], now_iso: str
    ) -> list[dict]:
        """Record new boiler messages and fault transitions; return the new entries."""
        new: list[dict] = []
        self.active = []
        if isinstance(errors, dict):
            for key in sorted(errors):
                message = parse_message(errors[key])
                if not message:
                    continue
                self.active.append(message)
                seen_key = f"{message['time']}|{message['code']}|{message['text']}"
                if seen_key not in self._seen:
                    self._remember(seen_key)
                    new.append({**message, "source": "boiler", "logged": now_iso})

        for name, heater in heaters.items():
            faulted = STATE_FAULT in heater.states
            if faulted and name not in self._faulted:
                new.append(
                    {"time": now_iso, "text": state_texts.get(name) or "Störung", "code": None,
                     "source": name, "logged": now_iso}
                )
            (self._faulted.add if faulted else self._faulted.discard)(name)

        for entry in new:
            self.history.insert(0, entry)
        del self.history[HISTORY_SIZE:]
        self.count += len(new)
        return new

    def findings(self) -> list[dict]:
        return [_finding(BOILER_MESSAGE, STATUS_WARNING, m["text"], message_code=m["code"]) for m in self.active]

    def _remember(self, key: str) -> None:
        self._seen.append(key)
        del self._seen[:-SEEN_KEYS_SIZE]


def overall_status(findings: list[dict], learning: bool) -> str:
    if not findings:
        return STATUS_LEARNING if learning else STATUS_OK
    return max((f["status"] for f in findings), key=STATUS_OPTIONS.index)


def is_problem(status: str) -> bool:
    return STATUS_OPTIONS.index(status) >= STATUS_OPTIONS.index(PROBLEM_FROM)


class Diagnosis:
    """All checks of one installation; plain Python, fed with API responses."""

    def __init__(self, stored: Optional[dict] = None, language: str = "en") -> None:
        stored = stored or {}
        language = (language or "en").split("-")[0]
        self.language = language if language in MESSAGES else "en"
        self.messages = MessageLog(stored.get("messages"))
        self.heaters = {n: HeaterHealth(d) for n, d in stored.get("heaters", {}).items()}
        self.heat_pumps = {n: HeatPumpHealth(d) for n, d in stored.get("heat_pumps", {}).items()}
        self.ambient = AmbientHealth(stored.get("ambient"))
        self.circuits: dict[str, CircuitHealth] = {}
        self.curves = {n: CurveHealth(d) for n, d in stored.get("curves", {}).items()}
        self.has_ambient = False
        self._state_texts: dict[str, str] = {}
        self._announced: set[str] = set(stored.get("announced", []))

    def as_dict(self) -> dict:
        return {
            "messages": self.messages.as_dict(),
            "heaters": {n: h.as_dict() for n, h in self.heaters.items()},
            "heat_pumps": {n: h.as_dict() for n, h in self.heat_pumps.items()},
            "ambient": self.ambient.as_dict(),
            "curves": {n: c.as_dict() for n, c in self.curves.items()},
            "announced": sorted(self._announced),
        }

    def heater(self, name: str) -> HeaterHealth:
        return self.heaters.setdefault(name, HeaterHealth())

    def heat_pump(self, name: str) -> HeatPumpHealth:
        return self.heat_pumps.setdefault(name, HeatPumpHealth())

    def curve(self, name: str) -> CurveHealth:
        return self.curves.setdefault(name, CurveHealth())

    def update(self, data: dict, now: float, now_iso: str) -> tuple[list[dict], list[dict]]:
        """Feed one API response; return (new messages, finding changes)."""
        system = data.get("system")
        ambient = _number(system.get("L_ambient")) if isinstance(system, dict) else None
        source = source_temperature(data)
        for name, values in data.items():
            if not isinstance(values, dict):
                continue
            if re.fullmatch(r"pe\d+", name):
                self.heater(name).update(values, now)
                self._state_texts[name] = " ".join(str(get_api_value(values.get("L_statetext")) or "").split())
            elif re.fullmatch(r"hk\d+", name):
                self.circuits.setdefault(name, CircuitHealth()).update(values, now)
                if has_curve_inputs(values, system):
                    self.curve(name).update(values, ambient, source, now)
            elif re.fullmatch(r"wp\d+", name):
                self.heat_pump(name).update(values, now)
            elif name == "system":
                self.has_ambient = "L_ambient" in values
                self.ambient.update(values, now)

        new_messages = self.messages.update(data.get("error"), self.heaters, self._state_texts, now_iso)
        return new_messages, self._finding_changes()

    def findings(self) -> list[dict]:
        found = [dict(f, component="error") for f in self.messages.findings()]
        for name, heater in self.heaters.items():
            found += [dict(f, component=name) for f in heater.findings(self._state_texts.get(name, ""))]
        for name, circuit in self.circuits.items():
            found += [dict(f, component=name) for f in circuit.findings()]
        for name, pump in self.heat_pumps.items():
            found += [dict(f, component=name) for f in pump.findings()]
        if self.has_ambient:
            found += [dict(f, component="system") for f in self.ambient.findings()]
        texts = MESSAGES[self.language]
        for f in found:
            f["message"] = texts[f["code"]].format(value=f["value"])
        found.sort(key=lambda f: STATUS_OPTIONS.index(f["status"]), reverse=True)
        return found

    @property
    def status(self) -> str:
        return overall_status(self.findings(), any(h.learning for h in self.heaters.values()))

    def _finding_changes(self) -> list[dict]:
        """Findings that appeared or cleared since the last update."""
        current = {f"{f['component']}|{f['code']}": f for f in self.findings()}
        changes = [dict(f, active=True) for key, f in current.items() if key not in self._announced]
        for key in self._announced - current.keys():
            component, code = key.split("|", 1)
            changes.append({"component": component, "code": code, "active": False})
        self._announced = set(current)
        return changes


def notification_for(
    change: dict, hub_name: str, language: str, entry_id: str
) -> Optional[tuple[str, str, str]]:
    """(notification_id, title, message) for a finding that appeared, else None.

    The id is fixed per component and code, so a finding that clears and comes
    back replaces its notification instead of stacking a second one. Boiler-log
    findings share one key for all messages, so those are notified per message
    by `message_notification` instead.
    """
    if not change.get("active") or change["component"] == "error":
        return None
    titles = NOTIFICATION_TITLES.get(language, NOTIFICATION_TITLES["en"])
    return (
        f"{DOMAIN}_{entry_id}_{change['component']}_{change['code']}",
        f"{hub_name}: {titles.get(change['code'], change['code'])}",
        change["message"],
    )


def message_notification(
    entry: dict, hub_name: str, language: str, entry_id: str
) -> Optional[tuple[str, str, str]]:
    """(notification_id, title, message) for a new boiler-log message, else None.

    Fault entries are skipped: the fault finding already announces them.
    """
    if entry.get("source") != "boiler":
        return None
    title = NOTIFICATION_TITLES.get(language, NOTIFICATION_TITLES["en"])[BOILER_MESSAGE]
    code = entry.get("code")
    return (
        f"{DOMAIN}_{entry_id}_message_{code if code is not None else 'none'}",
        f"{hub_name}: {title}{f' {code}' if code is not None else ''}",
        entry["text"],
    )


class DiagnosisMonitor:
    """Feeds hub updates into `Diagnosis`, persists it and fires events."""

    def __init__(self, hass, hub, entry_id: str, hub_name: str, notify: bool = True) -> None:
        from homeassistant.helpers.storage import Store

        self._hass = hass
        self._hub = hub
        self._hub_name = hub_name
        self._notify = notify
        self._entry_id = entry_id
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.diagnosis.{entry_id}")
        self.diagnosis = Diagnosis(language=hass.config.language)
        self._last_save = 0.0
        self._history_task = None
        self._curve_history_task = None
        self._history_ready = False  # set once the entities exist (async_load_history)

    async def async_start(self) -> None:
        stored = await self._store.async_load()
        self.diagnosis = Diagnosis(stored, self._hass.config.language)
        self._hub.async_add_pellematic_sensor(self._handle_update)
        if self._hub.data:
            self._handle_update()  # the hub pre-fetched: no need to wait a poll

    async def async_stop(self) -> None:
        self._hub.async_remove_pellematic_sensor(self._handle_update)
        for task in (self._history_task, self._curve_history_task):
            if task and not task.done():
                task.cancel()
        await self._store.async_save(self.diagnosis.as_dict())

    def maintenance_done(self, heater: str) -> None:
        from homeassistant.util import dt as dt_util

        self.diagnosis.heater(heater).maintenance_done(dt_util.utcnow().timestamp())
        self._save_soon()

    def _save_soon(self) -> None:
        self._last_save = time.monotonic()
        self._store.async_delay_save(self.diagnosis.as_dict, 1)

    def _handle_update(self) -> None:
        from homeassistant.components import persistent_notification
        from homeassistant.util import dt as dt_util

        now = dt_util.utcnow()
        messages, changes = self.diagnosis.update(
            self._hub.data or {}, now.timestamp(), dt_util.as_local(now).isoformat()
        )
        notifications = []
        for entry in messages:
            _LOGGER.warning("Ökofen %s: %s", self._hub_name, entry["text"])
            self._hass.bus.async_fire(EVENT_MESSAGE, {"hub": self._hub_name, **entry})
            notifications.append(
                message_notification(entry, self._hub_name, self.diagnosis.language, self._entry_id)
            )
        for change in changes:
            self._hass.bus.async_fire(EVENT_FINDING, {"hub": self._hub_name, **change})
            notifications.append(
                notification_for(change, self._hub_name, self.diagnosis.language, self._entry_id)
            )
        if self._notify:
            for notification in filter(None, notifications):
                notification_id, title, message = notification
                persistent_notification.async_create(self._hass, message, title, notification_id)
        if messages or changes or time.monotonic() - self._last_save >= SAVE_INTERVAL_SECONDS:
            self._save_soon()
        self._seed_curves_if_needed()

    def _seed_curves_if_needed(self) -> None:
        """Start the curve seeding for circuits that showed up after setup (boiler was unreachable)."""
        if not self._history_ready or (self._curve_history_task and not self._curve_history_task.done()):
            return
        if any(not curve.history_checked for curve in self.diagnosis.curves.values()):
            self._curve_history_task = self._hass.async_create_background_task(
                self._async_seed_curves_from_history(), f"{DOMAIN} diagnosis curve history"
            )


    def async_load_history(self) -> None:
        """Seed the flue-gas baseline and the heating curves from the recorder once the entities exist."""
        self._history_task = self._hass.async_create_background_task(
            self._async_seed_from_history(), f"{DOMAIN} diagnosis history"
        )
        self._history_ready = True
        self._seed_curves_if_needed()

    async def _async_seed_curves_from_history(self) -> None:
        """Give each heating circuit its curve at once, from the hourly statistics.

        Once per circuit: after this the curve lives on what the hub delivers,
        and replaying the same weeks again would count them twice.
        """
        curves = {name: curve for name, curve in self.diagnosis.curves.items() if not curve.history_checked}
        if not curves:
            return
        try:
            await self._async_read_curve_history(curves)
        except Exception:  # noqa: BLE001 - history is a bonus, live learning still works
            _LOGGER.debug("Ökofen %s: no heating-curve history available", self._hub_name, exc_info=True)
        # Not reached when the task is cancelled (unload, restart): the next start tries again.
        for curve in curves.values():
            curve.history_checked = True
        self._save_soon()
        self._hub.async_notify_listeners()

    async def _async_read_curve_history(self, curves: dict) -> None:
        if "recorder" not in self._hass.config.components:
            return
        from datetime import timedelta

        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder.statistics import statistics_during_period
        from homeassistant.helpers import entity_registry as er
        from homeassistant.util import dt as dt_util

        registry = er.async_get(self._hass)
        prefix = self._hub_name.lower()
        data = self._hub.data or {}

        def entity_id(component: str, key: str) -> Optional[str]:
            return registry.async_get_entity_id("sensor", DOMAIN, f"{prefix}_{component}_{key}")

        def components(kind: str) -> list[str]:
            return [n for n, v in data.items() if isinstance(v, dict) and re.fullmatch(rf"{kind}\d+", n)]

        # Same choice as source_temperature(): buffers if there are any.
        if components("pu"):
            source_ids = [entity_id(name, "L_tpo_act") for name in components("pu")]
        else:
            source_ids = [entity_id(name, "L_temp_act") for name in components("pe")]
            source_ids += [entity_id(name, "L_temp_flow_is") for name in components("wp")]
        sources_known = all(source_ids)
        ambient_id = entity_id("system", "L_ambient")

        recorder = get_instance(self._hass)
        await recorder.async_db_ready
        now = dt_util.utcnow()
        for name, curve in curves.items():
            ids = {
                "ambient": ambient_id,
                "room_set": entity_id(name, "L_roomtemp_set"),
                "flow_set": entity_id(name, "L_flowtemp_set"),
                "flow_act": entity_id(name, "L_flowtemp_act"),
            }
            if not all(ids.values()):
                continue
            wanted = set(ids.values()) | ({i for i in source_ids} if sources_known else set())
            stats = await recorder.async_add_executor_job(
                statistics_during_period, self._hass, now - timedelta(days=CURVE_HISTORY_DAYS),
                now, wanted, "hour", None, {"mean"},
            )

            def rows(statistic_id: str) -> list[tuple[float, float]]:
                return [
                    (row["start"], row["mean"])
                    for row in stats.get(statistic_id, [])
                    if row.get("mean") is not None
                ]

            history = {key: rows(statistic_id) for key, statistic_id in ids.items()}
            if sources_known and source_ids:
                # The coolest source of each hour, and only hours every source reported.
                per_source = [dict(rows(statistic_id)) for statistic_id in source_ids]
                history["source"] = [
                    (start, min(series[start] for series in per_source))
                    for start in per_source[0]
                    if all(start in series for series in per_source)
                ]
            hours = seed_curve_from_history(curve, history)
            if hours:
                _LOGGER.info(
                    "Ökofen %s %s: heating curve seeded from %d hours of history",
                    self._hub_name, name, hours,
                )

    async def _async_seed_from_history(self) -> None:
        """Take the flue-gas baseline from the recorder's long-term statistics."""
        heaters = {
            name: heater
            for name, heater in self.diagnosis.heaters.items()
            if heater.has_flue_gas and not heater.history_checked
        }
        if not heaters or "recorder" not in self._hass.config.components:
            return
        from datetime import timedelta

        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder.statistics import statistics_during_period
        from homeassistant.helpers import entity_registry as er
        from homeassistant.util import dt as dt_util

        registry = er.async_get(self._hass)
        prefix = self._hub_name.lower()

        def entity_id(heater: str, key: str) -> Optional[str]:
            return registry.async_get_entity_id("sensor", DOMAIN, f"{prefix}_{heater}_{key}")

        try:
            recorder = get_instance(self._hass)
            await recorder.async_db_ready
            now = dt_util.utcnow()
            for name, heater in heaters.items():
                fan_id, modulation_id = entity_id(name, "L_fluegas"), entity_id(name, "L_modulation")
                if not fan_id or not modulation_id:
                    continue
                stats = await recorder.async_add_executor_job(
                    statistics_during_period, self._hass, now - timedelta(days=HISTORY_DAYS),
                    now, {fan_id, modulation_id}, "hour", None, {"mean"},
                )

                def rows(statistic_id: str) -> list[tuple[float, float]]:
                    return [
                        (row["start"], row["mean"])
                        for row in stats.get(statistic_id, [])
                        if row.get("mean") is not None
                    ]

                result = baseline_from_history(rows(fan_id), rows(modulation_id), now.timestamp())
                if result is None:
                    continue
                baseline, recent, hours = result
                if heater.seed_from_history(baseline, recent):
                    _LOGGER.info(
                        "Ökofen %s %s: flue-gas baseline %.1f %% from %d full-load hours of history",
                        self._hub_name, name, baseline, hours,
                    )
                self._save_soon()
        except Exception:  # noqa: BLE001 - history is a bonus, live learning still works
            _LOGGER.debug("Ökofen %s: no flue-gas history available", self._hub_name, exc_info=True)
            return
        self._hub.async_notify_listeners()


def utc_iso(timestamp: Optional[float]) -> Optional[str]:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
