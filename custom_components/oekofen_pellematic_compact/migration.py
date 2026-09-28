"""Entity ID migration helper for Ökofen Pellematic Compact integration.

This module handles one-time migration of entity IDs from older versions
to preserve user automations and dashboards.
"""

import logging
import re
from typing import Dict, List, Tuple
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

_LOGGER = logging.getLogger(__name__)

LEGACY_BINARY_SENSOR_REPAIR_ID = "legacy_binary_sensors_under_sensor_domain"

# Version where object_id was introduced
MIGRATION_FROM_VERSION = "4.0.0"
MIGRATION_MARKER = "migrated_entity_ids"
# Keys stored in config entry data to suppress repeated notifications
ENTITY_WARNING_SHOWN_KEY = "entity_id_warning_shown"
MIGRATION_NOTIFICATION_SHOWN_KEY = "migration_notification_shown"


def _generate_old_entity_id_patterns() -> List[Tuple[str, str, str]]:
    """Generate patterns for old entity IDs that might need migration.
    
    Returns:
        List of tuples (platform, old_pattern, new_component_prefix)
        where old_pattern is a regex pattern to match old entity IDs
        and new_component_prefix is the new component prefix to use.
    """
    patterns = []
    
    # Common old entity ID patterns that were based on English names
    # Pattern format: (platform, old_regex_pattern, new_component_prefix)
    
    # Pellematic heater sensors: heater_1_xxx -> pe1_xxx
    # Match: sensor.{anything}_heater_{number}_{rest}
    patterns.append(("sensor", r"^sensor\..+_heater_(\d+)_(.+)$", "pe"))
    
    # Heating circuit sensors: heating_circuit_1_xxx -> hk1_xxx
    patterns.append(("sensor", r"^sensor\..+_heating_circuit_(\d+)_(.+)$", "hk"))
    
    # Hot water sensors: hot_water_1_xxx -> ww1_xxx
    patterns.append(("sensor", r"^sensor\..+_hot_water_(\d+)_(.+)$", "ww"))
    
    # Buffer storage sensors: buffer_storage_1_xxx -> pu1_xxx
    patterns.append(("sensor", r"^sensor\..+_buffer_storage_(\d+)_(.+)$", "pu"))
    
    # Climate entities
    patterns.append(("climate", r"^climate\..+_heating_circuit_(\d+)_climate$", "hk"))
    
    return patterns


