# Package initialization file

"""
Pathfinder Combat Simulator
===========================

A comprehensive, rule-compliant battle simulator for Pathfinder 1st Edition.
"""

# Core combat simulation classes
from .pathfinder_simulator import (
    Combatant,
    CombatEngine,
    MonsterDatabase,
    ActionHandler, # Added for test_combat_engine and general use
    Attack,        # Added for test_combat_engine and general use
    DamageType,    # Added for test_combat_engine and general use
)

# Enhanced database with PMD integration
from .enhanced_monster_database import (
    EnhancedMonsterDatabase,
    create_enhanced_monster_database,
)

# PMD Integration (if direct access is needed, otherwise it's used by EnhancedMonsterDatabase)
# from .pmd_integration import PMDIntegrator

# Main CLI application entry point (usually not imported as a library component)
# from .main import main


__all__ = [
    "Combatant",
    "CombatEngine",
    "MonsterDatabase",
    "EnhancedMonsterDatabase",
    "create_enhanced_monster_database",
    "ActionHandler",
    "Attack",
    "DamageType",
    # "PMDIntegrator", # Uncomment if PMDIntegrator is part of the public API
]
