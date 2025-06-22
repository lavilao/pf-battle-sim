#!/usr/bin/env python3
"""
Pathfinder 1e Battle Simulator - Comprehensive Demo
Demonstrates full functionality of Parts 1-3 without user input
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pathfinder_simulator import (
    Combatant, Attack, DamageType, MonsterDatabase, 
    CombatEngine, ActionHandler
)


def create_sample_fighter():
    """Create a sample fighter PC"""
    fighter = Combatant("Sir Roderick", is_pc=True)
    fighter.player_controller = "Player 1"
    fighter.max_hp = 15
    fighter.current_hp = 15
    fighter.ability_scores.strength = 16
    fighter.ability_scores.dexterity = 13
    fighter.ability_scores.constitution = 14
    fighter.ability_scores.intelligence = 10
    fighter.ability_scores.wisdom = 12
    fighter.ability_scores.charisma = 8
    fighter.base_attack_bonus = 2  # 2nd level
    fighter.armor_class.armor_bonus = 6  # Chainmail
    fighter.armor_class.shield_bonus = 2  # Heavy shield
    fighter.saving_throws.fortitude_base = 3
    fighter.saving_throws.reflex_base = 0
    fighter.saving_throws.will_base = 0
    fighter.feats = ["Power Attack", "Weapon Focus (Longsword)"]
    
    # Add longsword attack
    longsword = Attack(
        name="Longsword +1",
        damage_dice="1d8",
        critical_threat_range="19-20",
        critical_multiplier="x2",
        damage_type=DamageType.SLASHING,
        enhancement_bonus=1
    )
    fighter.attacks.append(longsword)
    
    fighter.initiative_modifier = fighter.ability_scores.get_modifier("dexterity")
    return fighter


def create_sample_rogue():
    """Create a sample rogue PC"""
    rogue = Combatant("Shadowstep", is_pc=True)
    rogue.player_controller = "Player 2"
    rogue.max_hp = 12
    rogue.current_hp = 12
    rogue.ability_scores.strength = 12
    rogue.ability_scores.dexterity = 18
    rogue.ability_scores.constitution = 13
    rogue.ability_scores.intelligence = 14
    rogue.ability_scores.wisdom = 10
    rogue.ability_scores.charisma = 12
    rogue.base_attack_bonus = 1  # 2nd level rogue
    rogue.armor_class.armor_bonus = 3  # Studded leather
    rogue.saving_throws.fortitude_base = 0
    rogue.saving_throws.reflex_base = 3
    rogue.saving_throws.will_base = 0
    rogue.feats = ["Weapon Finesse"]
    
    # Add rapier attack (using Dex for attack)
    rapier = Attack(
        name="Rapier",
        damage_dice="1d6",
        critical_threat_range="18-20",
        critical_multiplier="x2",
        damage_type=DamageType.PIERCING,
        associated_ability_for_attack="dexterity"
    )
    rogue.attacks.append(rapier)
    
    rogue.initiative_modifier = rogue.ability_scores.get_modifier("dexterity")
    return rogue


def create_sample_monsters():
    """Create and return sample monsters"""
    # Orc Barbarian (stronger than basic orc)
    orc = Combatant("Orc Barbarian", is_pc=False)
    orc.max_hp = 15
    orc.current_hp = 15
    orc.ability_scores.strength = 19
    orc.ability_scores.dexterity = 12
    orc.ability_scores.constitution = 15
    orc.ability_scores.intelligence = 8
    orc.ability_scores.wisdom = 11
    orc.ability_scores.charisma = 8
    orc.base_attack_bonus = 2
    orc.armor_class.armor_bonus = 4  # Scale mail
    orc.armor_class.shield_bonus = 1  # Light shield
    orc.saving_throws.fortitude_base = 3
    orc.saving_throws.reflex_base = 0
    orc.saving_throws.will_base = 0
    orc.size = "Medium"
    orc.creature_type = "Humanoid"
    orc.subtypes = ["Orc"]
    orc.alignment = "Chaotic Evil"
    
    greataxe = Attack(
        name="Greataxe",
        damage_dice="1d12",
        critical_threat_range="20",
        critical_multiplier="x3",
        damage_type=DamageType.SLASHING
    )
    orc.attacks.append(greataxe)
    orc.initiative_modifier = orc.ability_scores.get_modifier("dexterity")
    
    # Goblin Archer
    goblin = Combatant("Goblin Archer", is_pc=False)
    goblin.max_hp = 6
    goblin.current_hp = 6
    goblin.ability_scores.strength = 11
    goblin.ability_scores.dexterity = 16
    goblin.ability_scores.constitution = 12
    goblin.ability_scores.intelligence = 10
    goblin.ability_scores.wisdom = 9
    goblin.ability_scores.charisma = 6
    goblin.base_attack_bonus = 1
    goblin.armor_class.armor_bonus = 2  # Leather armor
    goblin.armor_class.size_modifier = 1  # Small size
    goblin.saving_throws.fortitude_base = 1
    goblin.saving_throws.reflex_base = 2
    goblin.saving_throws.will_base = -1
    goblin.size = "Small"
    goblin.creature_type = "Humanoid"
    goblin.subtypes = ["Goblinoid"]
    goblin.alignment = "Neutral Evil"
    
    shortbow = Attack(
        name="Shortbow",
        damage_dice="1d4",
        critical_threat_range="20",
        critical_multiplier="x3",
        damage_type=DamageType.PIERCING,
        associated_ability_for_attack="dexterity",
        associated_ability_for_damage="strength"  # Bows don't add str to damage unless composite
    )
    goblin.attacks.append(shortbow)
    goblin.initiative_modifier = goblin.ability_scores.get_modifier("dexterity")
    
    return [orc, goblin]


def run_sample_combat():
    """Run a sample combat encounter"""
    print("="*80)
    print("           PATHFINDER 1E BATTLE SIMULATOR DEMO")
    print("="*80)
    
    # Create combatants
    fighter = create_sample_fighter()
    rogue = create_sample_rogue()
    orc, goblin = create_sample_monsters()
    
    print("\n=== COMBATANTS ===")
    print(f"{fighter.name} (Fighter): HP {fighter.max_hp}, AC {fighter.get_ac()}")
    print(f"{rogue.name} (Rogue): HP {rogue.max_hp}, AC {rogue.get_ac()}")
    print(f"{orc.name}: HP {orc.max_hp}, AC {orc.get_ac()}")
    print(f"{goblin.name}: HP {goblin.max_hp}, AC {goblin.get_ac()}")
    
    # Set up combat
    combat = CombatEngine()
    action_handler = ActionHandler(combat)
    
    # Add combatants (all aware)
    combat.add_combatant(fighter, is_aware=True)
    combat.add_combatant(rogue, is_aware=True)
    combat.add_combatant(orc, is_aware=True)
    combat.add_combatant(goblin, is_aware=True)
    
    # Start combat
    combat.start_combat()
    
    # Run combat with simple AI
    turn_count = 0
    max_turns = 20  # Safety limit
    
    while combat.combat_active and turn_count < max_turns:
        current_combatant = combat.get_current_combatant()
        if not current_combatant:
            break
        
        # Simple AI logic
        targets = combat.get_valid_targets(current_combatant)
        if targets and current_combatant.attacks:
            # Choose target: NPCs target PCs, PCs target NPCs
            if current_combatant.is_pc:
                # PCs prioritize weakest enemy
                npc_targets = [t for t in targets if not t.is_pc]
                if npc_targets:
                    target = min(npc_targets, key=lambda t: t.current_hp)
                else:
                    target = targets[0]
            else:
                # NPCs target random PC
                pc_targets = [t for t in targets if t.is_pc]
                if pc_targets:
                    target = pc_targets[0]
                else:
                    target = targets[0]
            
            # Determine action type based on BAB
            if current_combatant.base_attack_bonus >= 6:
                # High BAB characters can use full attack effectively
                action_handler.take_full_attack_action(current_combatant, target, 0)
            else:
                # Low BAB characters use standard attack
                action_handler.take_attack_action(current_combatant, target, 0)
        else:
            combat.log.add_entry(f"{current_combatant.name} has no valid actions")
        
        # Advance turn
        combat.advance_turn()
        turn_count += 1
        
        # Check if combat should end
        if combat.is_combat_over():
            combat.end_combat()
            break
    
    if turn_count >= max_turns:
        combat.log.add_entry(f"\nCombat ended after {max_turns} turns (demo limit)")
        combat.end_combat()
    
    print(f"\n=== COMBAT RESULTS ===")
    survivors = [c for c in combat.combatants if c.current_hp > 0]
    defeated = [c for c in combat.combatants if c.current_hp <= 0]
    
    if survivors:
        print("Survivors:")
        for survivor in survivors:
            print(f"  {survivor.name}: {survivor.current_hp}/{survivor.max_hp} HP")
    
    if defeated:
        print("Defeated:")
        for fallen in defeated:
            print(f"  {fallen.name}")
    
    return combat


def demonstrate_database():
    """Demonstrate monster database functionality"""
    print("\n" + "="*60)
    print("              DATABASE DEMONSTRATION")
    print("="*60)
    
    db = MonsterDatabase()
    
    # Create and save monsters
    orc, goblin = create_sample_monsters()
    
    print("Saving monsters to database...")
    db.save_monster(orc)
    db.save_monster(goblin)
    
    print(f"Monsters in database: {db.list_monsters()}")
    
    # Load and display a monster
    loaded_orc = db.load_monster("Orc Barbarian")
    if loaded_orc:
        print(f"\nLoaded {loaded_orc.name} from database:")
        print(f"  HP: {loaded_orc.max_hp}")
        print(f"  Str: {loaded_orc.ability_scores.strength}")
        print(f"  AC: {loaded_orc.get_ac()}")
        print(f"  Primary Attack: {loaded_orc.attacks[0].name} ({loaded_orc.attacks[0].damage_dice})")


def demonstrate_combat_mechanics():
    """Demonstrate specific combat mechanics"""
    print("\n" + "="*60)
    print("           COMBAT MECHANICS DEMONSTRATION")
    print("="*60)
    
    fighter = create_sample_fighter()
    orc, _ = create_sample_monsters()
    
    print("\n=== Attack Roll Demonstration ===")
    
    # Manual attack demonstration
    attack = fighter.attacks[0]  # Longsword
    print(f"{fighter.name} attacks {orc.name} with {attack.name}")
    
    # Show AC calculation
    print(f"\nAC Calculation for {orc.name}:")
    print(f"  Base AC: 10")
    print(f"  Armor Bonus: +{orc.armor_class.armor_bonus}")
    print(f"  Shield Bonus: +{orc.armor_class.shield_bonus}")
    print(f"  Dex Modifier: +{orc.ability_scores.get_modifier('dexterity')}")
    print(f"  Total AC: {orc.get_ac()}")
    
    # Show attack bonus calculation
    attack_bonus = fighter.get_attack_bonus(attack)
    print(f"\nAttack Bonus for {fighter.name}:")
    print(f"  BAB: +{fighter.base_attack_bonus}")
    print(f"  Str Modifier: +{fighter.ability_scores.get_modifier('strength')}")
    print(f"  Enhancement: +{attack.enhancement_bonus}")
    print(f"  Total Attack: +{attack_bonus}")
    
    # Show damage calculation
    print(f"\nDamage Calculation:")
    print(f"  Base Damage: {attack.damage_dice}")
    print(f"  Str Modifier: +{fighter.ability_scores.get_modifier('strength')}")
    print(f"  Enhancement: +{attack.enhancement_bonus}")
    print(f"  Critical: {attack.critical_threat_range}/{attack.critical_multiplier}")
    
    print(f"\n=== Saving Throw Demonstration ===")
    print(f"{fighter.name}'s Saves:")
    print(f"  Fortitude: +{fighter.saving_throws.calculate_save('fortitude', fighter.ability_scores)}")
    print(f"  Reflex: +{fighter.saving_throws.calculate_save('reflex', fighter.ability_scores)}")
    print(f"  Will: +{fighter.saving_throws.calculate_save('will', fighter.ability_scores)}")


if __name__ == "__main__":
    # Run all demonstrations
    demonstrate_database()
    demonstrate_combat_mechanics()
    combat = run_sample_combat()
    
    print("\n" + "="*80)
    print("                        DEMO COMPLETE")
    print("="*80)
    print("✓ Part 1: Combatant data structures and persistent database")
    print("✓ Part 2: Initiative system, rounds, and turn management")
    print("✓ Part 3: Action economy, attacks, damage, and critical hits")
    print("\nFeatures Demonstrated:")
    print("• Character creation with full Pathfinder 1e stats")
    print("• Monster database with JSON storage and retrieval")
    print("• Initiative rolling with proper tie-breaking")
    print("• Turn-based combat with action economy")
    print("• Attack rolls with modifiers and AC calculations")
    print("• Damage rolling with critical hit confirmation")
    print("• Combat ending conditions")
    print("• Flat-footed and condition tracking")
    print("\nThe CLI interface (pathfinder_cli.py) provides interactive access to all features.")
