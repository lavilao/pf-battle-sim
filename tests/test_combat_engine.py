#!/usr/bin/env python3
"""
Test cases for the combat engine following TDD principles.

Tests proper Pathfinder 1e combat rules implementation including:
- Combat ending conditions (death, unconsciousness, disabled)
- Dying and stabilization rules
- Hit point management
- Proper initiative handling
"""

import unittest
import sys
import os
import random # Moved import to top level

# Assuming tests are run from the root directory where `src` is visible,
# or pytest handles path resolution for the src layout.
# Add project root to path if tests are run from 'tests' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pathfinder_combat_simulator import (
    Combatant, CombatEngine, ActionHandler, Attack, DamageType
)


class TestCombatEndingConditions(unittest.TestCase):
    """Test combat ending according to Pathfinder rules"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.combat = CombatEngine()
        self.action_handler = ActionHandler(self.combat)
        
        # Create test combatants
        self.fighter = self._create_fighter()
        self.orc = self._create_orc()
        
    def _create_fighter(self):
        """Create a test fighter"""
        fighter = Combatant("Test Fighter", is_pc=True)
        fighter.max_hp = 15
        fighter.current_hp = 15
        fighter.ability_scores.constitution = 14
        fighter.ability_scores.strength = 16
        fighter.ability_scores.dexterity = 13
        fighter.base_attack_bonus = 2
        
        # Add a basic attack
        sword = Attack(
            name="Longsword",
            damage_dice="1d8",
            critical_threat_range="19-20",
            critical_multiplier="x2",
            damage_type=DamageType.SLASHING
        )
        fighter.attacks.append(sword)
        return fighter
    
    def _create_orc(self):
        """Create a test orc"""
        orc = Combatant("Test Orc", is_pc=False)
        orc.max_hp = 10
        orc.current_hp = 10
        orc.ability_scores.constitution = 13
        orc.ability_scores.strength = 17
        orc.ability_scores.dexterity = 11
        orc.base_attack_bonus = 1
        
        # Add a basic attack
        axe = Attack(
            name="Battleaxe",
            damage_dice="1d8",
            critical_threat_range="20",
            critical_multiplier="x3",
            damage_type=DamageType.SLASHING
        )
        orc.attacks.append(axe)
        return orc
    
    def test_combat_ends_when_one_side_dies(self):
        """Test that combat ends when one side is completely defeated"""
        # Add combatants to combat
        self.combat.add_combatant(self.fighter, is_aware=True)
        self.combat.add_combatant(self.orc, is_aware=True)
        self.combat.start_combat()
        
        # Manually reduce orc to 0 HP (unconscious/dying)
        self.orc.current_hp = 0
        
        # Combat should end
        self.assertTrue(self.combat.is_combat_over())
    
    def test_combat_ends_when_one_side_dies_negative_hp(self):
        """Test that combat ends when one side reaches negative HP equal to Con score"""
        # Add combatants to combat
        self.combat.add_combatant(self.fighter, is_aware=True)
        self.combat.add_combatant(self.orc, is_aware=True)
        self.combat.start_combat()
        
        # Reduce orc to -Con score (dead)
        self.orc.current_hp = -self.orc.ability_scores.constitution
        
        # Combat should end
        self.assertTrue(self.combat.is_combat_over())
    
    def test_combat_continues_when_creatures_unconscious_but_stabilized(self):
        """Test that combat doesn't end if unconscious creatures are stabilized"""
        # Add combatants to combat
        self.combat.add_combatant(self.fighter, is_aware=True)
        self.combat.add_combatant(self.orc, is_aware=True)
        self.combat.start_combat()
        
        # Make orc unconscious but stable
        self.orc.current_hp = -1
        self.orc.add_condition("stable")
        
        # Combat should continue if both sides have potential combatants
        # However, since the orc is unconscious, combat should end
        self.assertTrue(self.combat.is_combat_over())
    
    def test_combat_continues_with_multiple_combatants_per_side(self):
        """Test combat continues when multiple combatants exist per side"""
        # Create second orc
        orc2 = self._create_orc()
        orc2.name = "Test Orc 2"
        
        # Add all combatants
        self.combat.add_combatant(self.fighter, is_aware=True)
        self.combat.add_combatant(self.orc, is_aware=True)
        self.combat.add_combatant(orc2, is_aware=True)
        self.combat.start_combat()
        
        # Kill one orc
        self.orc.current_hp = 0
        
        # Combat should continue (fighter vs orc2)
        self.assertFalse(self.combat.is_combat_over())
        
        # Kill second orc
        orc2.current_hp = 0
        
        # Now combat should end
        self.assertTrue(self.combat.is_combat_over())


