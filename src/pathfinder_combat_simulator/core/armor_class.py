from dataclasses import dataclass
from typing import Optional

@dataclass
class ArmorClass:
    """Represents AC components"""
    armor_bonus: int = 0
    shield_bonus: int = 0
    natural_armor_bonus: int = 0
    deflection_bonus: int = 0
    dodge_bonus: int = 0
    size_modifier: int = 0
    max_dex_bonus_from_armor: Optional[int] = None

    def calculate_ac(self, dex_modifier: int, is_flat_footed: bool = False) -> int:
        """Calculate total AC following Pathfinder rules"""
        effective_dex = min(dex_modifier, self.max_dex_bonus_from_armor or dex_modifier)
        if is_flat_footed:
            effective_dex = 0

        return (10 + self.armor_bonus + self.shield_bonus +
               self.natural_armor_bonus + effective_dex +
               self.size_modifier + self.deflection_bonus +
               self.dodge_bonus)

    def calculate_touch_ac(self, dex_modifier: int, is_flat_footed: bool = False) -> int:
        """Calculate touch AC (ignores armor, shield, and natural armor)"""
        effective_dex = min(dex_modifier, self.max_dex_bonus_from_armor or dex_modifier)
        if is_flat_footed:
            effective_dex = 0

        return (10 + effective_dex + self.size_modifier +
               self.deflection_bonus + self.dodge_bonus)

    def calculate_flat_footed_ac(self, dex_modifier: int) -> int:
        """Calculate flat-footed AC (loses Dex bonus, retains other bonuses)"""
        return (10 + self.armor_bonus + self.shield_bonus +
               self.natural_armor_bonus + self.size_modifier +
               self.deflection_bonus + self.dodge_bonus)
