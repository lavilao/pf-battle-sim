import unittest
import random
from typing import List, Tuple

# Assuming the simulator module is in the parent directory or installed
import sys
import os
# Add project root to path if tests are run from 'tests' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pathfinder_combat_simulator.pathfinder_simulator import (
    Combatant, CombatEngine, ActionHandler, Attack, DamageType, ActionType, AttackType, AbilityScores
)

class TestAdvancedCombatMechanics(unittest.TestCase):

    def setUp(self):
        # Suppress print statements from the simulator during tests for cleaner output
        # self.old_stdout = sys.stdout
        # sys.stdout = open(os.devnull, 'w')
        # random.seed(42) # For reproducible random rolls during testing certain scenarios

        self.engine = CombatEngine()
        self.action_handler = ActionHandler(self.engine)

        # Create generic combatants
        self.combatant1 = Combatant("Alice", is_pc=True)
        self.combatant1.max_hp = 20
        self.combatant1.ability_scores.constitution = 14 # For dying/dead checks
        self.combatant1.attacks.append(Attack("Longsword", "1d8", "19-20", "x2", DamageType.SLASHING))
        self.combatant1.attacks.append(Attack("Shortbow", "1d6", "20", "x3", DamageType.PIERCING, attack_type=AttackType.RANGED))
        self.combatant1.skills["Heal"] = 5 # Give some heal skill

        self.combatant2 = Combatant("Bob", is_pc=False)
        self.combatant2.max_hp = 15
        self.combatant2.ability_scores.constitution = 12
        self.combatant2.attacks.append(Attack("Scimitar", "1d6", "18-20", "x2", DamageType.SLASHING))

        self.engine.add_combatant(self.combatant1)
        self.engine.add_combatant(self.combatant2)
        # self.engine.start_combat() # Don't auto start, let tests control this

    def tearDown(self):
        # sys.stdout.close()
        # sys.stdout = self.old_stdout
        pass

    def _set_current_turn(self, combatant_name: str):
        """Helper to set whose turn it is."""
        self.engine.initiative_order = []
        if combatant_name == self.combatant1.name:
            self.engine.initiative_order.append((self.combatant1, 20))
            self.engine.initiative_order.append((self.combatant2, 10))
        else:
            self.engine.initiative_order.append((self.combatant2, 20))
            self.engine.initiative_order.append((self.combatant1, 10))
        self.engine.current_turn_index = 0
        self.engine.combat_active = True
        self.engine.current_round = 1
        self.engine.log.clear() # Clear log for test isolation


    # 1. Hit Points and Injury Conditions
    def test_hp_conditions_disabled_dying_dead(self):
        self.combatant1.max_hp = 10
        self.combatant1.ability_scores.constitution = 10 # Dead at -10 HP
        self.combatant1.reset_for_combat()
        self.assertEqual(self.combatant1.current_hp, 10)

        self.combatant1.take_damage(10) # HP becomes 0
        self.assertEqual(self.combatant1.current_hp, 0)
        self.assertTrue(self.combatant1.is_disabled())
        self.assertFalse(self.combatant1.is_dying())
        self.assertFalse(self.combatant1.is_dead())

        self.combatant1.take_damage(1) # HP becomes -1
        self.assertEqual(self.combatant1.current_hp, -1)
        self.assertFalse(self.combatant1.is_disabled())
        self.assertTrue(self.combatant1.is_dying())
        self.assertFalse(self.combatant1.is_dead())

        self.combatant1.take_damage(8) # HP becomes -9
        self.assertEqual(self.combatant1.current_hp, -9)
        self.assertTrue(self.combatant1.is_dying())

        self.combatant1.take_damage(1) # HP becomes -10 (dead)
        self.assertEqual(self.combatant1.current_hp, -10)
        self.assertFalse(self.combatant1.is_dying())
        self.assertTrue(self.combatant1.is_dead())
        self.assertTrue(self.combatant1.has_condition("dead"))

        # Damage shouldn't go below -Con score
        self.combatant1.take_damage(5)
        self.assertEqual(self.combatant1.current_hp, -10)


    def test_stabilization_self(self):
        self.combatant1.current_hp = -5
        self.combatant1.add_condition("dying")

        # Test stabilization success (force roll using seed or mock if complex)
        random.seed(1) # roll = 18 for d20
        stabilized = self.combatant1.stabilize()
        self.assertTrue(stabilized)
        self.assertTrue(self.combatant1.has_condition("stable"))
        self.assertFalse(self.combatant1.has_condition("dying"))
        self.assertEqual(self.combatant1.current_hp, -5) # HP doesn't change on stabilize

        self.combatant1.current_hp = -1
        self.combatant1.conditions.clear()
        self.combatant1.add_condition("dying")
        random.seed(15) # roll = 1 for d20 -> (1 - 1) vs DC 10 -> fail
        stabilized = self.combatant1.stabilize()
        self.assertFalse(stabilized)
        self.assertFalse(self.combatant1.has_condition("stable"))
        self.assertTrue(self.combatant1.has_condition("dying")) # Still dying
        self.assertEqual(self.combatant1.current_hp, -2) # Lost 1 HP


    def test_stabilization_by_heal_skill(self):
        self._set_current_turn(self.combatant1.name)
        self.combatant2.current_hp = -3
        self.combatant2.add_condition("dying")

        random.seed(10) # Heal roll d20 = 16. 16+5 = 21 >= 15 (success)
        success = self.action_handler.take_stabilize_other_action(self.combatant1, self.combatant2)
        self.assertTrue(success)
        self.assertTrue(self.combatant2.has_condition("stable"))
        self.assertFalse(self.combatant2.has_condition("dying"))

        self.combatant2.current_hp = -3
        self.combatant2.conditions.clear()
        self.combatant2.add_condition("dying")
        random.seed(1) # Heal roll d20 = 18. This seed gives 18, but if skill is low...
                       # Let's set skill low.
        self.combatant1.skills["Heal"] = -2
        random.seed(10) # Heal roll d20 = 16. 16-2 = 14 < 15 (fail)
        success = self.action_handler.take_stabilize_other_action(self.combatant1, self.combatant2)
        self.assertFalse(success)
        self.assertFalse(self.combatant2.has_condition("stable"))


    # 2. Attacks of Opportunity
    def test_aoo_provoked_by_ranged_attack(self):
        self._set_current_turn(self.combatant1.name)
        self.combatant1.reset_for_combat() # C1 is active
        self.combatant2.reset_for_combat() # C2 can make AoO
        self.combatant2.current_hp = 10 # Ensure C2 is alive to make AoO

        # Mock get_threatened_squares if needed, or assume they are adjacent for test
        # For simplicity, we assume CombatEngine's trigger_attacks_of_opportunity
        # will consider combatant2 to threaten combatant1 if can_make_aoo is true.
        # A more robust test would mock positions.

        original_hp_c1 = self.combatant1.current_hp
        random.seed(50) # Control rolls for AoO and the ranged attack
        # C1 (attacker) uses shortbow (index 1) against C2 (target)
        self.action_handler.take_attack_action(self.combatant1, self.combatant2, 1)

        # Check if C1 took damage from an AoO from C2
        # This requires C2's AoO to hit and deal damage.
        # The log will show "Bob gets an AoO against Alice!"
        # And then "Bob attacks Alice with Scimitar"
        # Let's check the log or C1's HP
        self.assertLess(self.combatant1.current_hp, original_hp_c1, "Combatant1 should have taken damage from AoO")
        self.assertIn(f"{self.combatant2.name} gets an AoO against {self.combatant1.name}!", self.engine.log.get_full_log())


    def test_aoo_combat_reflexes(self):
        self._set_current_turn(self.combatant1.name)
        self.combatant2.feats.append("Combat Reflexes")
        self.combatant2.ability_scores.dexterity = 14 # Dex mod +2, so 1 (base) + 2 = 3 AoOs
        self.combatant2.aoo_made_this_round = 0
        self.combatant2.is_flat_footed = False

        self.assertTrue(self.engine.can_make_aoo(self.combatant2))
        self.engine.trigger_attacks_of_opportunity(self.combatant1, "provoking action 1") # Simulates C2 making 1 AoO
        self.assertEqual(self.combatant2.aoo_made_this_round, 1)

        self.assertTrue(self.engine.can_make_aoo(self.combatant2))
        self.engine.trigger_attacks_of_opportunity(self.combatant1, "provoking action 2") # C2 makes 2nd AoO
        self.assertEqual(self.combatant2.aoo_made_this_round, 2)

        self.assertTrue(self.engine.can_make_aoo(self.combatant2))
        self.engine.trigger_attacks_of_opportunity(self.combatant1, "provoking action 3") # C2 makes 3rd AoO
        self.assertEqual(self.combatant2.aoo_made_this_round, 3)

        self.assertFalse(self.engine.can_make_aoo(self.combatant2)) # Maxed out


    def test_aoo_flat_footed_no_combat_reflexes(self):
        self.combatant2.is_flat_footed = True
        self.combatant2.feats = [] # Ensure no Combat Reflexes
        self.assertFalse(self.engine.can_make_aoo(self.combatant2))

    def test_aoo_flat_footed_with_combat_reflexes(self):
        self.combatant2.is_flat_footed = True # Still flat-footed
        self.combatant2.feats.append("Combat Reflexes")
        self.combatant2.ability_scores.dexterity = 12 # Dex mod +1
        self.combatant2.aoo_made_this_round = 0
        # Even if flat-footed, Combat Reflexes allows AoOs (but without Dex to AC if attacked)
        self.assertTrue(self.engine.can_make_aoo(self.combatant2))


    # 3. Saving Throws
    def test_saving_throw_natural_rolls(self):
        random.seed(10) # d20 roll = 16
        self.assertTrue(self.combatant1.make_saving_throw("reflex", 10)) # 16 + bonus vs 10 = success

        random.seed(15) # d20 roll = 1
        self.assertFalse(self.combatant1.make_saving_throw("fortitude", 0)) # Nat 1 always fails

        random.seed(11) # d20 roll = 20
        self.assertTrue(self.combatant1.make_saving_throw("will", 100)) # Nat 20 always succeeds


    # 4. Condition Effects
    def test_condition_blinded_ac_penalty_miss_chance(self):
        self._set_current_turn(self.combatant1.name)
        self.combatant2.reset_for_combat()
        self.combatant1.reset_for_combat()

        original_ac_c2 = self.combatant2.get_ac("standard")
        self.combatant2.add_condition("blinded")
        # Blinded: -2 AC, loses Dex to AC (effectively flat-footed)
        # get_ac for blinded should be calculated as flat_footed and then -2
        expected_ac_c2 = self.combatant2.get_ac("flat_footed") - 2
        self.assertEqual(self.combatant2.get_ac("standard"), expected_ac_c2)

        # Test miss chance for blinded attacker
        self.combatant1.add_condition("blinded")
        # Force a hit scenario for attack roll, then check miss chance
        random.seed(11) # Ensures d20 roll is 20 for C1's attack (auto hit threat)
                       # And for C1's confirm roll (auto crit)

        # Now, the 50% miss chance from blindness should apply
        # We need to run many trials or seed the miss chance roll
        # For a single test, let's seed the miss chance roll to occur
        missed_due_to_blindness = False
        for i in range(20): # Try a few times to hit the miss chance
            random.seed(i) # Vary the seed for the miss chance part
            initial_hp_c2 = self.combatant2.current_hp
            # Force attack roll to be high (e.g. by temporarily boosting BAB)
            # Or use a seed that makes the attack roll itself high.
            # Let's ensure the attack tries to hit first.
            # We will control the miss chance roll (random.randint(1,100) <= 50)

            # The following seeds for random.randint(1,100) will produce:
            # seed(0) -> 25 (miss)
            # seed(1) -> 28 (miss)
            # seed(2) -> 5 (miss)
            # seed(3) -> 68 (hit)

            # Seed for attack roll and confirm (d20)
            # Seed for miss chance (d100)
            # This is tricky because random is global.
            # Let's assume make_attack uses random.randint(1,20) for attack/confirm
            # and random.randint(1,100) for miss chance.

            # For this test, let's simplify by directly checking the log or a flag if possible
            # Or by mocking random.randint for the miss chance part.

            # Simplified check: make_attack logs the miss chance.
            self.engine.log.clear()
            with unittest.mock.patch('random.randint') as mock_rand:
                # 1st call: attack roll (make it 20)
                # 2nd call: miss chance roll (make it <=50 for miss)
                # 3rd call: (if crit) confirm roll (make it 20)
                mock_rand.side_effect = [20, 25, 20] # Attack=20 (hit), MissChance=25 (miss), Confirm=20 (if reached)
                self.action_handler.take_attack_action(self.combatant1, self.combatant2, 0) # Melee attack

            if f"missed due to 50% miss chance" in self.engine.log.get_full_log():
                missed_due_to_blindness = True
                self.assertEqual(self.combatant2.current_hp, initial_hp_c2) # No damage
                break
        self.assertTrue(missed_due_to_blindness, "Attack should have missed due to blindness miss chance")
        self.combatant1.remove_condition("blinded") # cleanup

    def test_condition_prone_ac_attack_mods(self):
        self.combatant1.reset_for_combat()
        self.combatant2.reset_for_combat()
        self._set_current_turn(self.combatant1.name)

        # C2 (target) is prone
        self.combatant2.add_condition("prone")
        ac_std_c2 = self.combatant2.get_ac("standard") # Base AC while prone (dex applies if not flat_footed)

        # C1 (attacker) attacks C2 (prone) with melee (Longsword, index 0)
        # C2 should have -4 AC vs this melee attack.
        # So, effective AC for C1's attack should be ac_std_c2 - 4.
        # This is handled inside make_attack logging.
        self.engine.log.clear()
        self.action_handler.take_attack_action(self.combatant1, self.combatant2, 0)
        self.assertIn(f"{self.combatant2.name} is prone, -4 AC vs melee attack.", self.engine.log.get_full_log())

        # C1 (attacker) attacks C2 (prone) with ranged (Shortbow, index 1)
        # C2 should have +4 AC vs this ranged attack.
        # Effective AC for C1's attack should be ac_std_c2 + 4.
        self.engine.log.clear()
        self.action_handler.take_attack_action(self.combatant1, self.combatant2, 1)
        self.assertIn(f"{self.combatant2.name} is prone, +4 AC vs ranged attack.", self.engine.log.get_full_log())

        # C1 (attacker) is prone, attacks C2 with melee
        self.combatant1.add_condition("prone")
        self.combatant2.remove_condition("prone")
        attack_bonus_melee_prone = self.combatant1.get_attack_bonus(self.combatant1.attacks[0], target=self.combatant2)
        attack_bonus_melee_normal = self.combatant1.get_attack_bonus(self.combatant1.attacks[0], target=self.combatant2) # Re-calculate without prone for base
        self.combatant1.remove_condition("prone") # remove for normal calculation
        attack_bonus_melee_normal_val = self.combatant1.get_attack_bonus(self.combatant1.attacks[0], target=self.combatant2)
        self.combatant1.add_condition("prone") # re-add for the check
        self.assertEqual(attack_bonus_melee_prone, attack_bonus_melee_normal_val - 4, "Melee attack while prone should be -4")

        # C1 (attacker) is prone, attacks C2 with ranged (Shortbow) - should be heavily penalized or disallowed
        attack_bonus_ranged_prone = self.combatant1.get_attack_bonus(self.combatant1.attacks[1], target=self.combatant2)
        self.assertLess(attack_bonus_ranged_prone, attack_bonus_melee_normal_val - 10) # Expect very large penalty

        self.combatant1.remove_condition("prone")


    def test_condition_stunned_action_restriction_ac(self):
        self.combatant1.add_condition("stunned")
        self.assertFalse(self.action_handler.can_take_action(self.combatant1, ActionType.STANDARD))
        self.assertFalse(self.action_handler.can_take_action(self.combatant1, ActionType.MOVE))
        self.assertFalse(self.action_handler.can_take_action(self.combatant1, ActionType.FULL_ROUND))

        # Stunned: -2 AC, loses Dex to AC
        ac_normal = self.combatant1.get_ac("standard") # Get AC without stun to compare
        self.combatant1.remove_condition("stunned")
        ac_val_normal = self.combatant1.get_ac("standard")
        self.combatant1.add_condition("stunned")

        ac_stunned_flat_footed = self.combatant1.get_ac("flat_footed") # Loses dex
        expected_ac_stunned = ac_stunned_flat_footed - 2
        self.assertEqual(self.combatant1.get_ac("standard"), expected_ac_stunned)


if __name__ == '__main__':
    unittest.main()