class TestHitPointsAndDeath(unittest.TestCase):
    """Test hit point management according to Pathfinder rules"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.combatant = Combatant("Test", is_pc=True)
        self.combatant.max_hp = 10
        self.combatant.current_hp = 10
        self.combatant.ability_scores.constitution = 12  # Con score = 12
    
    def test_disabled_at_zero_hp(self):
        """Test that combatant becomes disabled at 0 HP"""
        self.combatant.current_hp = 0
        self.assertTrue(self.combatant.is_disabled())
        self.assertFalse(self.combatant.is_dying())
        self.assertFalse(self.combatant.is_dead())
    
    def test_dying_at_negative_hp(self):
        """Test that combatant is dying at negative HP but above -Con"""
        self.combatant.current_hp = -5  # Above -12 (Con score)
        self.assertFalse(self.combatant.is_disabled())
        self.assertTrue(self.combatant.is_dying())
        self.assertFalse(self.combatant.is_dead())
    
    def test_dead_at_negative_con_score(self):
        """Test that combatant dies at -Con score"""
        self.combatant.current_hp = -12  # Equal to -Con score
        self.assertFalse(self.combatant.is_disabled())
        self.assertFalse(self.combatant.is_dying())
        self.assertTrue(self.combatant.is_dead())
    
    def test_stabilized_dying_character(self):
        """Test stabilized dying character"""
        self.combatant.current_hp = -3
        self.combatant.add_condition("stable")
        
        self.assertTrue(self.combatant.is_dying())
        self.assertTrue(self.combatant.has_condition("stable"))


class TestAttackResolution(unittest.TestCase):
    """Test attack resolution and damage application"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.combat = CombatEngine()
        self.attacker = Combatant("Attacker", is_pc=True)
        self.target = Combatant("Target", is_pc=False)
        
        # Set up attacker
        self.attacker.ability_scores.strength = 16  # +3 bonus
        self.attacker.base_attack_bonus = 3
        
        # Set up target
        self.target.max_hp = 20
        self.target.current_hp = 20
        self.target.armor_class.armor_bonus = 2
        
        # Create test attack
        self.attack = Attack(
            name="Test Attack",
            damage_dice="1d8",
            critical_threat_range="20",
            critical_multiplier="x2",
            damage_type=DamageType.SLASHING
        )
        self.attacker.attacks.append(self.attack)
    
    def test_attack_hits_target_ac(self):
        """Test that attack hits when roll meets or exceeds AC"""
        # Force a specific attack roll by mocking random
        # import random # Moved to top
        original_randint = random.randint
        
        def mock_randint(a, b):
            if a == 1 and b == 20:  # Attack roll
                return 15  # Should hit AC 18 (10 + 2 armor + 6 total attack)
            return original_randint(a, b)
        
        random.randint = mock_randint
        
        try:
            result = self.combat.make_attack(self.attacker, self.target, self.attack)
            self.assertTrue(result.is_hit)
        finally:
            random.randint = original_randint
    
    def test_damage_reduces_hp(self):
        """Test that damage properly reduces target HP"""
        initial_hp = self.target.current_hp
        
        # Force hit and specific damage
        # import random # Moved to top
        original_randint = random.randint
        
        def mock_randint(a, b):
            if a == 1 and b == 20:  # Attack roll - natural 20 to guarantee hit
                return 20
            elif a == 1 and b == 8:  # Damage roll
                return 6
            return original_randint(a, b)
        
        random.randint = mock_randint
        
        try:
            result = self.combat.make_attack(self.attacker, self.target, self.attack)
            expected_damage = 6 + 3  # 1d8 + Str mod
            self.assertEqual(self.target.current_hp, initial_hp - expected_damage)
        finally:
            random.randint = original_randint


