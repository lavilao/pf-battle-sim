# This file makes the 'core' directory a Python package.

# We can choose to expose certain classes at the package level for easier imports,
# e.g., from pathfinder_combat_simulator.core import Combatant
# instead of from pathfinder_combat_simulator.core.combatant import Combatant

from .enums import ActionType, AttackType, DamageType, ACType
from .attack import Attack
from .ability_scores import AbilityScores
from .armor_class import ArmorClass
from .saving_throws import SavingThrows
from .combatant import Combatant
from .monster_database import MonsterDatabase
from .combat_log import CombatLog
from .attack_result import AttackResult
from .combat_engine import CombatEngine
from .action_handler import ActionHandler
from .utils import roll_dice

__all__ = [
    "ActionType", "AttackType", "DamageType", "ACType",
    "Attack",
    "AbilityScores",
    "ArmorClass",
    "SavingThrows",
    "Combatant",
    "MonsterDatabase",
    "CombatLog",
    "AttackResult",
    "CombatEngine",
    "ActionHandler",
    "roll_dice",
]
