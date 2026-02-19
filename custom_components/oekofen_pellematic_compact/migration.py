"""Entity ID migration helper for Ökofen Pellematic Compact integration.

This module handles one-time migration of entity IDs from older versions
to preserve user automations and dashboards.
"""

import logging
import re
from typing import Dict, List, Tuple
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

# Version where object_id was introduced
MIGRATION_FROM_VERSION = "4.0.0"
MIGRATION_MARKER = "migrated_entity_ids"


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
            "Entity ID migration completed for %s: %d entities renamed",
            hub_name,
            migrated_count
        )
        
        # Create a persistent notification to inform the user
        try:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "message": f"**Ökofen Pellematic: Entity ID Migration Complete**\n\n"
                               f"Successfully renamed {migrated_count} entity ID(s) for backwards compatibility.\n\n"
                               f"Your existing automations and dashboards should continue working without changes.\n\n"
                               f"For more information, see the [Migration Guide](https://github.com/dominikamann/oekofen-pellematic-compact/blob/main/MIGRATION_GUIDE.md).",
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
            
            # French words
            french_indicators = [
                "température", "circuit", "chauffage"
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