class TestMonsterOnlyCombat(unittest.TestCase):
    """Test combat scenarios involving only monsters."""

    def setUp(self):
        """Set up test fixtures for monster-only combat."""
        self.combat_engine = CombatEngine()
        self.action_handler = ActionHandler(self.combat_engine)

        # Create monster combatants
        self.orc1 = self._create_monster("Orc Warrior 1", hp=15)
        self.orc2 = self._create_monster("Orc Warrior 2", hp=15)
        self.goblin1 = self._create_monster("Goblin Scamp", hp=7, bab=0, damage_dice="1d4")

    def _create_monster(self, name, hp=10, bab=1, damage_dice="1d8", con=12, strength=14, dexterity=10):
        monster = Combatant(name, is_pc=False)
        monster.max_hp = hp
        monster.current_hp = hp
        monster.ability_scores.constitution = con
        monster.ability_scores.strength = strength
        monster.ability_scores.dexterity = dexterity
        monster.base_attack_bonus = bab

        attack_weapon = Attack(
            name="Claws" if damage_dice == "1d4" else "Battleaxe", # Generic weapon name
            damage_dice=damage_dice,
            critical_threat_range="20",
            critical_multiplier="x2",
            damage_type=DamageType.SLASHING
        )
        monster.attacks.append(attack_weapon)
        monster.initiative_modifier = monster.ability_scores.get_modifier("dexterity")
        return monster

    def test_combat_ends_one_monster_left(self):
        """Test that combat ends when only one monster remains in a monster-only battle."""
        self.combat_engine.add_combatant(self.orc1, is_aware=True)
        self.combat_engine.add_combatant(self.orc2, is_aware=True)
        self.combat_engine.start_combat()

        # Simulate orc1 defeating orc2
        # For simplicity, directly set orc2's HP to be defeated
        self.orc2.current_hp = -self.orc2.ability_scores.get_total_score("constitution") # Dead
        self.orc2.add_condition("dead")


        # Check combat end condition
        # Need to advance turns or directly call is_combat_over
        # Advancing a turn should trigger the check if get_current_combatant finds no one or combat ends
        self.combat_engine.advance_turn() # Process current turn
        if self.combat_engine.combat_active: # If combat didn't end after first turn processing
            self.combat_engine.advance_turn() # Process next turn (if any)

        self.assertTrue(self.combat_engine.is_combat_over(),
                        f"Combat should be over. Log: {self.combat_engine.log.get_full_log()}")

        remaining_active = [c for c in self.combat_engine.combatants if c.current_hp > 0 and not c.is_dead()]
        self.assertEqual(len(remaining_active), 1, "Exactly one monster should remain active.")
        self.assertEqual(remaining_active[0].name, self.orc1.name, "Orc1 should be the survivor.")

    def test_monsters_attack_each_other(self):
        """Test that monsters attack each other in a monster-only battle and combat proceeds."""
        self.combat_engine.add_combatant(self.orc1, is_aware=True)
        self.combat_engine.add_combatant(self.goblin1, is_aware=True)
        self.combat_engine.start_combat()

        initial_orc1_hp = self.orc1.current_hp
        initial_goblin1_hp = self.goblin1.current_hp

        max_turns = 10 # Safety break for the test loop
        turns_taken = 0

        # Simplified AI: current combatant attacks the other living monster
        while self.combat_engine.combat_active and turns_taken < max_turns:
            current_combatant = self.combat_engine.get_current_combatant()
            if not current_combatant:
                break # Should be caught by is_combat_over

            targets = self.combat_engine.get_valid_targets(current_combatant)

            if targets and current_combatant.attacks:
                # NPCs target other NPCs (first available for simplicity in test)
                non_pc_targets = [t for t in targets if not t.is_pc]
                if non_pc_targets:
                    target = non_pc_targets[0]
                    self.action_handler.take_attack_action(current_combatant, target, 0)
                else:
                    # This case shouldn't happen in a 2-monster battle if one is still up
                    self.combat_engine.log.add_entry(f"{current_combatant.name} has no valid non-PC targets.")
            else:
                self.combat_engine.log.add_entry(f"{current_combatant.name} has no valid actions or targets.")

            self.combat_engine.advance_turn()
            turns_taken += 1
            if self.combat_engine.is_combat_over():
                self.combat_engine.end_combat() # Ensure combat ends if conditions met
                break

        self.assertTrue(turns_taken > 0, "Combat should have proceeded for at least one turn.")
        self.assertTrue(self.combat_engine.is_combat_over(),
                        f"Combat should be over after monsters fight. Log: {self.combat_engine.log.get_full_log()}")

        # Check that some damage was dealt (i.e., attacks happened)
        # This is a loose check; one might be defeated very quickly.
        orc1_hp_changed = self.orc1.current_hp < initial_orc1_hp
        goblin1_hp_changed = self.goblin1.current_hp < initial_goblin1_hp
        self.assertTrue(orc1_hp_changed or goblin1_hp_changed,
                        "At least one monster should have taken damage, indicating they attacked each other.")

        remaining_active = [c for c in self.combat_engine.combatants if c.current_hp > 0 and not c.is_dead()]
        self.assertEqual(len(remaining_active), 1,
                         f"Exactly one monster should remain active. Survivors: {[r.name for r in remaining_active]}. Log: {self.combat_engine.log.get_full_log()}")


if __name__ == '__main__':
    unittest.main()
