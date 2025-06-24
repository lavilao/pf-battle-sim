import json
import os
from typing import List, Optional, Any, Dict # Added Dict and Any
from .combatant import Combatant

class MonsterDatabase:
    """
    Handles persistent storage and retrieval of monster statblocks
    Implements Part 1.2 of the specification
    """

    def __init__(self, database_path: str = "monster_data"):
        self.database_path = database_path
        # It's good practice to ensure the path is absolute or clearly relative to a known location.
        # For now, assuming it's relative to where the script is run or a predefined base.
        # If this script is part of a larger package, constructing path from package root might be better.
        # Example: os.path.join(os.path.dirname(__file__), '..', database_path) if monster_data is sibling to core
        os.makedirs(self.database_path, exist_ok=True)

    def save_monster(self, combatant: Combatant) -> bool:
        """Save a monster template to JSON file"""
        try:
            # Ensure combatant.name is filesystem-safe.
            # Replace spaces with underscores, convert to lowercase.
            # Consider more robust sanitization if names can have special characters.
            safe_name = combatant.name.lower().replace(' ', '_')
            # Basic sanitization for other potentially problematic characters (very basic example)
            safe_name = "".join(c if c.isalnum() or c in ['_', '-'] else '' for c in safe_name)
            if not safe_name: # Handle cases where name becomes empty after sanitization
                safe_name = "unnamed_monster"

            filename = f"{safe_name}.json"
            filepath = os.path.join(self.database_path, filename)

            with open(filepath, 'w') as f:
                json.dump(combatant.to_dict(), f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving monster {combatant.name}: {e}")
            return False

    def load_monster(self, monster_name: str) -> Optional[Combatant]:
        """Load a monster template from JSON file"""
        try:
            # Handle both "Monster Name" and "monster_name.json" formats
            if monster_name.endswith('.json'):
                filename = monster_name
            else:
                # Apply similar sanitization to monster_name for lookup
                safe_name = monster_name.lower().replace(' ', '_')
                safe_name = "".join(c if c.isalnum() or c in ['_', '-'] else '' for c in safe_name)
                if not safe_name: # Should ideally not happen if names are managed well
                    return None
                filename = f"{safe_name}.json"

            filepath = os.path.join(self.database_path, filename)

            if not os.path.exists(filepath):
                # Try original formatting if sanitized one not found, just in case
                if not monster_name.endswith('.json'):
                    original_filename = f"{monster_name.lower().replace(' ', '_')}.json"
                    original_filepath = os.path.join(self.database_path, original_filename)
                    if os.path.exists(original_filepath):
                        filepath = original_filepath
                    else:
                        print(f"Monster file not found: {filepath} (and other variants like {original_filename})")
                        return None
                else: # if it already ended with .json and wasn't found
                    print(f"Monster file not found: {filepath}")
                    return None

            with open(filepath, 'r') as f:
                data = json.load(f)

            # The Combatant.from_dict method should handle creating the object
            combatant = Combatant.from_dict(data)
            # Reset for combat is good practice if this instance is directly used
            combatant.reset_for_combat()

            return combatant
        except Exception as e:
            print(f"Error loading monster {monster_name}: {e}")
            return None

    def list_monsters(self) -> List[str]:
        """List all available monster templates"""
        try:
            files = [f for f in os.listdir(self.database_path) if f.endswith('.json')]
            # Attempt to revert filenames to more readable names
            # Remove .json, replace underscores with spaces, title case
            # This assumes filenames were created by replacing spaces with underscores.
            monster_names = []
            for f in files:
                name_part = f[:-5] # Remove .json
                # A simple heuristic: if it contains underscores, it was likely space-separated.
                # Otherwise, it might have been a single word or CamelCase.
                # This part is tricky without knowing the exact naming convention used for saving.
                # The original code just did replace('_', ' ').title()
                # Let's stick to that for consistency with original behavior.
                readable_name = name_part.replace('_', ' ').title()
                monster_names.append(readable_name)
            return monster_names
        except Exception as e:
            print(f"Error listing monsters: {e}")
            return []

    def delete_monster(self, monster_name: str) -> bool:
        """Delete a monster template"""
        try:
            # Apply similar sanitization as in load_monster to find the file
            if monster_name.endswith('.json'): # Should not happen if called with readable name
                filename_to_delete = monster_name
            else:
                safe_name = monster_name.lower().replace(' ', '_')
                safe_name = "".join(c if c.isalnum() or c in ['_', '-'] else '' for c in safe_name)
                if not safe_name:
                    print(f"Cannot delete monster with invalid name format: {monster_name}")
                    return False
                filename_to_delete = f"{safe_name}.json"

            filepath = os.path.join(self.database_path, filename_to_delete)

            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            else:
                # Try original formatting before giving up
                original_filename = f"{monster_name.lower().replace(' ', '_')}.json"
                original_filepath = os.path.join(self.database_path, original_filename)
                if os.path.exists(original_filepath):
                    os.remove(original_filepath)
                    return True
                else:
                    print(f"Monster file not found for deletion: {filepath} (and other variants like {original_filename})")
                    return False
        except Exception as e:
            print(f"Error deleting monster {monster_name}: {e}")
            return False
