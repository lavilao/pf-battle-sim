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

class ConditionType(Enum):
    """Common Pathfinder 1e conditions"""
    BLINDED = "blinded"
    CONFUSED = "confused"
    COWERING = "cowering"
    DAZED = "dazed"
    DAZZLED = "dazzled"
    DEAD = "dead"
    DEAFENED = "deafened"
    DISABLED = "disabled"
    DYING = "dying"
    ENERGY_DRAINED = "energy_drained"
    ENTANGLED = "entangled"
    EXHAUSTED = "exhausted"
    FATIGUED = "fatigued"
    FLAT_FOOTED = "flat-footed"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    HELPLESS = "helpless"
    INCORPOREAL = "incorporeal"
    INVISIBLE = "invisible"
    NAUSEATED = "nauseated"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    PINNED = "pinned"
    PRONE = "prone"
    SHAKEN = "shaken"
    SICKENED = "sickened"
    STABLE = "stable"
    STAGGERED = "staggered"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"