async def async_migrate_entity_ids(
    hass: HomeAssistant,
    entry_id: str,
    hub_name: str,
) -> int:
    """Migrate entity IDs from old format to new format.
    
    This is a one-time migration that runs when the integration is upgraded.
    It preserves old entity IDs by updating the entity registry to use the
    new object_id format while keeping the same entity_id that users are
    familiar with.
    
    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        hub_name: Name of the hub (integration instance)
        
    Returns:
        Number of entities migrated
    """
    # Check if migration was already done
    data = hass.data.get("oekofen_pellematic_compact", {})
    hub_data = data.get(hub_name, {})
    
    if hub_data.get(MIGRATION_MARKER, False):
        _LOGGER.debug("Entity ID migration already completed for %s", hub_name)
        return 0
    
    entity_reg = er.async_get(hass)
    migrated_count = 0
    
    # Get all entities for this config entry
    entities = er.async_entries_for_config_entry(entity_reg, entry_id)
    
    _LOGGER.info(
        "Starting entity ID migration for %s (%d entities found)",
        hub_name,
        len(entities)
    )
    
    patterns = _generate_old_entity_id_patterns()
    
    for entity in entities:
        entity_id = entity.entity_id
        platform = entity.domain
        matched_old_pattern = False

        # Check each old naming-convention pattern (e.g., heater_1_ -> pe1_)
        for pattern_platform, old_pattern, new_prefix in patterns:
            if platform != pattern_platform:
                continue

            match = re.match(old_pattern, entity_id)
            if not match:
                continue

            # Found a match - this entity needs migration
            # The entity_id will be preserved, but we log the change
            _LOGGER.info(
                "Preserving entity_id '%s' for compatibility (matches old pattern)",
                entity_id
            )
            migrated_count += 1
            matched_old_pattern = True
            break

        # Second pass: detect mixed-case entity IDs (Phase 1 scenario)
        # Only runs when no old naming-convention pattern matched
        if not matched_old_pattern and entity_id != entity_id.lower():
            target_id = entity_id.lower()

            # Duplicate detection: skip rename if lowercase target already exists
            existing = entity_reg.async_get(target_id)
            if existing is not None:
                _LOGGER.warning(
                    "Cannot rename %s to %s: target already exists, skipping",
                    entity_id,
                    target_id,
                )
                continue

            # Safe to rename — only update new_entity_id, never unique_id
            entity_reg.async_update_entity(entity_id, new_entity_id=target_id)
            _LOGGER.info(
                "Renamed entity %s → %s (unique_id preserved)",
                entity_id,
                target_id,
            )
            migrated_count += 1
    
    # Mark migration as complete
    if hub_name not in hass.data.get("oekofen_pellematic_compact", {}):
        hass.data.setdefault("oekofen_pellematic_compact", {})[hub_name] = {}
    
    hass.data["oekofen_pellematic_compact"][hub_name][MIGRATION_MARKER] = True
    
    if migrated_count > 0:
        _LOGGER.info(
            "Entity ID migration completed for %s: %d entity IDs preserved for backwards compatibility",
            hub_name,
            migrated_count
        )

        # Create a persistent notification to inform the user
        try:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "message": (
                        f"**Ökofen Pellematic: Entity ID Migration Complete**\n\n"
                        f"Successfully preserved {migrated_count} entity ID(s) from an older "
                        f"version to keep your automations and dashboards working.\n\n"
                        f"**This notification will not appear again after this restart.**\n\n"
                        f"**Want clean, new-style entity IDs?**\n"
                        f"The preserved IDs use the old naming convention. If you prefer the "
                        f"new-style IDs, you can rename individual entities in *Settings → "
                        f"Entities*, or delete the affected entities there before reloading "
                        f"the integration so they are recreated with updated names.\n\n"
                        f"For more information, see the "
                        f"[Migration Guide](https://github.com/dominikamann/oekofen-pellematic-compact/blob/main/MIGRATION_GUIDE.md)."
                    ),
                    "title": "Ökofen Pellematic Migration",
                    "notification_id": f"oekofen_migration_{hub_name}",
                },
            )
        except Exception as e:
            _LOGGER.debug("Could not create migration notification: %s", e)
    else:
        _LOGGER.debug("No old-format entity IDs found for %s", hub_name)
    
    return migrated_count


async def async_check_and_warn_entity_changes(
    hass: HomeAssistant,
    entry_id: str,
    hub_name: str,
) -> List[str]:
    """Check for potential entity ID changes and warn the user.
    
    This function compares the current entity registry with expected entity IDs
    based on the API data and warns about discrepancies.
    
    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        hub_name: Name of the hub
        
    Returns:
        List of warning messages
    """
    warnings = []
    entity_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_reg, entry_id)
    
    # Group entities by platform
    entities_by_platform: Dict[str, List] = {}
    for entity in entities:
        platform = entity.domain
        entities_by_platform.setdefault(platform, []).append(entity)
    
    # Check for entities with non-standard object_ids
    for platform, platform_entities in entities_by_platform.items():
        for entity in platform_entities:
            # Check if entity_id contains translated words (common issue)
            entity_id_lower = entity.entity_id.lower()
            
            # German words that shouldn't be in entity IDs
            german_indicators = [
                "kesseltemperatur", "temperatur", "raumtemperatur",
                "außentemperatur", "betriebsart", "warmwasser"
            ]
            
            # French words that are NOT also common English words
            french_indicators = [
                "température", "chauffage"
            ]
            
            for word in german_indicators + french_indicators:
                if word in entity_id_lower:
                    warnings.append(
                        f"Entity {entity.entity_id} contains translated text ('{word}'). "
                        f"This may cause issues if the system language changes."
                    )
                    break
    
    # If there are warnings, create a notification
    if warnings and len(warnings) > 0:
        # Limit to first 5 warnings to avoid overwhelming notification
        warning_text = "\n".join(f"- {w}" for w in warnings[:5])
        if len(warnings) > 5:
            warning_text += f"\n\n...and {len(warnings) - 5} more warnings (check logs for details)"
        
        try:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "message": f"**Ökofen Pellematic: Entity ID Warning**\n\n"
                               f"Some entity IDs contain translated text which may cause issues:\n\n"
                               f"{warning_text}\n\n"
                               f"These entities will continue working, but consider renaming them to use standardized IDs.\n\n"
                               f"See the [Migration Guide](https://github.com/dominikamann/oekofen-pellematic-compact/blob/main/MIGRATION_GUIDE.md) for more information.",
                    "title": "Ökofen Pellematic Entity Warning",
                    "notification_id": f"oekofen_entity_warning_{hub_name}",
                },
            )
        except Exception as e:
            _LOGGER.debug("Could not create entity warning notification: %s", e)

    return warnings


