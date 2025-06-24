from enum import Enum

class ActionType(Enum):
    """Types of actions available in combat"""
    STANDARD = "standard"
    MOVE = "move"
    FULL_ROUND = "full_round"
    SWIFT = "swift"
    IMMEDIATE = "immediate"
    FREE = "free"


class AttackType(Enum):
    """Types of attacks"""
    MELEE = "melee"
    RANGED = "ranged"
    NATURAL = "natural"


class DamageType(Enum):
    """Types of damage"""
    SLASHING = "slashing"
    PIERCING = "piercing"
    BLUDGEONING = "bludgeoning"
    FIRE = "fire"
    COLD = "cold"
    ACID = "acid"
    ELECTRICITY = "electricity"
    SONIC = "sonic"
    FORCE = "force"

class ACType(Enum):
    """Armor class types"""
    STANDARD = "standard"
    TOUCH = "touch"
    FLAT_FOOTED = "flat_footed"
