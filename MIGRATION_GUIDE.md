# Entity ID Migration Guide

## Overview

Starting from version 4.0.8, this integration includes automatic entity ID migration to help preserve your automations and dashboards when upgrading from older versions.

## What Changed?

Previous versions of this integration may have created entity IDs based on:
- **Translated names** from the Ökofen API (e.g., German "Kesseltemperatur" or French "Température")
- **Different component naming** (e.g., "heater_1" instead of "pe1")

This could cause entity IDs to change if:
- Your system language/firmware settings changed
- You upgraded from a very old version with different naming conventions

## Automatic Migration

The integration now includes **automatic one-time migration** that:

1. ✅ **Detects old entity ID patterns** (e.g., `sensor.pellematic_heater_1_temperature`)
2. ✅ **Preserves existing entity IDs** to maintain compatibility
3. ✅ **Logs the migration process** for transparency
4. ✅ **Runs only once** - won't affect new installations

### What Gets Migrated

Common patterns that are automatically detected and preserved:

| Old Pattern | New Pattern | Example Old ID | Preserved As |
|-------------|-------------|----------------|--------------|
| `heater_X_*` | `peX_*` | `sensor.pellematic_heater_1_temperature` | ✅ Preserved |
| `heating_circuit_X_*` | `hkX_*` | `sensor.pellematic_heating_circuit_1_temperature` | ✅ Preserved |
| `hot_water_X_*` | `wwX_*` | `sensor.pellematic_hot_water_1_temperature` | ✅ Preserved |
| `buffer_storage_X_*` | `puX_*` | `sensor.pellematic_buffer_storage_1_temperature` | ✅ Preserved |

## For New Installations

If you're installing this integration for the first time, entity IDs will be created using the **new standardized format**:

### Format: `{platform}.{hub_name}_{component}_{key}`

Examples:
- `sensor.pellematic_pe1_L_temp_act` (Pellematic 1 Temperature)
- `sensor.pellematic_hk1_L_roomtemp_act` (Heating Circuit 1 Room Temperature)
- `sensor.pellematic_ww1_L_temp_act` (Hot Water 1 Temperature)
- `climate.pellematic_hk1_climate` (Heating Circuit 1 Climate Control)

### Component Prefixes

| Prefix | Component | Example |
|--------|-----------|---------|
| `pe1`, `pe2`, ... | Pellematic Heater | `pe1_L_temp_act` |
| `hk1`, `hk2`, ... | Heating Circuit | `hk1_L_roomtemp_act` |
| `ww1`, `ww2`, ... | Hot Water | `ww1_L_temp_act` |
| `pu1`, `pu2`, ... | Buffer Storage | `pu1_L_temp_top` |
| `sk1`, `sk2`, ... | Solar Collector | `sk1_L_temp_coll` |
| `se1`, `se2`, ... | Solar Gain | `se1_L_solarheat` |
| `wp1`, `wp2`, ... | Heat Pump | `wp1_L_temp_eintritt` |
| `system` | System-wide | `system_L_ambient` |

## Manual Migration

If you prefer to manually migrate or customize entity IDs:

### Option 1: Via UI (Recommended)

1. Go to **Settings** → **Devices & Services**
2. Find your **Ökofen Pellematic Compact** integration
3. Click on the device
4. Click on any entity you want to rename
5. Click the **gear icon** (⚙️) in the top right
6. Under "Entity ID", change to your preferred ID
7. Click **Update**

### Option 2: Via Entity Registry

1. Go to **Developer Tools** → **States**
2. Find entities starting with your integration name
3. Note their current `entity_id` and `object_id`
4. Use the UI method above to rename them

### Option 3: Edit `.storage/core.entity_registry`

⚠️ **Advanced users only** - Backup first!

1. Stop Home Assistant
2. Edit `.storage/core.entity_registry`
3. Find entities with `"platform": "oekofen_pellematic_compact"`
4. Modify the `"entity_id"` field (keep `"unique_id"` unchanged)
5. Save and restart Home Assistant