# Object-ID suffixes that strongly indicate a binary-sensor key. Used to spot
# pre-4.0 legacy entity IDs whose unique_id no longer matches modern discovery.
#
# Matching is suffix-based (object_id.endswith(suffix)) — substring matching
# would false-positive on, e.g., `_l_pump_release` (a temperature setpoint).
_LEGACY_BINARY_KEY_SUFFIXES = (
    "_l_pump",
    "_l_pummp",  # firmware typo present in real fixtures
    "_l_ak",
    "_l_br",
    "_l_not",
    "_l_stb",
    "_l_usb_stick",
    "_l_forecast_today",
    "_l_batt_enabled",
    "_l_output_mode",
    # German/French translated remnants (best-effort for v3.x installs)
    "_pompe",
    "_pumpe",
    "_brenner_kontakt",
    "_contact_bruleur",
    "_emergency_stop",
    "_safety_thermostat",
    "_chaud_ex_ak",
    # Read-only two-option keys published by the `json.properties` USB trick
    # (discussion #194, fixture api_response_v402b_jsonprops.json) — not part of
    # a stock response, but real installations run with them.
    "_l_cfg_ambient_avg_mode",
    "_l_cfg_auto_extern",
    "_l_cfg_ash_measurement",
    "_l_cfg_cycle_mode",
    "_l_cfg_mixer",
    "_l_cfg_priority",
    "_l_cfg_request_type",
    "_l_cfg_timeprog",
    "_l_ke_burner_request",
    "_l_ash_end_switch",
    "_l_ash_warn_mode",
)


# Maps a legacy object_id suffix back to the API key(s) it could stand for, so
# the suffix verdict can be checked against live API metadata. Translated
# suffixes map to every key they might represent (firmware typo included).
_SUFFIX_TO_API_KEYS = {
    "_l_pump": ("L_pump",),
    "_l_pummp": ("L_pummp",),
    "_l_ak": ("L_ak",),
    "_l_br": ("L_br",),
    "_l_not": ("L_not",),
    "_l_stb": ("L_stb",),
    "_l_usb_stick": ("L_usb_stick",),
    "_l_forecast_today": ("L_forecast_today",),
    "_l_batt_enabled": ("L_batt_enabled",),
    "_l_output_mode": ("L_output_mode",),
    "_pompe": ("L_pump", "L_pummp"),
    "_pumpe": ("L_pump", "L_pummp"),
    "_brenner_kontakt": ("L_ak",),
    "_contact_bruleur": ("L_ak",),
    "_chaud_ex_ak": ("L_ak",),
    "_emergency_stop": ("L_not",),
    "_safety_thermostat": ("L_stb",),
    "_l_cfg_ambient_avg_mode": ("L_cfg_ambient_avg_mode",),
    "_l_cfg_auto_extern": ("L_cfg_auto_extern",),
    "_l_cfg_ash_measurement": ("L_cfg_ash_measurement",),
    "_l_cfg_cycle_mode": ("L_cfg_cycle_mode",),
    "_l_cfg_mixer": ("L_cfg_mixer",),
    "_l_cfg_priority": ("L_cfg_priority",),
    "_l_cfg_request_type": ("L_cfg_request_type",),
    "_l_cfg_timeprog": ("L_cfg_timeprog",),
    "_l_ke_burner_request": ("L_ke_burner_request",),
    "_l_ash_end_switch": ("L_ash_end_switch",),
    "_l_ash_warn_mode": ("L_ash_warn_mode",),
}


def _component_slugs(component_key: str) -> set[str]:
    """Entity-ID slugs a component may appear as (raw key + localized names).

    ``sk1`` → ``{"sk1", "solar_collector_1", "solarkollektor_1", "solaire_1"}``.
    Pre-4.0 entity IDs embedded the *display* name, so the raw key alone is not
    enough to locate the component an orphan belongs to.
    """
    from .dynamic_discovery import (
        COMPONENT_NAMES_TRANSLATIONS,
        get_component_display_name,
    )

    slugs = {component_key.lower()}

    index = 0
    for char in component_key:
        if char.isdigit():
            index = index * 10 + int(char)

    for language in ("en", *COMPONENT_NAMES_TRANSLATIONS):
        display = get_component_display_name(component_key, index, language)
        slug = re.sub(r"[^a-z0-9]+", "_", display.lower()).strip("_")
        if slug:
            slugs.add(slug)

    return slugs


