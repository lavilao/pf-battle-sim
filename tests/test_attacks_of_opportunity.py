"""
Tests for the Attacks of Opportunity (AoO) System.
"""

import pytest
from pathfinder_combat_simulator.core import (
    Combatant,
    Attack,
    Position,
    Size,
    Facing,
    CombatLog,
    AttacksOfOpportunitySystem,
    AttackOfOpportunity,
    AoOState,
    AoOTriggerType,
    AoOResult,
    DamageType,
    AttackType,
    CombatEngine,
    CombatantPosition,
)
from pathfinder_combat_simulator.core.enums import ConditionType


class TestAoOTriggerType:
    """Tests for AoOTriggerType enum."""
    
    def test_trigger_types_exist(self):
        """Test that all expected trigger types exist."""
        expected_triggers = [
            "MOVEMENT",
            "FIVE_FOOT_STEP",
            "WITHDRAW",
            "CAST_SPELL_SOMATIC",
            "RANGED_ATTACK",
            "RANGED_WEAPON_THREATENED",
            "DRINK_POTION",
            "USE_CONSUMABLE",
            "STAND_UP",
            "SHEATHE_WEAPON",
            "DRAW_WEAPON",
            "ATTACK",
            "GRAPPLE",
            "BULL_RUSH",
            "TRIP",
            "DISARM",
            "SUNDER",
        ]
        
        for trigger in expected_triggers:
            assert hasattr(AoOTriggerType, trigger), f"Missing trigger type: {trigger}"
    
    def test_trigger_type_values(self):
        """Test that trigger types have expected string values."""
        assert AoOTriggerType.MOVEMENT.value == "movement"
        assert AoOTriggerType.FIVE_FOOT_STEP.value == "five_foot_step"
        assert AoOTriggerType.WITHDRAW.value == "withdraw"


class TestAoOState:
    """Tests for AoOState dataclass."""
    
    def test_default_aoo_state(self):
        """Test default AoO state values."""
        state = AoOState()
        
        assert state.aoos_remaining == 1
        assert state.aoos_used_this_round == 0
        assert state.max_aoos_per_round == 1
        assert state.threatens_enemies == False
        assert state.threatened_squares == set()
        assert state.last_turn_aoo_count == 0
    
    def test_custom_aoo_state(self):
        """Test custom AoO state values."""
        threatened_squares = {Position(1, 1), Position(1, 2)}
        state = AoOState(
            aoos_remaining=3,
            aoos_used_this_round=1,
            max_aoos_per_round=4,
            threatens_enemies=True,
            threatened_squares=threatened_squares,
            last_turn_aoo_count=2,
        )
        
        assert state.aoos_remaining == 3
        assert state.aoos_used_this_round == 1
        assert state.max_aoos_per_round == 4
        assert state.threatens_enemies == True
        assert state.threatened_squares == threatened_squares
        assert state.last_turn_aoo_count == 2


class TestAttackOfOpportunity:
    """Tests for AttackOfOpportunity dataclass."""
    
    def _create_test_attack(self):
        """Create a test attack."""
        return Attack(
            name="Longsword",
            damage_dice="1d8",
            critical_threat_range="19-20",
            critical_multiplier="x2",
            damage_type=DamageType.SLASHING,
            attack_type=AttackType.MELEE,
            reach=5,
        )
    
    def _create_test_combatants(self):
        """Create test combatants."""
        attacker = Combatant(name="Warrior", is_pc=True)
        attacker.attacks.append(self._create_test_attack())
        
        target = Combatant(name="Goblin", is_pc=False)
        
        return attacker, target
    
    def test_default_attack_of_opportunity(self):
        """Test default AttackOfOpportunity values."""
        attacker, target = self._create_test_combatants()
        attack = self._create_test_attack()
        
        aoo = AttackOfOpportunity(
            attacker=attacker,
            target=target,
            attack=attack,
            trigger_type=AoOTriggerType.MOVEMENT,
        )
        
        assert aoo.attacker == attacker
        assert aoo.target == target
        assert aoo.attack == attack
        assert aoo.trigger_type == AoOTriggerType.MOVEMENT
        assert aoo.is_hit == False
        assert aoo.is_critical == False
        assert aoo.damage == 0
        assert aoo.interrupted_action == False
        assert aoo.original_action == ""
    
    def test_filled_attack_of_opportunity(self):
        """Test AttackOfOpportunity with all values set."""
        attacker, target = self._create_test_combatants()
        attack = self._create_test_attack()
        
        aoo = AttackOfOpportunity(
            attacker=attacker,
            target=target,
            attack=attack,
            trigger_type=AoOTriggerType.RANGED_ATTACK,
            is_hit=True,
            is_critical=True,
            damage=12,
            interrupted_action=True,
            original_action="firing a bow",
        )
        
        assert aoo.is_hit == True
        assert aoo.is_critical == True
        assert aoo.damage == 12
        assert aoo.interrupted_action == True
        assert aoo.original_action == "firing a bow"


