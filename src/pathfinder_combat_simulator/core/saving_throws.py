from dataclasses import dataclass
# It seems AbilityScores is needed here. Let's add the import.
# If it causes circular dependency issues later, we might need to refactor further
# or pass AbilityScores instance as a parameter instead of type hinting it directly in the class.
from .ability_scores import AbilityScores

@dataclass
class SavingThrows:
    """Represents saving throw bonuses"""
    fortitude_base: int = 0
    reflex_base: int = 0
    will_base: int = 0

    def calculate_save(self, save_type: str, ability_scores: AbilityScores) -> int:
        """Calculate total saving throw bonus"""
        base = getattr(self, f"{save_type}_base")
        if save_type == "fortitude":
            return base + ability_scores.get_modifier("constitution")
        elif save_type == "reflex":
            return base + ability_scores.get_modifier("dexterity")
        elif save_type == "will":
            return base + ability_scores.get_modifier("wisdom")
        return base
