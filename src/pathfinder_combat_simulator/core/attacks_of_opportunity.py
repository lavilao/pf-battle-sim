"""
Attacks of Opportunity (AoO) System for Pathfinder Battle Simulator.

This module implements:
- AoO triggers and conditions
- Combatant state tracking for AoO availability
- Reaction system for AoO resolution
- Movement interruption when AoO hits
- Combat Reflexes and Improved AoO feat support
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, FrozenSet
from enum import Enum, auto
import random

from .combatant import Combatant
from .attack import Attack
from .attack_result import AttackResult
from .positioning import Position, CombatantPosition, Size
from .combat_log import CombatLog
from .enums import DamageType, AttackType
from .combat_log import CombatLog

if TYPE_CHECKING:
    from .combat_engine import CombatEngine


class AoOTriggerType(Enum):
    """Types of actions that can provoke an Attack of Opportunity."""
    MOVEMENT = "movement"  # Moving out of threatened square
    FIVE_FOOT_STEP = "five_foot_step"  # 5-foot step (doesn't provoke)
    WITHDRAW = "withdraw"  # Withdraw action (doesn't provoke)
    CAST_SPELL_SOMATIC = "cast_spell_somatic"  # Spell with somatic component
    RANGED_ATTACK = "ranged_attack"  # Making a ranged attack
    RANGED_WEAPON_THREATENED = "ranged_weapon_threatened"  # Using ranged weapon while threatened
    DRINK_POTION = "drink_potion"  # Drinking a potion
    USE_CONSUMABLE = "use_consumable"  # Using a consumable item
    STAND_UP = "stand_up"  # Standing up from prone
    SHEATHE_WEAPON = "sheathe_weapon"  # Sheathing a weapon
    DRAW_WEAPON = "draw_weapon"  # Drawing a weapon (doesn't provoke)
    ATTACK = "attack"  # Making an attack (AoO on attacker)
    GRAPPLE = "grapple"  # Initiating a grapple
    BULL_RUSH = "bull_rush"  # Bull rush attempt
    TRIP = "trip"  # Trip attempt
    DISARM = "disarm"  # Disarm attempt
    SUNDER = "sunder"  # Sunder attempt


class AoOResult(Enum):
    """Result of an Attack of Opportunity."""
    MISS = "miss"
    HIT = "hit"
    CRITICAL = "critical"
    INTERRUPTED = "interrupted"  # Action was interrupted due to hit


@dataclass
class AttackOfOpportunity:
    """
    Represents a single Attack of Opportunity.
    
    Attributes:
        attacker: The combatant making the AoO
        target: The combatant provoking the AoO
        attack: The attack used for the AoO
        trigger_type: What triggered this AoO
        is_hit: Whether the AoO hit
        is_critical: Whether the AoO was a critical hit
        damage: Damage dealt by the AoO
        interrupted_action: Whether the action was interrupted
        original_action: Description of the action that was interrupted
    """
    attacker: Combatant
    target: Combatant
    attack: Attack
    trigger_type: AoOTriggerType
    is_hit: bool = False
    is_critical: bool = False
    damage: int = 0
    interrupted_action: bool = False
    original_action: str = ""


@dataclass
class AoOState:
    """
    Tracks the Attack of Opportunity state for a combatant.
    
    Attributes:
        aoos_remaining: Number of AoOs remaining this round
        aoos_used_this_round: Number of AoOs used this round
        max_aoos_per_round: Maximum AoOs allowed per round
        threatens_enemies: Whether this combatant threatens any enemies
        threatened_squares: Set of positions threatened by this combatant
        last_turn_aoo_count: AoO count at start of turn (for Combat Reflexes)
    """
    aoos_remaining: int = 1
    aoos_used_this_round: int = 0
    max_aoos_per_round: int = 1
    threatens_enemies: bool = False
    threatened_squares: Set[Position] = field(default_factory=set)
    last_turn_aoo_count: int = 0


class AttacksOfOpportunitySystem:
    """
    Main system for managing Attacks of Opportunity.
    
    This system handles:
    - AoO trigger detection and validation
    - Combatant AoO state management
    - AoO resolution as reactions
    - Movement interruption on AoO hits
    - Integration with combat engine and positioning
    """
    
    def __init__(self, combat_log: Optional[CombatLog] = None):
        """
        Initialize the AoO system.
        
        Args:
            combat_log: Optional combat log for recording AoO events
        """
        self.log = combat_log
        # Track AoO state for each combatant by combatant name
        self.aoo_states: Dict[str, AoOState] = {}
    
    def get_aoo_state(self, combatant: Combatant) -> AoOState:
        """Get or create AoO state for a combatant."""
        if combatant.name not in self.aoo_states:
            self.aoo_states[combatant.name] = AoOState()
        return self.aoo_states[combatant.name]
    
    def reset_aoo_state(self, combatant: Combatant):
        """Reset AoO state for a new round."""
        aoo_state = self.get_aoo_state(combatant)
        
        # Calculate max AoOs based on feats
        max_aoos = self.get_max_aoos(combatant)
        
        aoo_state.aoos_remaining = max_aoos
        aoo_state.aoos_used_this_round = 0
        aoo_state.max_aoos_per_round = max_aoos
    
    def get_max_aoos(self, combatant: Combatant) -> int:
        """
        Calculate the maximum number of AoOs a combatant can make per round.
        
        Args:
            combatant: The combatant to check
            
        Returns:
            Maximum number of AoOs per round
        """
        # Base: 1 AoO per round
        max_aoos = 1
        
        # Combat Reflexes feat: Additional AoOs equal to Dex mod
        if "Combat Reflexes" in combatant.feats:
            dex_mod = combatant.ability_scores.get_modifier("dexterity")
            max_aoos += max(0, dex_mod)
        
        return max_aoos
    
    def can_make_aoo(
        self, 
        combatant: Combatant, 
        target: Optional[Combatant] = None,
        target_position: Optional[Position] = None
    ) -> bool:
        """
        Check if a combatant can make an Attack of Opportunity.
        
        Args:
            combatant: The combatant attempting to make an AoO
            target: Optional target to check if threatened
            target_position: Optional target position to check if threatened
            
        Returns:
            True if the combatant can make an AoO
        """
        # Cannot make AoOs if flat-footed, unless they have Combat Reflexes feat
        if combatant.is_flat_footed and "Combat Reflexes" not in combatant.feats:
            return False
        
        # Conditions that prevent AoOs
        if (combatant.has_condition("stunned") or
            combatant.has_condition("paralyzed") or
            combatant.has_condition("helpless") or
            combatant.has_condition("unconscious") or
            combatant.is_dead() or
            combatant.has_condition("dying")):
            return False
        
        # Check AoO availability
        aoo_state = self.get_aoo_state(combatant)
        if aoo_state.aoos_remaining <= 0:
            return False
        
        # If target/target_position provided, check if they are threatened
        if target is not None and target_position is None:
            if target.position_info:
                target_position = target.position_info.position
            else:
                # Fallback: assume target position is threatened if no position info
                return True  # Cannot determine, assume yes for now
        
        if target_position is not None:
            threatened_squares = self.get_threatened_squares(combatant)
            if target_position not in threatened_squares:
                return False
        
        return True
    
    def get_threatened_squares(self, combatant: Combatant) -> Set[Position]:
        """
        Get the squares threatened by a combatant.
        
        Args:
            combatant: The combatant to check
            
        Returns:
            Set of positions threatened by the combatant
        """
        if combatant.position_info:
            # Use the combatant's position info to calculate threatened squares
            weapon_reach = self._get_weapon_reach(combatant)
            return combatant.position_info.get_threatened_squares(weapon_reach)
        else:
            # Fallback: assume adjacent squares are threatened
            threatened = set()
            return threatened
    
    def _get_weapon_reach(self, combatant: Combatant) -> int:
        """
        Get the reach of the combatant's weapon for AoO purposes.
        
        Args:
            combatant: The combatant to check
            
        Returns:
            Reach in feet
        """
        # Check for a suitable melee/natural attack
        for attack in combatant.attacks:
            if (attack.attack_type.value in ["melee", "natural"] and 
                attack.reach > 0):
                return attack.reach
        
        # Default to 5ft reach
        return 5
    
    def does_action_provoke_aoo(
        self, 
        action_type: AoOTriggerType, 
        combatant: Combatant
    ) -> bool:
        """
        Check if an action type provokes an Attack of Opportunity.
        
        Args:
            action_type: The type of action being taken
            combatant: The combatant taking the action
            
        Returns:
            True if the action provokes AoO
        """
        # Actions that do NOT provoke AoO
        exempt_actions = {
            AoOTriggerType.FIVE_FOOT_STEP,
            AoOTriggerType.WITHDRAW,
            AoOTriggerType.DRAW_WEAPON,  # Drawing a weapon is a move action, doesn't provoke
        }
        
        if action_type in exempt_actions:
            return False
        
        # Actions that ALWAYS provoke AoO
        provoking_actions = {
            AoOTriggerType.MOVEMENT,
            AoOTriggerType.CAST_SPELL_SOMATIC,
            AoOTriggerType.RANGED_ATTACK,
            AoOTriggerType.RANGED_WEAPON_THREATENED,
            AoOTriggerType.DRINK_POTION,
            AoOTriggerType.USE_CONSUMABLE,
            AoOTriggerType.STAND_UP,
            AoOTriggerType.SHEATHE_WEAPON,
            AoOTriggerType.ATTACK,
            AoOTriggerType.GRAPPLE,
            AoOTriggerType.BULL_RUSH,
            AoOTriggerType.TRIP,
            AoOTriggerType.DISARM,
            AoOTriggerType.SUNDER,
        }
        
        if action_type in provoking_actions:
            return True
        
        return False
    
    def get_provoking_combatants(
        self, 
        provoking_combatant: Combatant,
        all_combatants: List[Combatant]
    ) -> List[Combatant]:
        """
        Get all combatants that can make an AoO against the provoking combatant.
        
        Args:
            provoking_combatant: The combatant performing the provoking action
            all_combatants: List of all combatants in combat
            
        Returns:
            List of combatants that can make an AoO
        """
        potential_attackers = []
        
        # Get the provoking combatant's position
        provoking_pos = None
        if provoking_combatant.position_info:
            provoking_pos = provoking_combatant.position_info.position
        
        for combatant in all_combatants:
            # Cannot attack yourself
            if combatant == provoking_combatant:
                continue
            
            # Cannot be dead or unable to act
            if combatant.is_dead() or combatant.has_condition("unconscious"):
                continue
            
            # Must be able to make an AoO
            if not self.can_make_aoo(combatant):
                continue
            
            # Must threaten the provoking combatant's position
            if provoking_pos is not None:
                threatened_squares = self.get_threatened_squares(combatant)
                if provoking_pos not in threatened_squares:
                    continue
            
            # Must be on opposite team (not allies)
            # This is a simplification - in practice, allies can threaten each other
            # For now, assume all non-provocateurs can be enemies
            
            potential_attackers.append(combatant)
        
        return potential_attackers
    
    def resolve_attack_of_opportunity(
        self,
        attacker: Combatant,
        target: Combatant,
        trigger_type: AoOTriggerType,
        original_action: str,
        combat_engine: 'CombatEngine'
    ) -> AttackOfOpportunity:
        """
        Resolve an Attack of Opportunity.
        
        Args:
            attacker: The combatant making the AoO
            target: The combatant provoking the AoO
            trigger_type: What triggered this AoO
            original_action: Description of the action being interrupted
            combat_engine: The combat engine for attack resolution
            
        Returns:
            AttackOfOpportunity with resolution results
        """
        # Find a suitable attack for the AoO
        attack = self._select_aoo_attack(attacker)
        
        if attack is None:
            # No suitable attack found
            if self.log:
                self.log.add_entry(
                    f"  {attacker.name} could make an AoO but has no suitable attack."
                )
            return AttackOfOpportunity(
                attacker=attacker,
                target=target,
                attack=Attack(
                    name="None", 
                    damage_dice="1d0", 
                    critical_threat_range="20", 
                    critical_multiplier="x2", 
                    damage_type=DamageType.BLUDGEONING,
                    attack_type=AttackType.MELEE
                ),
                trigger_type=trigger_type,
                original_action=original_action
            )
        
        # Create the AoO record
        aoo = AttackOfOpportunity(
            attacker=attacker,
            target=target,
            attack=attack,
            trigger_type=trigger_type,
            original_action=original_action
        )
        
        # Make the attack using combat engine
        result = combat_engine.make_attack(attacker, target, attack, is_aoo=True)
        
        if result is None:
            return aoo
        
        # Update AoO state
        aoo.is_hit = result.is_hit
        aoo.is_critical = result.is_critical_hit
        aoo.damage = result.total_damage
        
        # Log the AoO
        if self.log:
            self.log.add_entry(
                f"  {attacker.name} makes AoO against {target.name} with {attack.name}"
            )
            if aoo.is_hit:
                if aoo.is_critical:
                    self.log.add_entry(f"  CRITICAL HIT! {aoo.damage} damage!")
                else:
                    self.log.add_entry(f"  HIT! {aoo.damage} damage!")
            else:
                self.log.add_entry(f"  MISS!")
        
        # Increment AoO usage
        aoo_state = self.get_aoo_state(attacker)
        aoo_state.aoos_remaining -= 1
        aoo_state.aoos_used_this_round += 1
        
        # Check if action was interrupted
        if aoo.is_hit and self._action_interrupted(target):
            aoo.interrupted_action = True
            if self.log:
                self.log.add_entry(f"  {target.name}'s action ({original_action}) is interrupted!")
        
        return aoo
    
    def _select_aoo_attack(self, combatant: Combatant) -> Optional[Attack]:
        """
        Select the best attack for an Attack of Opportunity.
        
        Args:
            combatant: The combatant making the AoO
            
        Returns:
            The selected attack or None if no suitable attack
        """
        # Look for melee or natural attacks
        for attack in combatant.attacks:
            if (attack.attack_type.value in ["melee", "natural"] and 
                attack.reach > 0):
                return attack
        
        # If no melee weapon, use unarmed strike if available
        # This would require a different mechanism
        
        return None
    
    def _action_interrupted(self, combatant: Combatant) -> bool:
        """
        Check if an action was interrupted by the AoO.
        
        An action is interrupted if the combatant is:
        - Dead
        - Unconscious
        - Stunned
        - Paralyzed
        
        Args:
            combatant: The combatant to check
            
        Returns:
            True if the action was interrupted
        """
        return (
            combatant.is_dead() or
            combatant.has_condition("unconscious") or
            combatant.has_condition("stunned") or
            combatant.has_condition("paralyzed")
        )
    
    def check_movement_aoo(
        self,
        moving_combatant: Combatant,
        from_position: Position,
        to_position: Position,
        path: List[Position],
        all_combatants: List[Combatant],
        combat_engine: 'CombatEngine',
        is_withdraw: bool = False,
        is_five_foot_step: bool = False
    ) -> Tuple[bool, Optional[Position]]:
        """
        Check for AoOs during movement and handle movement interruption.
        
        Args:
            moving_combatant: The combatant moving
            from_position: Starting position
            to_position: Target position
            path: List of positions being traversed
            all_combatants: All combatants in combat
            combat_engine: The combat engine
            is_withdraw: Whether this is a withdraw action
            is_five_foot_step: Whether this is a 5-foot step
            
        Returns:
            Tuple of (movement_stopped, stop_position)
            - movement_stopped: True if movement was stopped by AoO
            - stop_position: Position where movement stopped
        """
        # 5-foot step and withdraw don't provoke AoOs
        if is_five_foot_step or is_withdraw:
            return False, None
        
        # Check each square in the path for AoO threats
        current_pos = from_position
        
        for next_pos in path:
            # Check if any enemy threatens the next position
            potential_attackers = self.get_provoking_combatants(
                moving_combatant, all_combatants
            )
            
            for attacker in potential_attackers:
                # Check if attacker threatens the square being entered
                threatened_squares = self.get_threatened_squares(attacker)
                
                if next_pos in threatened_squares:
                    # Trigger AoO
                    aoo = self.resolve_attack_of_opportunity(
                        attacker=attacker,
                        target=moving_combatant,
                        trigger_type=AoOTriggerType.MOVEMENT,
                        original_action="movement",
                        combat_engine=combat_engine
                    )
                    
                    # If AoO hit, movement is interrupted
                    if aoo.interrupted_action:
                        if self.log:
                            self.log.add_entry(
                                f"  {moving_combatant.name}'s movement interrupted at {next_pos}!"
                            )
                        return True, current_pos
            
            current_pos = next_pos
        
        return False, None
    
    def update_threatened_squares(self, combatant: Combatant):
        """
        Update the threatened squares for a combatant.
        
        Args:
            combatant: The combatant to update
        """
        aoo_state = self.get_aoo_state(combatant)
        aoo_state.threatened_squares = self.get_threatened_squares(combatant)
    
    def update_threatens_enemies(self, combatant: Combatant, enemies: List[Combatant]):
        """
        Update whether a combatant threatens any enemies.
        
        Args:
            combatant: The combatant to check
            enemies: List of enemy combatants
        """
        aoo_state = self.get_aoo_state(combatant)
        
        threatens = False
        for enemy in enemies:
            if enemy.is_dead():
                continue
            
            enemy_pos = None
            if enemy.position_info:
                enemy_pos = enemy.position_info.position
            else:
                continue
            
            threatened_squares = self.get_threatened_squares(combatant)
            if enemy_pos in threatened_squares:
                threatens = True
                break
        
        aoo_state.threatens_enemies = threatens
    
    def get_aoo_summary(self, combatant: Combatant) -> str:
        """
        Get a summary of a combatant's AoO status.
        
        Args:
            combatant: The combatant to check
            
        Returns:
            Summary string
        """
        aoo_state = self.get_aoo_state(combatant)
        
        summary = f"{combatant.name} AoO Status:\n"
        summary += f"  AoOs remaining: {aoo_state.aoos_remaining}/{aoo_state.max_aoos_per_round}\n"
        summary += f"  AoOs used this round: {aoo_state.aoos_used_this_round}\n"
        summary += f"  Threatens enemies: {aoo_state.threatens_enemies}\n"
        summary += f"  Threatened squares: {len(aoo_state.threatened_squares)}\n"
        
        # Check for relevant feats
        if "Combat Reflexes" in combatant.feats:
            summary += "  Has Combat Reflexes feat (extra AoOs based on Dex)\n"
        
        if "Improved Unarmed Strike" in combatant.feats:
            summary += "  Has Improved Unarmed Strike (AoO with unarmed strikes)\n"
        
        return summary


def create_aoo_trigger_from_action(
    action_type: str, 
    action_details: Optional[Dict] = None
) -> AoOTriggerType:
    """
    Convert an action type string to an AoO trigger type.
    
    Args:
        action_type: The action type string
        action_details: Optional additional details about the action
        
    Returns:
        Corresponding AoOTriggerType
    """
    action_mapping = {
        "moving": AoOTriggerType.MOVEMENT,
        "movement": AoOTriggerType.MOVEMENT,
        "five_foot_step": AoOTriggerType.FIVE_FOOT_STEP,
        "withdraw": AoOTriggerType.WITHDRAW,
        "casting": AoOTriggerType.CAST_SPELL_SOMATIC,
        "cast_spell": AoOTriggerType.CAST_SPELL_SOMATIC,
        "ranged_attack": AoOTriggerType.RANGED_ATTACK,
        "ranged attack": AoOTriggerType.RANGED_ATTACK,
        "ranged weapon threatened": AoOTriggerType.RANGED_WEAPON_THREATENED,
        "drinking potion": AoOTriggerType.DRINK_POTION,
        "drink_potion": AoOTriggerType.DRINK_POTION,
        "drink potion": AoOTriggerType.DRINK_POTION,
        "using consumable": AoOTriggerType.USE_CONSUMABLE,
        "use_consumable": AoOTriggerType.USE_CONSUMABLE,
        "standing up": AoOTriggerType.STAND_UP,
        "stand_up": AoOTriggerType.STAND_UP,
        "standing from prone": AoOTriggerType.STAND_UP,
        "sheathing": AoOTriggerType.SHEATHE_WEAPON,
        "sheathe": AoOTriggerType.SHEATHE_WEAPON,
        "drawing weapon": AoOTriggerType.DRAW_WEAPON,
        "draw": AoOTriggerType.DRAW_WEAPON,
        "attacking": AoOTriggerType.ATTACK,
        "attack": AoOTriggerType.ATTACK,
        "grapple": AoOTriggerType.GRAPPLE,
        "grappling": AoOTriggerType.GRAPPLE,
        "bull_rush": AoOTriggerType.BULL_RUSH,
        "bull rush": AoOTriggerType.BULL_RUSH,
        "trip": AoOTriggerType.TRIP,
        "tripping": AoOTriggerType.TRIP,
        "disarm": AoOTriggerType.DISARM,
        "disarming": AoOTriggerType.DISARM,
        "sunder": AoOTriggerType.SUNDER,
        "sundering": AoOTriggerType.SUNDER,
    }
    
    # Normalize the action type
    normalized = action_type.lower().strip()
    
    return action_mapping.get(normalized, AoOTriggerType.MOVEMENT)