class TestAttacksOfOpportunitySystem:
    """Tests for AttacksOfOpportunitySystem class."""
    
    def test_system_initialization(self):
        """Test system initialization."""
        log = CombatLog()
        system = AttacksOfOpportunitySystem(combat_log=log)
        
        assert system.log == log
        assert system.aoo_states == {}
    
    def test_get_aoo_state_new_combatant(self):
        """Test getting AoO state for a new combatant."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        
        state = system.get_aoo_state(combatant)
        
        assert isinstance(state, AoOState)
        assert state.aoos_remaining == 1
        assert state.aoos_used_this_round == 0
    
    def test_get_aoo_state_existing_combatant(self):
        """Test getting AoO state for an existing combatant."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        
        # Get state twice - should return same state
        state1 = system.get_aoo_state(combatant)
        state2 = system.get_aoo_state(combatant)
        
        assert state1 is state2
    
    def test_reset_aoo_state(self):
        """Test resetting AoO state for a new round."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        
        # Modify state
        state = system.get_aoo_state(combatant)
        state.aoos_remaining = 0
        state.aoos_used_this_round = 3
        
        # Reset
        system.reset_aoo_state(combatant)
        
        # Check reset values
        state = system.get_aoo_state(combatant)
        assert state.aoos_remaining == 1
        assert state.aoos_used_this_round == 0
    
    def test_get_max_aoos_base(self):
        """Test max AoOs for base combatant."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        
        max_aoos = system.get_max_aoos(combatant)
        
        assert max_aoos == 1
    
    def test_get_max_aoos_with_combat_reflexes(self):
        """Test max AoOs with Combat Reflexes feat."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        combatant.feats.append("Combat Reflexes")
        combatant.ability_scores.strength = 14
        combatant.ability_scores.dexterity = 16  # +3 Dex mod
        
        max_aoos = system.get_max_aoos(combatant)
        
        # Base 1 + Dex mod 3 = 4
        assert max_aoos == 4
    
    def test_can_make_aoo_flat_footed_no_reflexes(self):
        """Test cannot make AoO when flat-footed without Combat Reflexes."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        combatant.is_flat_footed = True
        
        assert system.can_make_aoo(combatant) == False
    
    def test_can_make_aoo_flat_footed_with_reflexes(self):
        """Test can make AoO when flat-footed with Combat Reflexes."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        combatant.is_flat_footed = True
        combatant.feats.append("Combat Reflexes")
        
        assert system.can_make_aoo(combatant) == True
    
    def test_can_make_aoo_stunned(self):
        """Test cannot make AoO when stunned."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        combatant.add_condition("stunned")
        
        assert system.can_make_aoo(combatant) == False
    
    def test_can_make_aoo_no_aoos_remaining(self):
        """Test cannot make AoO when none remaining."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        
        state = system.get_aoo_state(combatant)
        state.aoos_remaining = 0
        
        assert system.can_make_aoo(combatant) == False
    
    def test_does_action_provoke_aoo_exempt(self):
        """Test exempt actions don't provoke AoO."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        
        assert system.does_action_provoke_aoo(AoOTriggerType.FIVE_FOOT_STEP, combatant) == False
        assert system.does_action_provoke_aoo(AoOTriggerType.WITHDRAW, combatant) == False
        assert system.does_action_provoke_aoo(AoOTriggerType.DRAW_WEAPON, combatant) == False
    
    def test_does_action_provoke_aoo_provoking(self):
        """Test provoking actions do provoke AoO."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        
        assert system.does_action_provoke_aoo(AoOTriggerType.MOVEMENT, combatant) == True
        assert system.does_action_provoke_aoo(AoOTriggerType.CAST_SPELL_SOMATIC, combatant) == True
        assert system.does_action_provoke_aoo(AoOTriggerType.RANGED_ATTACK, combatant) == True
        assert system.does_action_provoke_aoo(AoOTriggerType.STAND_UP, combatant) == True
        assert system.does_action_provoke_aoo(AoOTriggerType.DRINK_POTION, combatant) == True


class TestThreatenedSquares:
    """Tests for threatened squares calculation."""
    
    def test_get_threatened_squares_with_position_info(self):
        """Test getting threatened squares with position info."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        
        # Create position info with size Medium (5ft reach)
        combatant.position_info = CombatantPosition(
            position=Position(5, 5),
            facing=Facing.EAST,
            size=Size.MEDIUM,
            natural_reach=5,
        )
        
        threatened = system.get_threatened_squares(combatant)
        
        # With 5ft reach, should threaten adjacent squares (8 squares)
        # Position (5,5) threatens (4,4), (4,5), (4,6), (5,4), (5,6), (6,4), (6,5), (6,6)
        assert len(threatened) > 0
        assert Position(5, 4) in threatened  # West
        assert Position(6, 5) in threatened  # East
        assert Position(5, 6) in threatened  # North
        assert Position(5, 4) in threatened  # South
        # Diagonals
        assert Position(4, 4) in threatened
        assert Position(4, 6) in threatened
        assert Position(6, 4) in threatened
        assert Position(6, 6) in threatened
    
    def test_get_threatened_squares_without_position_info(self):
        """Test getting threatened squares without position info."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        # No position_info set
        
        threatened = system.get_threatened_squares(combatant)
        
        # Should return empty set without position info
        assert threatened == set()


class TestGetProvokingCombatants:
    """Tests for getting combatants that can make AoO."""
    
    def test_no_provoking_combatants(self):
        """Test when no combatants can make AoO."""
        system = AttacksOfOpportunitySystem()
        
        provoker = Combatant(name="Provoker")
        provoker.position_info = CombatantPosition(
            position=Position(5, 5),
            facing=Facing.EAST,
            size=Size.MEDIUM,
        )
        
        all_combatants = [provoker]
        
        result = system.get_provoking_combatants(provoker, all_combatants)
        
        # Only one combatant (the provoker), so no attackers
        assert result == []
    
    def test_one_provoking_combatant(self):
        """Test when one combatant can make AoO."""
        system = AttacksOfOpportunitySystem()
        
        provoker = Combatant(name="Provoker")
        provoker.position_info = CombatantPosition(
            position=Position(5, 5),
            facing=Facing.EAST,
            size=Size.MEDIUM,
        )
        
        attacker = Combatant(name="Warrior")
        attacker.position_info = CombatantPosition(
            position=Position(5, 4),  # Adjacent to provoker
            facing=Facing.EAST,
            size=Size.MEDIUM,
        )
        
        all_combatants = [provoker, attacker]
        
        result = system.get_provoking_combatants(provoker, all_combatants)
        
        assert len(result) == 1
        assert result[0] == attacker
    
    def test_dead_combatant_not_included(self):
        """Test that dead combatants are not included."""
        system = AttacksOfOpportunitySystem()
        
        provoker = Combatant(name="Provoker")
        provoker.position_info = CombatantPosition(
            position=Position(5, 5),
            facing=Facing.EAST,
            size=Size.MEDIUM,
        )
        
        dead_attacker = Combatant(name="Dead Warrior")
        dead_attacker.position_info = CombatantPosition(
            position=Position(5, 4),
            facing=Facing.EAST,
            size=Size.MEDIUM,
        )
        dead_attacker.current_hp = -5
        
        all_combatants = [provoker, dead_attacker]
        
        result = system.get_provoking_combatants(provoker, all_combatants)
        
        assert result == []


class TestActionInterrupted:
    """Tests for action interruption logic."""
    
    def test_action_interrupted_on_death(self):
        """Test action is interrupted when combatant dies."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        combatant.current_hp = -5
        
        assert system._action_interrupted(combatant) == True
    
    def test_action_interrupted_on_unconscious(self):
        """Test action is interrupted when combatant is unconscious."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        combatant.add_condition("unconscious")
        
        assert system._action_interrupted(combatant) == True
    
    def test_action_interrupted_on_stunned(self):
        """Test action is interrupted when combatant is stunned."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        combatant.add_condition("stunned")
        
        assert system._action_interrupted(combatant) == True
    
    def test_action_not_interrupted_on_prone(self):
        """Test action is not interrupted when combatant is prone."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        combatant.add_condition("prone")
        
        assert system._action_interrupted(combatant) == False
    
    def test_action_not_interrupted_healthy(self):
        """Test action is not interrupted when combatant is healthy."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        
        assert system._action_interrupted(combatant) == False


