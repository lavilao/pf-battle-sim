from dataclasses import dataclass, field
from typing import List
from .enums import DamageType, AttackType

@dataclass
class Attack:
    """Represents a weapon or natural attack"""
    name: str
    damage_dice: str  # e.g., "1d8", "2d6"
    critical_threat_range: str  # e.g., "20", "19-20"
    critical_multiplier: str  # e.g., "x2", "x3"
    damage_type: DamageType
    attack_type: AttackType = AttackType.MELEE # Added attack_type, default to MELEE
    reach: int = 5  # in feet
    associated_ability_for_attack: str = "str"  # str or dex
    associated_ability_for_damage: str = "str"
    is_primary_natural_attack: bool = True
    special_qualities: List[str] = field(default_factory=list)
    enhancement_bonus: int = 0

    def get_threat_range(self) -> List[int]:
        """Get the list of d20 values that constitute a threat"""
        if self.critical_threat_range == "20":
            return [20]
        elif self.critical_threat_range == "19-20":
            return [19, 20]
        elif self.critical_threat_range == "18-20":
            return [18, 19, 20]
        else:
            return [20]  # default

    def get_crit_multiplier(self) -> int:
        """Get the critical hit multiplier as an integer"""
        if self.critical_multiplier == "x2":
            return 2
        elif self.critical_multiplier == "x3":
            return 3
        elif self.critical_multiplier == "x4":
            return 4
        else:
            return 2  # default
