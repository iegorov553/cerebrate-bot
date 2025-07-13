#!/usr/bin/env python3
"""
Utility script to synchronize translation keys across all language files.
Ensures all languages have the same structure as the reference language (Russian).
"""

import json
from pathlib import Path
from typing import Dict, Any


def load_translations(language: str) -> Dict[str, Any]:
    """Load translation file for given language."""
    file_path = Path(f'bot/i18n/locales/{language}.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_translations(language: str, data: Dict[str, Any]) -> None:
    """Save translation file for given language."""
    file_path = Path(f'bot/i18n/locales/{language}.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sync_structure(reference: Dict[str, Any], target: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """Recursively sync structure from reference to target, preserving existing translations."""
    result = {}
    
    for key, value in reference.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            # Recursive case: nested object
            target_nested = target.get(key, {})
            result[key] = sync_structure(value, target_nested, full_key)
        else:
            # Base case: translation string
            if key in target and target[key]:
                # Keep existing translation
                result[key] = target[key]
                print(f"✅ Kept existing: {full_key}")
            else:
                # Add placeholder for missing translation
                result[key] = f"[TO_TRANSLATE] {value}"
                print(f"➕ Added placeholder: {full_key}")
    
    return result


def main():
    """Main synchronization function."""
    print("🔄 Synchronizing translation files...")
    
    # Load reference language (Russian)
    reference = load_translations('ru')
    print(f"📖 Loaded reference (RU) with structure")
    
    # Sync other languages
    for language in ['en', 'es']:
        print(f"\n🌍 Synchronizing {language.upper()}...")
        
        try:
            target = load_translations(language)
        except FileNotFoundError:
            print(f"⚠️  {language}.json not found, creating from scratch")
            target = {}
        
        # Sync structure
        synced = sync_structure(reference, target)
        
        # Save updated file
        save_translations(language, synced)
        print(f"💾 Saved {language}.json")
    
    print("\n✅ Translation synchronization complete!")
    print("\n📝 Next steps:")
    print("1. Review files and replace [TO_TRANSLATE] placeholders with actual translations")
    print("2. Run tests to verify completeness: pytest tests/test_translation_completeness.py")


if __name__ == '__main__':
    main()