class TestAoOSummary:
    """Tests for AoO summary functionality."""
    
    def test_aoo_summary(self):
        """Test getting AoO summary for a combatant."""
        system = AttacksOfOpportunitySystem()
        combatant = Combatant(name="Test Fighter")
        combatant.feats.append("Combat Reflexes")
        combatant.ability_scores.dexterity = 16
        
        state = system.get_aoo_state(combatant)
        state.aoos_remaining = 2
        state.aoos_used_this_round = 1
        state.threatens_enemies = True
        
        summary = system.get_aoo_summary(combatant)
        
        assert "Test Fighter AoO Status:" in summary
        assert "AoOs remaining: 2/4" in summary  # 1 base + 3 Dex mod
        assert "AoOs used this round: 1" in summary
        assert "Threatens enemies: True" in summary
        assert "Combat Reflexes" in summary


class TestCreateAoOTriggerFromAction:
    """Tests for creating AoO triggers from action strings."""
    
    def test_movement_action(self):
        """Test converting movement action to trigger."""
        from pathfinder_combat_simulator.core.attacks_of_opportunity import (
            create_aoo_trigger_from_action,
        )
        
        result = create_aoo_trigger_from_action("moving")
        assert result == AoOTriggerType.MOVEMENT
        
        result = create_aoo_trigger_from_action("movement")
        assert result == AoOTriggerType.MOVEMENT
    
    def test_five_foot_step(self):
        """Test converting five-foot step to trigger."""
        from pathfinder_combat_simulator.core.attacks_of_opportunity import (
            create_aoo_trigger_from_action,
        )
        
        result = create_aoo_trigger_from_action("five_foot_step")
        assert result == AoOTriggerType.FIVE_FOOT_STEP
    
    def test_withdraw(self):
        """Test converting withdraw to trigger."""
        from pathfinder_combat_simulator.core.attacks_of_opportunity import (
            create_aoo_trigger_from_action,
        )
        
        result = create_aoo_trigger_from_action("withdraw")
        assert result == AoOTriggerType.WITHDRAW
    
    def test_cast_spell(self):
        """Test converting spell casting to trigger."""
        from pathfinder_combat_simulator.core.attacks_of_opportunity import (
            create_aoo_trigger_from_action,
        )
        
        result = create_aoo_trigger_from_action("casting")
        assert result == AoOTriggerType.CAST_SPELL_SOMATIC
        
        result = create_aoo_trigger_from_action("cast_spell")
        assert result == AoOTriggerType.CAST_SPELL_SOMATIC
    
    def test_ranged_attack(self):
        """Test converting ranged attack to trigger."""
        from pathfinder_combat_simulator.core.attacks_of_opportunity import (
            create_aoo_trigger_from_action,
        )
        
        result = create_aoo_trigger_from_action("ranged_attack")
        assert result == AoOTriggerType.RANGED_ATTACK
    
    def test_stand_up(self):
        """Test converting stand up to trigger."""
        from pathfinder_combat_simulator.core.attacks_of_opportunity import (
            create_aoo_trigger_from_action,
        )
        
        result = create_aoo_trigger_from_action("standing up")
        assert result == AoOTriggerType.STAND_UP
    
    def test_drink_potion(self):
        """Test converting drink potion to trigger."""
        from pathfinder_combat_simulator.core.attacks_of_opportunity import (
            create_aoo_trigger_from_action,
        )
        
        result = create_aoo_trigger_from_action("drinking potion")
        assert result == AoOTriggerType.DRINK_POTION
    
    def test_unknown_action_defaults_to_movement(self):
        """Test unknown action defaults to movement trigger."""
        from pathfinder_combat_simulator.core.attacks_of_opportunity import (
            create_aoo_trigger_from_action,
        )
        
        result = create_aoo_trigger_from_action("unknown_action")
        assert result == AoOTriggerType.MOVEMENT
