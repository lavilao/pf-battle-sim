from dataclasses import dataclass

@dataclass
class AbilityScores:
    """Represents the six ability scores"""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    # Temporary modifiers (from spells, etc.)
    temp_str: int = 0
    temp_dex: int = 0
    temp_con: int = 0
    temp_int: int = 0
    temp_wis: int = 0
    temp_cha: int = 0

    def get_modifier(self, ability: str) -> int:
        """Get the modifier for an ability score"""
        # Map short names to full attribute names
        ability_map = {
            "str": "strength", "dex": "dexterity", "con": "constitution",
            "int": "intelligence", "wis": "wisdom", "cha": "charisma",
            "strength": "strength", "dexterity": "dexterity", "constitution": "constitution",
            "intelligence": "intelligence", "wisdom": "wisdom", "charisma": "charisma"
        }

        temp_map = {
            "str": "temp_str", "dex": "temp_dex", "con": "temp_con",
            "int": "temp_int", "wis": "temp_wis", "cha": "temp_cha",
            "strength": "temp_str", "dexterity": "temp_dex", "constitution": "temp_con",
            "intelligence": "temp_int", "wisdom": "temp_wis", "charisma": "temp_cha"
        }

        full_ability = ability_map.get(ability.lower(), ability)
        temp_attr = temp_map.get(ability.lower(), f"temp_{ability[:3]}")

        total_score = getattr(self, full_ability) + getattr(self, temp_attr)
        return (total_score - 10) // 2

    def get_total_score(self, ability: str) -> int:
        """Get the total ability score including temporary modifiers"""
        # Map short names to full attribute names
        ability_map = {
            "str": "strength", "dex": "dexterity", "con": "constitution",
            "int": "intelligence", "wis": "wisdom", "cha": "charisma",
            "strength": "strength", "dexterity": "dexterity", "constitution": "constitution",
            "intelligence": "intelligence", "wisdom": "wisdom", "charisma": "charisma"
        }

        temp_map = {
            "str": "temp_str", "dex": "temp_dex", "con": "temp_con",
            "int": "temp_int", "wis": "temp_wis", "cha": "temp_cha",
            "strength": "temp_str", "dexterity": "temp_dex", "constitution": "temp_con",
            "intelligence": "temp_int", "wisdom": "temp_wis", "charisma": "temp_cha"
        }

        full_ability = ability_map.get(ability.lower(), ability)
        temp_attr = temp_map.get(ability.lower(), f"temp_{ability[:3]}")

        return getattr(self, full_ability) + getattr(self, temp_attr)