def _looks_like_legacy_binary_sensor(
    entity_id: str, api_data: dict | None = None
) -> bool:
    """Heuristic: spot pre-4.0 entity IDs that likely belonged in binary_sensor.

    Two stages: resolve the ID against the live API response and mirror
    discovery's classification (stage 1), and only if it names nothing we
    recognise fall back to object_id suffix matching (stage 2). Suffix matching
    is never substring matching, so keys like ``_l_pump_release`` (a temperature
    setpoint) are not falsely flagged for containing a known suffix as an infix.

    The suffix alone is ambiguous, though: ``L_pump`` is a genuine on/off
    sensor on ``hk``/``ww``/``circ`` (``format: "0:Aus|1:Ein"``) but a
    speed-modulation percentage on ``sk``/``pu`` (``unit: "%"``, no format).
    Flagging the latter caused an endless repair loop — the flow deleted the
    entity, discovery correctly recreated the same ``sensor.*``, and the issue
    reappeared. So when ``api_data`` is supplied we resolve the orphan back to
    its component/key and let the discovery classifier decide.

    The translated suffixes are ambiguous in a second way (issue #192): a
    legacy object_id carries the whole slugified display text, so the French
    ``pu1.L_pump_release`` ("T démarrage pompe") ends in ``_pompe`` although it
    is a temperature. Resolution therefore matches the component slug anywhere
    in the object_id and maps the *remaining* words back to a concrete API key
    (raw key or slugified ``text``) before classifying.

    Falls back to the pure name heuristic only when no API data is available
    or the entity cannot be resolved to a component/key in it.
    """
    object_id = entity_id.split(".", 1)[1] if "." in entity_id else entity_id
    object_id_lower = object_id.lower()

    # Stage 1: with API data, resolve the ID against the live response and let
    # the discovery classifier decide. This is both stricter and wider than the
    # suffix list: stricter because a temperature named "T démarrage pompe"
    # resolves to `L_pump_release`, wider because a binary key whose localized
    # text nobody put in the list ("Brennerkontakt" → `L_br`) is still found.
    if api_data:
        verdict = _classify_against_api(object_id_lower, api_data)
        if verdict is not None:
            return verdict

    matched = [s for s in _LEGACY_BINARY_KEY_SUFFIXES if object_id_lower.endswith(s)]
    if not matched:
        return False

    if not api_data:
        return True

    # Stage 2: the ID named no key in the response (different firmware
    # language, hardware since removed). Fall back to the suffix→key map, which
    # still ties the verdict to live metadata where the component exists.
    # Longest suffix wins (e.g. prefer "_l_pump_release" style specificity).
    for suffix in sorted(matched, key=len, reverse=True):
        for component_key, component_data in api_data.items():
            if not isinstance(component_data, dict):
                continue
            remainder = _remainder_after_component_slug(
                object_id_lower, component_key, suffix
            )
            if remainder is None:
                continue

            # Resolved to a component — mirror discovery's own classification,
            # including its normalization of bare values (old firmware sends
            # `0` instead of a metadata dict, which yields no `format` and so
            # can only ever become a sensor).
            #
            # The suffix says which key the translated word stood for
            # ("solar_collector_1_pompe" → L_pump, even though this firmware
            # calls it "Pumpe").
            candidates = [
                (k, _normalize_api_def(component_data[k]))
                for k in _SUFFIX_TO_API_KEYS.get(suffix, ())
                if k in component_data
            ]
            if candidates:
                return any(
                    _discovery_makes_binary_sensor(k, d) for k, d in candidates
                )

    return True


def _classify_against_api(object_id_lower: str, api_data: dict) -> bool | None:
    """Resolve a legacy object_id to a datapoint in the live API response.

    Returns discovery's verdict for it, or None when the ID names no component
    or no key we recognise — then the caller falls back to the name heuristic.
    """
    for component_key, component_data in api_data.items():
        if not isinstance(component_data, dict):
            continue
        remainder = _remainder_after_component_slug(object_id_lower, component_key)
        if remainder is None:
            continue
        candidates = _api_keys_for_name(component_data, remainder)
        if candidates:
            return any(
                _discovery_makes_binary_sensor(key, data) for key, data in candidates
            )
    return None


