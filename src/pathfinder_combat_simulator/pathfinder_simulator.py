#!/usr/bin/env python3
"""
Pathfinder 1st Edition Battle Simulator
Following the comprehensive specification in prompt-pathfinder.md

Parts 1-3 Implementation:
- Part 1: Foundational Elements - Combatant Representation & Persistent Database
- Part 2: Core Combat Mechanics - Initiative, Rounds, and Basic State Tracking
- Part 3: Implementing Actions & Basic Attacks
"""

import json
import os
import random
# import re # No longer directly needed in this file as roll_dice is imported
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
# Enum is still used by the __main__ block indirectly through core classes, but not directly.
# from enum import Enum # Not directly used here anymore

# Simplified imports thanks to core/__init__.py
from .core import (
    ActionType, AttackType, DamageType, ACType,
    Attack,
    AbilityScores,
    ArmorClass,
    SavingThrows,
    Combatant,
    MonsterDatabase,
    CombatLog,
    AttackResult,
    CombatEngine,
    ActionHandler,
    roll_dice
)

# roll_dice function has been moved to core/utils.py
# All class definitions have been moved to the core package.


if __name__ == "__main__":
    # Demonstration of Parts 1-3 functionality
    print("=== Pathfinder 1e Battle Simulator - Parts 1-3 Demo ===")
    
    # Create monster database
    db = MonsterDatabase()
    
    # Create a sample monster (Orc Warrior)
    orc = Combatant("Orc Warrior", is_pc=False)
    orc.max_hp = 6
    orc.current_hp = 6
    orc.ability_scores.strength = 17
    orc.ability_scores.dexterity = 11
    orc.ability_scores.constitution = 12
    orc.ability_scores.intelligence = 8
    orc.ability_scores.wisdom = 11
    orc.ability_scores.charisma = 8
    orc.base_attack_bonus = 1
    orc.armor_class.armor_bonus = 4  # Scale mail
    orc.armor_class.shield_bonus = 1  # Light shield
    orc.saving_throws.fortitude_base = 3
    orc.saving_throws.reflex_base = 0
    orc.saving_throws.will_base = -1
    orc.base_speed = 30
    orc.size = "Medium"
    orc.creature_type = "Humanoid"
    orc.subtypes = ["Orc"]
    orc.alignment = "Chaotic Evil"
    
    # Add falchion attack
    falchion = Attack(
        name="Falchion",
        damage_dice="2d4",
        critical_threat_range="18-20",
        critical_multiplier="x2",
        damage_type=DamageType.SLASHING,
        attack_type=AttackType.MELEE, # Added attack_type
        reach=5,
        is_primary_natural_attack=False
    )
    orc.attacks.append(falchion)
    
    orc.initiative_modifier = orc.ability_scores.get_modifier("dexterity")
    
    # Create a PC
    fighter = Combatant("Sir Galahad", is_pc=True)
    fighter.player_controller = "Player 1"
    fighter.max_hp = 12
    fighter.current_hp = 12
    fighter.ability_scores.strength = 16
    fighter.ability_scores.dexterity = 13
    fighter.ability_scores.constitution = 14
    fighter.ability_scores.intelligence = 10
    fighter.ability_scores.wisdom = 12
    fighter.ability_scores.charisma = 8
    fighter.base_attack_bonus = 1
    fighter.armor_class.armor_bonus = 6  # Chainmail
    fighter.armor_class.shield_bonus = 2  # Heavy shield
    fighter.saving_throws.fortitude_base = 2
    fighter.saving_throws.reflex_base = 0
    fighter.saving_throws.will_base = 0
    fighter.feats = ["Power Attack", "Cleave"]
    
    longsword = Attack(
        name="Longsword",
        damage_dice="1d8",
        critical_threat_range="19-20",
        critical_multiplier="x2",
        damage_type=DamageType.SLASHING,
        attack_type=AttackType.MELEE, # Added attack_type
        reach=5,
        enhancement_bonus=1
    )
    fighter.attacks.append(longsword)
    
    fighter.initiative_modifier = fighter.ability_scores.get_modifier("dexterity")
    
    print("=== PART 1: Character Creation & Database ===")
    print(f"Created {orc.name}:")
    print(f"  HP: {orc.current_hp}/{orc.max_hp}, AC: {orc.get_ac()}")
    if orc.attacks:
      print(f"  Attack: {orc.attacks[0].name} +{orc.get_attack_bonus(orc.attacks[0])} ({orc.attacks[0].damage_dice})")
    
    print(f"\nCreated {fighter.name}:")
    print(f"  HP: {fighter.current_hp}/{fighter.max_hp}, AC: {fighter.get_ac()}")
    if fighter.attacks:
      print(f"  Attack: {fighter.attacks[0].name} +{fighter.get_attack_bonus(fighter.attacks[0])} ({fighter.attacks[0].damage_dice})")
    
    if db.save_monster(orc):
        print(f"\nSaved {orc.name} to database")
    
    print("\n=== PART 2-3: Combat Simulation ===")
    
    combat = CombatEngine()
    action_handler = ActionHandler(combat)
    
    orc_fighter = db.load_monster("Orc Warrior")

    player_fighter = Combatant("Sir Galahad", is_pc=True)
    player_fighter.max_hp = 12
    player_fighter.current_hp = 12
    player_fighter.ability_scores.strength = 16
    player_fighter.ability_scores.dexterity = 13
    player_fighter.ability_scores.constitution = 14
    player_fighter.base_attack_bonus = 1
    player_fighter.armor_class.armor_bonus = 6
    player_fighter.armor_class.shield_bonus = 2
    player_fighter.attacks.append(deepcopy(longsword))
    player_fighter.initiative_modifier = player_fighter.ability_scores.get_modifier("dexterity")

    if orc_fighter:
        combat.add_combatant(orc_fighter, is_aware=True)
    else:
        print("Error: Orc Warrior could not be loaded from database for combat.")
        exit()

    combat.add_combatant(player_fighter, is_aware=True)
    
    if not combat.start_combat():
        print("Combat could not be started.")
        exit()

    round_count = 0
    max_rounds = 5
    
    while combat.combat_active and round_count < max_rounds:
        current_combatant = combat.get_current_combatant()
        if not current_combatant:
            if combat.is_combat_over():
                 combat.end_combat()
            break
            
        targets = combat.get_valid_targets(current_combatant)
        if targets:
            target = targets[0]
            
            if current_combatant.attacks:
                action_handler.take_attack_action(current_combatant, target, 0)
            else:
                combat.log.add_entry(f"{current_combatant.name} has no attacks available and skips turn.")
        else:
            combat.log.add_entry(f"{current_combatant.name} has no valid targets and skips turn.")
        
        if not combat.combat_active:
            break

        combat.advance_turn()
        
        if combat.is_combat_over():
            if combat.combat_active : combat.end_combat()
            break
        
        if combat.current_round > round_count :
            round_count = combat.current_round
            if round_count >= max_rounds and combat.combat_active:
                combat.log.add_entry(f"\nCombat ended after {max_rounds} rounds (demo limit)")
                combat.end_combat()
                break
    
    if combat.combat_active:
        combat.log.add_entry("\nCombat ended due to hitting max round limit for demo.")
        combat.end_combat()

    print("\n=== Demo Complete ===")
    print("✓ Part 1: Combatant representation and database storage")
    print("✓ Part 2: Initiative system and round management") 
    print("✓ Part 3: Basic attack actions and damage resolution")
