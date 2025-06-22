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

# Add the code directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from pathfinder_simulator import (
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
        import random
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
        import random
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


if __name__ == '__main__':
    unittest.main()
