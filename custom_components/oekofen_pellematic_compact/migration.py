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

_LOGGER = logging.getLogger(__name__)

LEGACY_BINARY_SENSOR_REPAIR_ID = "legacy_binary_sensors_under_sensor_domain"
# Flag stored in entry.data when V2→V3 binary-sensor domain migration is pending.
# Set during async_migrate_entry (where hub.data isn't available yet) and consumed
# by async_setup_entry after the hub has fetched API data. Cleared on success.
PENDING_BINARY_SENSOR_DOMAIN_MIGRATION_KEY = "pending_binary_sensor_domain_migration"

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


async def async_migrate_binary_sensor_domain(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> Tuple[int, List[str]]:
    """Move binary-sensor entities from the `sensor` domain to `binary_sensor`.

    Until config version 3, binary sensors were created by sensor.py and ended
    up under the `sensor` domain (entity_id ``sensor.<...>``). This function
    renames matching registry entries to ``binary_sensor.<...>``.

    Identification strategy:

    - **Safe path:** match by ``unique_id``. We run discovery against the
      current API data and build the set of unique_ids the new
      ``PellematicBinarySensor`` would produce. Any registry entry whose
      domain is ``sensor`` AND whose ``unique_id`` is in that set is renamed.
      This covers v4.0+ installs cleanly.

    - **Legacy path:** for pre-4.0 installs with translated/legacy
      ``unique_id`` values (e.g. ``pellematic_pellematic_1_chaud_ex_ak``) the
      safe match fails. We don't rename those automatically — instead we
      collect them and surface a Repairs issue with actionable steps.

    Returns:
        A tuple of (renamed_count, legacy_entity_ids).
    """
    from .const import DOMAIN
    from .dynamic_discovery import discover_all_entities

    hub_data = hass.data.get(DOMAIN, {}).get(entry.data.get("name"), {})
    hub = hub_data.get("hub")
    api_data = getattr(hub, "data", None) if hub else None

    if not api_data:
        _LOGGER.debug(
            "V2→V3: No API data available yet, skipping binary-sensor domain migration"
        )
        return 0, []

    discovered = discover_all_entities(api_data)
    hub_name = entry.data.get("name", "")
    expected_unique_ids = {
        f"{hub_name.lower()}_{sensor_def['component']}_{sensor_def['key']}"
        for sensor_def in discovered["binary_sensors"]
    }

    entity_reg = er.async_get(hass)
    entries = er.async_entries_for_config_entry(entity_reg, entry.entry_id)

    renamed = 0
    legacy_candidates: List[str] = []

    for ent in entries:
        if ent.domain != "sensor":
            continue

        if ent.unique_id in expected_unique_ids:
            object_id = ent.entity_id.split(".", 1)[1]
            target_entity_id = f"binary_sensor.{object_id}"

            if entity_reg.async_get(target_entity_id) is not None:
                _LOGGER.warning(
                    "V2→V3: Target %s already exists, skipping rename of %s",
                    target_entity_id,
                    ent.entity_id,
                )
                continue

            entity_reg.async_update_entity(
                ent.entity_id, new_entity_id=target_entity_id
            )
            _LOGGER.info(
                "V2→V3: Renamed %s → %s (unique_id preserved)",
                ent.entity_id,
                target_entity_id,
            )
            renamed += 1
        elif _looks_like_legacy_binary_sensor(ent.unique_id, ent.entity_id):
            legacy_candidates.append(ent.entity_id)

    if renamed:
        _LOGGER.info(
            "V2→V3: Migrated %d binary sensors from sensor.* to binary_sensor.*",
            renamed,
        )

    if legacy_candidates:
        await _create_legacy_repair_issue(hass, entry, legacy_candidates)

    return renamed, legacy_candidates


# Object-ID suffixes that strongly indicate a binary-sensor key. Used to spot
# pre-4.0 legacy entity IDs whose unique_id no longer matches modern discovery.
#
# Matching is suffix-based (object_id.endswith(suffix)) — substring matching
# would false-positive on, e.g., `_l_pump_release` (a temperature setpoint).
_LEGACY_BINARY_KEY_SUFFIXES = (
    "_l_pump",
    "_l_ak",
    "_l_br",
    "_l_not",
    "_l_stb",
    "_l_usb_stick",
    "_l_forecast_today",
    # German/French translated remnants (best-effort for v3.x installs)
    "_pompe",
    "_pumpe",
    "_brenner_kontakt",
    "_contact_bruleur",
    "_emergency_stop",
    "_safety_thermostat",
    "_chaud_ex_ak",
)


def _looks_like_legacy_binary_sensor(unique_id: str, entity_id: str) -> bool:
    """Heuristic: spot pre-4.0 entity IDs that likely belonged in binary_sensor.

    Uses object_id suffix matching (not substring) so that keys like
    ``_l_pump_release`` (a temperature setpoint) are not falsely flagged just
    because they contain a known binary-sensor suffix as an infix.
    """
    object_id = entity_id.split(".", 1)[1] if "." in entity_id else entity_id
    object_id_lower = object_id.lower()
    return any(object_id_lower.endswith(s) for s in _LEGACY_BINARY_KEY_SUFFIXES)


async def _create_legacy_repair_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
    legacy_entity_ids: List[str],
) -> None:
    """Surface a Repairs issue listing legacy entities the user should clean up."""
    try:
        from homeassistant.helpers import issue_registry as ir
    except ImportError:
        _LOGGER.debug("issue_registry not available; skipping Repairs issue")
        return

    from .const import DOMAIN

    listed = "\n".join(f"- `{eid}`" for eid in sorted(legacy_entity_ids)[:20])
    if len(legacy_entity_ids) > 20:
        listed += f"\n- ...and {len(legacy_entity_ids) - 20} more"

    try:
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"{LEGACY_BINARY_SENSOR_REPAIR_ID}_{entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=LEGACY_BINARY_SENSOR_REPAIR_ID,
            translation_placeholders={"entity_list": listed},
        )
        _LOGGER.info(
            "V2→V3: Created Repairs issue for %d legacy binary-sensor entities",
            len(legacy_entity_ids),
        )
    except Exception as e:
        _LOGGER.debug("Could not create Repairs issue: %s", e)