def _discovery_makes_binary_sensor(key: str, data: dict) -> bool:
    """Mirror `discover_all_entities`: only read-only (`L_`) two-option fields
    become binary sensors — a *writable* two-option field (``heat_once``,
    ``oekomode``) becomes a select, so it must never be reported as an orphan.
    """
    from .dynamic_discovery import IGNORE_KEYS, is_binary_sensor

    if key in IGNORE_KEYS or not key.startswith("L_"):
        return False
    if "val" not in data:
        return False  # discovery skips these outright
    return is_binary_sensor(data)


def _normalize_api_def(value) -> dict:
    """Wrap bare old-firmware values the way discovery does."""
    return value if isinstance(value, dict) else {"val": value}


def _remainder_after_component_slug(
    object_id_lower: str, component_key: str, suffix: str | None = None
) -> str | None:
    """Return the object_id part that follows the component slug, or None.

    ``("chaudiere_buffer_storage_1_t_demarrage_pompe", "pu1")`` →
    ``"t_demarrage_pompe"``. The slug must appear as a whole ``_``-delimited
    segment group; when ``suffix`` is given the remainder must also end with
    it, so an unrelated component cannot claim the ID. Longest slug first, so a
    localized name wins over the bare key when both happen to appear.
    """
    padded = f"_{object_id_lower}"
    for slug in sorted(_component_slugs(component_key), key=len, reverse=True):
        needle = f"_{slug}_"
        index = padded.rfind(needle)
        if index == -1:
            continue
        remainder = padded[index + len(needle):]
        if suffix is None or remainder.endswith(suffix.lstrip("_")):
            return remainder
    return None


def _api_keys_for_name(component_data: dict, name: str) -> list:
    """``(key, definition)`` pairs in a component whose key or display text
    slugifies to ``name`` — how legacy IDs referenced a datapoint before v4.0.
    """
    from homeassistant.util import slugify

    matches = []
    for key, value in component_data.items():
        if key.lower() == name:
            matches.append((key, _normalize_api_def(value)))
            continue
        text = value.get("text") if isinstance(value, dict) else None
        if isinstance(text, str) and text and slugify(text) == name:
            matches.append((key, _normalize_api_def(value)))
    return matches


def get_api_data_for_entry(hass: HomeAssistant, entry: ConfigEntry) -> dict | None:
    """Best-effort lookup of the hub's last API response for an entry.

    Returns None when the hub has not fetched yet — callers then fall back to
    the name-only heuristic.
    """
    from .const import DOMAIN

    try:
        hub = hass.data[DOMAIN][entry.data["name"]]["hub"]
    except (KeyError, TypeError):
        return None
    return getattr(hub, "data", None) or None


async def async_refresh_legacy_binary_sensor_repair_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> int:
    """Detect orphan sensor.* entries that should live under binary_sensor.*
    and surface a fixable Repairs issue.

    Runs on every async_setup_entry. Uses object_id suffix matching against
    the known binary-sensor keys (L_pump, L_ak, L_br, L_not, L_stb,
    L_usb_stick, L_forecast_today plus French/German translated remnants),
    which covers both v4.0+ orphans and pre-4.0 translated IDs.

    The user fixes the issue from the Repairs UI; see repairs.py for the
    flow that deletes the listed entries and triggers a reload so the
    binary_sensor platform recreates them.

    Returns the number of orphan entities currently flagged.
    """
    from .const import DOMAIN

    entity_reg = er.async_get(hass)
    entries = er.async_entries_for_config_entry(entity_reg, entry.entry_id)

    api_data = get_api_data_for_entry(hass, entry)
    orphans = sorted(
        ent.entity_id
        for ent in entries
        if ent.domain == "sensor"
        and _looks_like_legacy_binary_sensor(ent.entity_id, api_data)
    )

    issue_id = f"{LEGACY_BINARY_SENSOR_REPAIR_ID}_{entry.entry_id}"

    if not orphans:
        try:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
        except Exception as e:
            _LOGGER.debug("Could not delete Repairs issue: %s", e)
        return 0

    listed = "\n".join(f"- `{eid}`" for eid in orphans[:20])
    if len(orphans) > 20:
        listed += f"\n- ...and {len(orphans) - 20} more"

    try:
        # data only carries scalar values so we stay within HA's typed
        # contract (dict[str, str|int|float|None]). The flow re-queries the
        # registry on submit to get the current orphan list.
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key=LEGACY_BINARY_SENSOR_REPAIR_ID,
            translation_placeholders={
                "count": str(len(orphans)),
                "entity_list": listed,
            },
            data={"entry_id": entry.entry_id},
        )
    except Exception as e:
        _LOGGER.debug("Could not refresh Repairs issue: %s", e)

    return len(orphans)