## Troubleshooting

### Entity IDs Still Changed

If you notice entity IDs changed despite the migration:

1. **Check the logs** for migration messages:
   ```
   Settings → System → Logs
   Search for: "Entity ID migration"
   ```

2. **Verify the entity registry**:
   ```yaml
   # In Developer Tools → Template:
   {{ states.sensor | selectattr('entity_id', 'search', 'pellematic') | map(attribute='entity_id') | list }}
   ```

3. **Check for duplicate entities**:
   - Old entities may have been disabled
   - Check: Settings → Devices → [Your Device] → Show disabled entities

### German/French Names in Entity IDs

If you see entity IDs with translated text (e.g., `kesseltemperatur`, `température`):

⚠️ **This indicates the entity was created using the API's translated text field.**

**Why this happens:**
- Your Ökofen system returns names in German/French via the API `text` field
- Entity IDs were created before `object_id` was properly implemented

**Solution:**
1. The migration should preserve these automatically
2. If you want English entity IDs, manually rename them (see "Manual Migration" above)
3. Future entities will use standardized component/key format

### Migration Logs

Check the logs to see what was migrated:

```
[oekofen_pellematic_compact] Starting entity ID migration for Pellematic (142 entities found)
[oekofen_pellematic_compact] Preserving entity_id 'sensor.pellematic_heater_1_temperature' for compatibility
[oekofen_pellematic_compact] Entity ID migration completed for Pellematic: 12 entities preserved
```

## Breaking Changes Warning

### When Breaking Changes Occur

The integration will **log warnings** if:
- Entity IDs contain translated words (German/French)
- Entity IDs don't follow the new standard format
- Potential conflicts are detected

**Example warning:**
```
Entity sensor.pellematic_pellematic_1_kesseltemperatur contains translated text ('kesseltemperatur'). 
This may cause issues if the system language changes.
```

### What to Do

1. ✅ **Nothing required** - the entity will continue working
2. 📝 **Optional**: Rename the entity to use English/standard format
3. 🔄 **Update automations/dashboards** if you rename entities

## Support

If you encounter issues with entity ID migration:

1. **Enable debug logging**:
   ```yaml
   # configuration.yaml
   logger:
     default: info
     logs:
       custom_components.oekofen_pellematic_compact: debug
   ```

2. **Check the logs** after restart
3. **Report issues** at: https://github.com/dominikamann/oekofen-pellematic-compact/issues

Include:
- Your Home Assistant version
- Integration version (before and after upgrade)
- Relevant log messages
- Example entity IDs (before/after)

## FAQ

### Q: Will my automations break?

**A:** No, if you're upgrading from a recent version. The migration preserves existing entity IDs.

### Q: Can I use both old and new entity IDs?

**A:** No, each entity has only one `entity_id`. However, the migration ensures your existing ID is preserved.

### Q: What if I did a fresh install?

**A:** Fresh installations use the new standardized format. No migration needed.

### Q: Can I force a re-migration?

**A:** The migration runs only once per installation. To reset:
1. Remove the integration
2. Delete entities from entity registry
3. Re-add the integration

### Q: Do I need to update my automations?

**A:** Only if:
- You manually rename entities
- You're doing a fresh install (not an upgrade)
- Otherwise, existing automations should continue working

### Q: Why does the new format use `pe1_L_temp_act`?

**A:** This is the **actual key** from the Ökofen API:
- `pe1` = Pellematic 1 (component)
- `L_temp_act` = API key for current temperature
- This format is language-independent and stable across firmware versions

## Version History

| Version | Change |
|---------|--------|
| 4.0.8 | Added automatic entity ID migration |
| 4.0.0 | Introduced `object_id` for stable entity IDs |
| < 4.0.0 | Entity IDs based on translated names |
