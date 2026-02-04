#!/usr/bin/env python3
"""
Script to clean up old Ökofen entities from Home Assistant entity_registry.

This will remove entities that:
1. Were created with the old naming scheme
2. Have incorrect entity types (e.g., storage_fill_today as number instead of sensor)

BACKUP YOUR ENTITY_REGISTRY FIRST!
"""

import json
import sys
from pathlib import Path

def backup_entity_registry(registry_path):
    """Create a backup of the entity_registry."""
    backup_path = registry_path.with_suffix('.json.backup')
    if registry_path.exists():
        import shutil
        shutil.copy2(registry_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return True
    else:
        print(f"❌ Entity registry not found: {registry_path}")
        return False

def clean_oekofen_entities(registry_path, dry_run=True):
    """Clean old Ökofen entities from entity_registry."""
    
    if not registry_path.exists():
        print(f"❌ File not found: {registry_path}")
        return
    
    with open(registry_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    entities = data.get('data', {}).get('entities', [])
    
    # Find Ökofen entities
    oekofen_entities = [e for e in entities if 'pellematic' in e.get('unique_id', '').lower()]
    
    print(f"\n📊 Found {len(oekofen_entities)} Ökofen entities")
    
    # Entities to remove (old naming scheme or wrong type)
    entities_to_remove = []
    
    for entity in oekofen_entities:
        entity_id = entity.get('entity_id', '')
        unique_id = entity.get('unique_id', '')
        platform = entity.get('platform', '')
        
        # Check for old German-based entity_ids
        if any(word in entity_id for word in ['pelletverbrauch', 'betriebsart', 'fuellstand']):
            entities_to_remove.append({
                'entity_id': entity_id,
                'unique_id': unique_id,
                'platform': platform,
                'reason': 'Old German-based entity_id'
            })
        
        # Check for wrong entity type (storage_fill_* should be sensors, not numbers)
        if entity_id.startswith('number.') and 'storage_fill' in unique_id:
            entities_to_remove.append({
                'entity_id': entity_id,
                'unique_id': unique_id,
                'platform': platform,
                'reason': 'Wrong type: should be sensor, not number'
            })
    
    if entities_to_remove:
        print(f"\n⚠️  Found {len(entities_to_remove)} entities to remove:\n")
        for e in entities_to_remove:
            print(f"   • {e['entity_id']:60} | {e['reason']}")
    else:
        print("\n✅ No old entities found to remove")
        return
    
    if dry_run:
        print(f"\n🔍 DRY RUN: No changes made")
        print(f"\nTo actually remove these entities, run with --apply flag")
    else:
        # Remove entities
        entity_ids_to_remove = {e['entity_id'] for e in entities_to_remove}
        
        new_entities = [e for e in entities if e.get('entity_id') not in entity_ids_to_remove]
        
        data['data']['entities'] = new_entities
        
        # Write back
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✅ Removed {len(entities_to_remove)} entities")
        print(f"\n⚠️  RESTART HOME ASSISTANT to apply changes!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean old Ökofen entities')
    parser.add_argument('--config-dir', type=str, default='config',
                       help='Path to Home Assistant config directory')
    parser.add_argument('--apply', action='store_true',
                       help='Actually remove entities (default is dry-run)')
    
    args = parser.parse_args()
    
    registry_path = Path(args.config_dir) / '.storage' / 'core.entity_registry'
    
    print(f"\n{'='*80}")
    print(f"Ökofen Entity Registry Cleanup")
    print(f"{'='*80}\n")
    
    if not args.apply:
        print("⚠️  DRY RUN MODE (use --apply to actually remove entities)\n")
    
    # Create backup
    if backup_entity_registry(registry_path):
        clean_oekofen_entities(registry_path, dry_run=not args.apply)
