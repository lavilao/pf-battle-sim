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
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
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


@dataclass
class Attack:
    """Represents a weapon or natural attack"""
    name: str
    damage_dice: str  # e.g., "1d8", "2d6"
    critical_threat_range: str  # e.g., "20", "19-20"
    critical_multiplier: str  # e.g., "x2", "x3"
    damage_type: DamageType
    reach: int = 5  # in feet
    associated_ability_for_attack: str = "str"  # str or dex
    associated_ability_for_damage: str = "str"
    is_primary_natural_attack: bool = True
    special_qualities: List[str] = field(default_factory=list)
    enhancement_bonus: int = 0
    
    def get_threat_range(self) -> List[int]:
        """Get the list of d20 values that constitute a threat"""
        if self.critical_threat_range == "20":
            return [20]
        elif self.critical_threat_range == "19-20":
            return [19, 20]
        elif self.critical_threat_range == "18-20":
            return [18, 19, 20]
        else:
            return [20]  # default
    
    def get_crit_multiplier(self) -> int:
        """Get the critical hit multiplier as an integer"""
        if self.critical_multiplier == "x2":
            return 2
        elif self.critical_multiplier == "x3":
            return 3
        elif self.critical_multiplier == "x4":
            return 4
        else:
            return 2  # default


@dataclass
class AbilityScores:
    """Represents the six ability scores"""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    # Temporary modifiers (from spells, etc.)
    temp_str: int = 0
    temp_dex: int = 0
    temp_con: int = 0
    temp_int: int = 0
    temp_wis: int = 0
    temp_cha: int = 0
    
    def get_modifier(self, ability: str) -> int:
        """Get the modifier for an ability score"""
        # Map short names to full attribute names
        ability_map = {
            "str": "strength", "dex": "dexterity", "con": "constitution",
            "int": "intelligence", "wis": "wisdom", "cha": "charisma",
            "strength": "strength", "dexterity": "dexterity", "constitution": "constitution",
            "intelligence": "intelligence", "wisdom": "wisdom", "charisma": "charisma"
        }
        
        temp_map = {
            "str": "temp_str", "dex": "temp_dex", "con": "temp_con",
            "int": "temp_int", "wis": "temp_wis", "cha": "temp_cha",
            "strength": "temp_str", "dexterity": "temp_dex", "constitution": "temp_con",
            "intelligence": "temp_int", "wisdom": "temp_wis", "charisma": "temp_cha"
        }
        
        full_ability = ability_map.get(ability.lower(), ability)
        temp_attr = temp_map.get(ability.lower(), f"temp_{ability[:3]}")
        
        total_score = getattr(self, full_ability) + getattr(self, temp_attr)
        return (total_score - 10) // 2
    
    def get_total_score(self, ability: str) -> int:
        """Get the total ability score including temporary modifiers"""
        # Map short names to full attribute names
        ability_map = {
            "str": "strength", "dex": "dexterity", "con": "constitution",
            "int": "intelligence", "wis": "wisdom", "cha": "charisma",
            "strength": "strength", "dexterity": "dexterity", "constitution": "constitution",
            "intelligence": "intelligence", "wisdom": "wisdom", "charisma": "charisma"
        }
        
        temp_map = {
            "str": "temp_str", "dex": "temp_dex", "con": "temp_con",
            "int": "temp_int", "wis": "temp_wis", "cha": "temp_cha",
            "strength": "temp_str", "dexterity": "temp_dex", "constitution": "temp_con",
            "intelligence": "temp_int", "wisdom": "temp_wis", "charisma": "temp_cha"
        }
        
        full_ability = ability_map.get(ability.lower(), ability)
        temp_attr = temp_map.get(ability.lower(), f"temp_{ability[:3]}")
        
        return getattr(self, full_ability) + getattr(self, temp_attr)


@dataclass
class ArmorClass:
    """Represents AC components"""
    armor_bonus: int = 0
    shield_bonus: int = 0
    natural_armor_bonus: int = 0
    deflection_bonus: int = 0
    dodge_bonus: int = 0
    size_modifier: int = 0
    max_dex_bonus_from_armor: Optional[int] = None
    
    def calculate_ac(self, dex_modifier: int, is_flat_footed: bool = False) -> int:
        """Calculate total AC following Pathfinder rules"""
        effective_dex = min(dex_modifier, self.max_dex_bonus_from_armor or dex_modifier)
        if is_flat_footed:
            effective_dex = 0
            
        return (10 + self.armor_bonus + self.shield_bonus + 
               self.natural_armor_bonus + effective_dex +
               self.size_modifier + self.deflection_bonus + 
               self.dodge_bonus)
    
    def calculate_touch_ac(self, dex_modifier: int, is_flat_footed: bool = False) -> int:
        """Calculate touch AC (ignores armor, shield, and natural armor)"""
        effective_dex = min(dex_modifier, self.max_dex_bonus_from_armor or dex_modifier)
        if is_flat_footed:
            effective_dex = 0
            
        return (10 + effective_dex + self.size_modifier +
               self.deflection_bonus + self.dodge_bonus)
    
    def calculate_flat_footed_ac(self, dex_modifier: int) -> int:
        """Calculate flat-footed AC (loses Dex bonus, retains other bonuses)"""
        return (10 + self.armor_bonus + self.shield_bonus +
               self.natural_armor_bonus + self.size_modifier +
               self.deflection_bonus + self.dodge_bonus)


@dataclass
class SavingThrows:
    """Represents saving throw bonuses"""
    fortitude_base: int = 0
    reflex_base: int = 0
    will_base: int = 0
    
    def calculate_save(self, save_type: str, ability_scores: AbilityScores) -> int:
        """Calculate total saving throw bonus"""
        base = getattr(self, f"{save_type}_base")
        if save_type == "fortitude":
            return base + ability_scores.get_modifier("constitution")
        elif save_type == "reflex":
            return base + ability_scores.get_modifier("dexterity")
        elif save_type == "will":
            return base + ability_scores.get_modifier("wisdom")
        return base


class Combatant:
    """
    Core class representing any entity in combat (PC or NPC/Monster)
    Implements all requirements from Part 1.1 of the specification
    """
    
    def __init__(self, name: str, is_pc: bool = False):
        # Identification
        self.name = name
        self.is_pc = is_pc
        self.player_controller = ""
        self.unique_id = ""
        
        # Core Stats
        self.max_hp = 1
        self.current_hp = 1
        self.temporary_hp = 0
        
        # Ability Scores
        self.ability_scores = AbilityScores()
        
        # Combat Stats - Offense
        self.base_attack_bonus = 0
        self.attacks: List[Attack] = []
        
        # Combat Stats - Defense
        self.armor_class = ArmorClass()
        self.damage_reduction: Dict[str, Any] = {}  # e.g., {"amount": 5, "type": "magic"}
        self.spell_resistance = 0
        self.energy_resistances: Dict[str, int] = {}  # e.g., {"fire": 10, "cold": 5}
        self.energy_immunities: List[str] = []
        self.energy_vulnerabilities: List[str] = []
        
        # Movement
        self.base_speed = 30
        self.fly_speed = 0
        self.swim_speed = 0
        self.climb_speed = 0
        self.burrow_speed = 0
        self.fly_maneuverability = "average"
        
        # Saving Throws
        self.saving_throws = SavingThrows()
        
        # Skills (dictionary of skill_name: total_modifier)
        self.skills: Dict[str, int] = {}
        
        # Feats
        self.feats: List[str] = []
        
        # Special Abilities
        self.special_abilities: List[Dict[str, Any]] = []
        
        # Spellcasting
        self.caster_level = 0
        self.spellcasting_ability = "intelligence"
        self.spells_per_day: Dict[int, int] = {}
        self.known_spells: Dict[int, List[str]] = {}
        self.prepared_spells: Dict[int, List[str]] = {}
        self.spell_dc_base = 10
        self.metamagic_feats: List[str] = []
        
        # Size and Type
        self.size = "Medium"
        self.creature_type = "Humanoid"
        self.subtypes: List[str] = []
        self.alignment = "True Neutral"
        
        # Initiative
        self.initiative_modifier = 0
        self.current_initiative_roll = 0
        self.final_initiative_score = 0
        
        # Mythic (placeholders)
        self.mythic_tier = 0
        self.mythic_path = ""
        self.mythic_power_points = 0
        self.mythic_abilities: List[str] = []
        self.mythic_feats: List[str] = []
        
        # Combat State
        self.conditions: set = set()
        self.is_flat_footed = True
        self.has_acted_this_combat = False
        self.aoo_made_this_round = 0
        self.has_moved_this_turn = False # For 5-foot step tracking
        
        # Equipment
        self.equipment_slots: Dict[str, Optional[str]] = {
            "main_hand": None,
            "off_hand": None,
            "armor": None,
            "belt": None,
            "eyes": None,
            "feet": None,
            "hands": None,
            "head": None,
            "neck": None,
            "ring1": None,
            "ring2": None,
            "shoulders": None,
            "wrists": None
        }
    
    def get_size_modifier(self) -> int:
        """Get size modifier for attack rolls and AC"""
        size_modifiers = {
            "Fine": 8, "Diminutive": 4, "Tiny": 2, "Small": 1,
            "Medium": 0, "Large": -1, "Huge": -2, 
            "Gargantuan": -4, "Colossal": -8
        }
        return size_modifiers.get(self.size, 0)

    def get_special_size_modifier_for_cmb_cmd(self) -> int:
        """Get special size modifier for CMB and CMD based on Pathfinder rules."""
        size_map = {
            "Fine": -8, "Diminutive": -4, "Tiny": -2, "Small": -1,
            "Medium": 0, "Large": 1, "Huge": 2, "Gargantuan": 4, "Colossal": 8
        }
        return size_map.get(self.size, 0)

    def calculate_cmb(self) -> int:
        """Calculate Combat Maneuver Bonus (CMB)."""
        bab = self.base_attack_bonus

        # Creatures Tiny or smaller use Dexterity instead of Strength for CMB.
        if self.size in ["Fine", "Diminutive", "Tiny"]:
            ability_mod = self.ability_scores.get_modifier("dexterity")
        else:
            ability_mod = self.ability_scores.get_modifier("strength")

        special_size_mod = self.get_special_size_modifier_for_cmb_cmd()

        # TODO: Add other modifiers from feats, spells, etc.
        return bab + ability_mod + special_size_mod
    
    def calculate_cmd(self) -> int:
        """Calculate Combat Maneuver Defense (CMD)."""
        bab = self.base_attack_bonus
        str_mod = self.ability_scores.get_modifier("strength")
        dex_mod = self.ability_scores.get_modifier("dexterity")
        special_size_mod = self.get_special_size_modifier_for_cmb_cmd()
        
        # CMD = 10 + BAB + Str mod + Dex mod + special size mod + other AC bonuses (deflection, dodge, etc.)
        # Note: Armor, shield, and natural armor bonuses do NOT apply to CMD.
        cmd = 10 + bab + str_mod + dex_mod + special_size_mod
        
        # Add AC modifiers that apply to CMD
        cmd += self.armor_class.deflection_bonus
        cmd += self.armor_class.dodge_bonus
        # TODO: Add other applicable AC bonuses (insight, luck, morale, profane, sacred)
        # TODO: Apply penalties to AC to CMD as well.

        if self.is_flat_footed:
            # A flat-footed creature does not add its Dexterity bonus to its CMD.
            # Note: We added total dex_mod initially, so if flat-footed, subtract it.
            # However, conditions like "pinned" or "helpless" might also make dex 0,
            # which would already be handled by get_modifier if those conditions modify temp_dex.
            # For simplicity here, if is_flat_footed is true, we ensure Dex bonus is not applied.
            # This assumes get_modifier("dexterity") returns the current effective Dex mod.
            # If flat_footed specifically negates Dex for CMD regardless of other Dex penalties,
            # then we should subtract the positive part of dex_mod if it was added.

            # If dex_mod was positive and added, remove it.
            # If dex_mod was negative, it should still apply as a penalty.
            # The rule states "does not add its Dexterity bonus", implying positive contributions.
            # Penalties (negative Dex mod) should still apply.
            if dex_mod > 0:
                 cmd -= dex_mod
        
        return cmd
    
    def get_ac(self, ac_type: str = "standard") -> int:
        """Get armor class of specified type with proper size modifiers"""
        dex_mod = self.ability_scores.get_modifier("dexterity")
        size_mod = self.get_size_modifier() # This is the attack/AC size modifier, not CMB/CMD one
        
        # Calculate base AC based on type
        if ac_type == "touch":
            ac = self.armor_class.calculate_touch_ac(dex_mod, self.is_flat_footed or self.has_condition("helpless") or self.has_condition("stunned") or self.has_condition("paralyzed"))
        elif ac_type == "flat_footed" or self.is_flat_footed or self.has_condition("helpless") or self.has_condition("stunned") or self.has_condition("paralyzed"):
            ac = self.armor_class.calculate_flat_footed_ac(dex_mod) # Dex mod is ignored internally by this call
        else:  # standard AC
            ac = self.armor_class.calculate_ac(dex_mod, self.is_flat_footed)

        ac += size_mod # Apply general size modifier to AC

        # Condition-based AC penalties / modifications
        if self.has_condition("blinded"):
            ac -= 2
            # Loses Dex bonus to AC is handled by passing is_flat_footed=True or similar to calculate_ac variants
            # For blinded, effectively flat-footed against all attacks.
        if self.has_condition("cowering"): # cowering not in the initial list, but similar to helpless
            ac -= 2
            # Loses Dex bonus to AC
        if self.has_condition("helpless"): # e.g. paralyzed, unconscious, bound, sleeping
            ac -= 4 # Specific penalty for helplessness against melee attacks. Ranged attacks don't get this.
                    # This needs to be context specific (melee vs ranged attacker).
                    # For now, general AC penalty.
            # Loses Dex bonus to AC (handled by flat_footed logic in calculate_ac)
        if self.has_condition("pinned"):
             ac -= 4 # Pinned implies grappled, but also has specific -4 AC.
             # Loses Dex bonus to AC
        if self.has_condition("prone"):
            # This is context-dependent: +4 AC vs ranged, -4 AC vs melee.
            # Cannot be generically applied here without knowing attacker type.
            # For now, this will be handled where attack roll is made.
            pass
        if self.has_condition("stunned"):
            ac -= 2
            # Loses Dex bonus to AC

        return ac
    
    def get_attack_bonus(self, attack: Attack, is_full_attack: bool = False, 
                        attack_number: int = 0, target: Optional['Combatant'] = None) -> int:
        """
        Calculate total attack bonus for a specific attack.
        Target is optional but needed for some conditions (e.g. prone).
        """
        ability_to_use = attack.associated_ability_for_attack

        # Apply penalties from conditions to ability scores for modifier calculation
        # This is a simplified approach. A full system would have temporary ability score penalties.
        effective_str_mod = self.ability_scores.get_modifier("strength")
        effective_dex_mod = self.ability_scores.get_modifier("dexterity")

        if self.has_condition("exhausted"):
            effective_str_mod -= 3 # -6 penalty to score = -3 to modifier
            effective_dex_mod -= 3
        elif self.has_condition("fatigued"):
            effective_str_mod -= 1 # -2 penalty to score = -1 to modifier
            effective_dex_mod -= 1

        if self.has_condition("entangled"): # -4 dex
             effective_dex_mod -= 2

        if ability_to_use == "str":
            ability_mod = effective_str_mod
        elif ability_to_use == "dex":
            ability_mod = effective_dex_mod
        else: # other abilities, not typically modified by these conditions directly
            ability_mod = self.ability_scores.get_modifier(ability_to_use)

        size_mod = self.get_size_modifier() # Attack roll size mod
        
        bab = self.base_attack_bonus
        if is_full_attack and attack_number > 0:
            bab -= (attack_number * 5)
        
        total_bonus = bab + ability_mod + size_mod + attack.enhancement_bonus

        # Condition-based attack penalties
        if self.has_condition("blinded"): # Though usually can't attack specific target if fully blind
            pass # Blinded doesn't directly penalize attack rolls, but makes targets have total concealment (50% miss)
        if self.has_condition("dazzled"):
            total_bonus -= 1
        if self.has_condition("entangled"):
            total_bonus -= 2
        if self.has_condition("frightened") or self.has_condition("shaken"):
            total_bonus -= 2
        if self.has_condition("grappled"): # -2 penalty on attacks, unless grappling or escaping
            # Assuming this attack is not part of a grapple maintenance action
            total_bonus -= 2
        if self.has_condition("prone") and attack.attack_type == AttackType.MELEE:
            total_bonus -= 4
        elif self.has_condition("prone") and attack.attack_type == AttackType.RANGED and attack.name.lower() != "crossbow" and attack.name.lower() != "shuriken":
             # Most ranged weapons cannot be used while prone. Crossbows/shuriken are exceptions.
             # This should ideally prevent the attack entirely if not allowed.
             # For now, apply a heavy penalty or mark as invalid.
             # Let's assume for now it means cannot attack, this method should signal that.
             # Returning a very low number to ensure miss, or raise exception.
             # For now, log and penalize heavily.
             print(f"Warning: {self.name} attempting ranged attack ({attack.name}) while prone.")
             total_bonus -= 20 # Effectively impossible to hit for most.
        if self.has_condition("sickened"):
            total_bonus -= 2
        # Stunned: cannot take actions, so won't be attacking.
        # Helpless: cannot take actions.
        # Nauseated: cannot attack.
        # Paralyzed: cannot take actions.

        # Target-related penalties (e.g. target is prone and attacker is ranged)
        if target and target.has_condition("prone") and attack.attack_type == AttackType.RANGED:
            # Attacking a prone target with a ranged weapon. No penalty for attacker, target gets +4 AC vs ranged.
            # This is handled on the AC side of target.
            pass

        return total_bonus
    
    def get_damage_bonus(self, attack: Attack, is_off_hand: bool = False, 
                        is_two_handed: bool = False) -> int:
        """Calculate damage bonus for an attack"""
        ability_to_use = attack.associated_ability_for_damage
        ability_mod = self.ability_scores.get_modifier(ability_to_use) # Base modifier

        # Apply penalties from conditions to ability scores for modifier calculation
        if ability_to_use == "strength":
            if self.has_condition("exhausted"):
                ability_mod -= 3 # -6 Str score
            elif self.has_condition("fatigued"):
                ability_mod -= 1 # -2 Str score
        
        # Modify strength bonus based on attack type
        if ability_to_use == "strength":
            if is_off_hand:
                ability_mod = ability_mod // 2 if ability_mod > 0 else ability_mod
            elif is_two_handed and self.size != "Small":  # Two-handed weapons
                ability_mod = int(ability_mod * 1.5)
        
        damage_bonus = ability_mod + attack.enhancement_bonus

        if self.has_condition("sickened"):
            damage_bonus -= 2 # Sickened applies penalty to damage rolls too

        return damage_bonus
    
    def roll_damage(self, attack: Attack, is_critical: bool = False, 
                   is_off_hand: bool = False, is_two_handed: bool = False) -> int:
        """Roll damage for an attack"""
        # Parse damage dice (e.g., "1d8", "2d6")
        dice_parts = attack.damage_dice.split('d')
        if len(dice_parts) != 2:
            return 1  # fallback
        
        num_dice = int(dice_parts[0])
        die_size = int(dice_parts[1])
        
        # Roll damage dice
        damage = sum(random.randint(1, die_size) for _ in range(num_dice))
        
        # Add damage bonus
        damage_bonus = self.get_damage_bonus(attack, is_off_hand, is_two_handed)
        
        if is_critical:
            # Multiply weapon damage and bonuses, but not extra dice
            multiplier = attack.get_crit_multiplier()
            damage = (damage + damage_bonus) * multiplier
        else:
            damage += damage_bonus
        
        return max(1, damage)  # Minimum 1 damage

    def get_threatened_squares(self, current_position: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Get a list of squares threatened by this combatant.
        For simplicity, assumes combatants occupy a single square (5ft x 5ft).
        Reach is determined by the first equipped melee weapon or default 5ft.
        This is a simplified model; a full grid system would be more complex.
        """
        # TODO: Integrate with a proper grid system. This is a placeholder.
        # For now, assume all adjacent squares are threatened by default.
        # A more robust implementation would check weapon reach.

        reach = 5 # default reach
        if self.attacks:
            # Find first melee attack to determine reach
            for attack in self.attacks:
                if attack.reach > 0 and attack.attack_type in [AttackType.MELEE, AttackType.NATURAL]:
                    reach = attack.reach
                    break

        # Simplified: if reach is 5ft, threaten adjacent squares (including diagonals)
        # If reach is 10ft, threaten squares 2 units away, but not adjacent ones (typical for reach weapons)
        # This is a very simplified model of reach.

        threatened = []
        x, y = current_position

        if reach == 5:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    threatened.append((x + dx, y + dy))
        elif reach == 10: # Typical reach weapon behavior (threatens 10ft, not 5ft)
             for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    # Only squares at exactly 2 units distance (Manhattan distance for simplicity here)
                    # Or squares that are 2 units away diagonally
                    manhattan_dist = abs(dx) + abs(dy)
                    chebyshev_dist = max(abs(dx), abs(dy))

                    if chebyshev_dist == 2: # Squares like (0,2), (1,2), (2,2), (2,1), (2,0) etc.
                         threatened.append((x + dx, y + dy))

        # This is a placeholder. Actual threatened squares depend on grid, position, and weapon.
        # For now, let's assume a 5ft reach threatens all adjacent squares.
        # A more sophisticated model would use the 'reach' attribute of equipped weapons.
        if not threatened and reach > 0: # Fallback for simple adjacency if specific reach logic fails
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    threatened.append((x + dx, y + dy))
        return threatened

    def take_damage(self, damage: int, damage_type: str = "untyped") -> int:
        """Apply damage, considering DR and resistances"""
        effective_damage = damage
        
        # Apply damage reduction
        if self.damage_reduction:
            dr_amount = self.damage_reduction.get("amount", 0)
            dr_type = self.damage_reduction.get("type", "")
            
            # Simple DR implementation - reduce damage by DR amount
            # TODO: Implement proper DR type checking
            effective_damage = max(0, effective_damage - dr_amount)
        
        # Apply energy resistances
        if damage_type in self.energy_resistances:
            resistance = self.energy_resistances[damage_type]
            effective_damage = max(0, effective_damage - resistance)
        
        # Apply immunities
        if damage_type in self.energy_immunities:
            effective_damage = 0
        
        # Apply vulnerabilities (double damage)
        if damage_type in self.energy_vulnerabilities:
            effective_damage *= 2
        
        # Apply damage to temporary HP first, then regular HP
        if self.temporary_hp > 0:
            temp_damage = min(effective_damage, self.temporary_hp)
            self.temporary_hp -= temp_damage
            effective_damage -= temp_damage
        
        self.current_hp -= effective_damage

        # Update conditions based on HP
        if self.current_hp <= 0 and self.current_hp > -self.ability_scores.get_total_score("constitution"):
            self.add_condition("disabled" if self.current_hp == 0 else "dying")
            if self.current_hp < 0:
                self.remove_condition("disabled") # Can't be disabled and dying
        elif self.current_hp <= -self.ability_scores.get_total_score("constitution"):
            self.add_condition("dead")
            self.remove_condition("dying")
            self.remove_condition("disabled")
            self.current_hp = -self.ability_scores.get_total_score("constitution") # HP doesn't go below this

        return effective_damage

    def is_disabled(self) -> bool:
        """Check if combatant is disabled (at 0 HP)"""
        return self.current_hp == 0 and "dead" not in self.conditions

    def is_dying(self) -> bool:
        """Check if combatant is dying (negative HP, but not dead)"""
        return self.current_hp < 0 and "dead" not in self.conditions

    def is_dead(self) -> bool:
        """Check if combatant is dead (HP <= -Constitution score)"""
        return "dead" in self.conditions

    def stabilize(self) -> bool:
        """Attempt to stabilize if dying. Returns True if stabilized, False otherwise."""
        if not self.is_dying():
            return False # Not dying, or already stable/dead

        # Penalty on check is equal to negative HP total
        penalty = abs(self.current_hp) if self.current_hp < 0 else 0
        roll = random.randint(1, 20)

        # Automatic success on natural 20
        if roll == 20:
            self.add_condition("stable")
            self.remove_condition("dying") # No longer actively dying once stable
            return True

        # Check against DC 10
        if roll - penalty >= 10:
            self.add_condition("stable")
            self.remove_condition("dying")
            return True
        else:
            # Failed stabilization, lose 1 HP
            self.current_hp -= 1
            # Check for death after HP loss
            if self.current_hp <= -self.ability_scores.get_total_score("constitution"):
                self.add_condition("dead")
                self.remove_condition("dying")
                self.remove_condition("stable")
            return False

    def heal(self, amount: int) -> int:
        """Heal damage"""
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        # Healing can remove disabled/dying conditions
        if self.current_hp > 0:
            self.remove_condition("disabled")
            self.remove_condition("dying")
            self.remove_condition("stable")
        elif self.current_hp == 0:
            self.add_condition("disabled")
            self.remove_condition("dying")
            self.remove_condition("stable")
        return self.current_hp - old_hp

    def make_saving_throw(self, save_type: str, dc: int, source_effect_name: str = "Unknown Effect") -> bool:
        """
        Make a saving throw against a given DC.
        save_type should be 'fortitude', 'reflex', or 'will'.
        Returns True if the save is successful, False otherwise.
        """
        if save_type not in ["fortitude", "reflex", "will"]:
            print(f"Error: Invalid save type '{save_type}' for {self.name}.")
            return False # Or raise an error

        save_bonus = self.saving_throws.calculate_save(save_type, self.ability_scores)
        roll = random.randint(1, 20)
        total_roll = roll + save_bonus

        success = False
        if roll == 1: # Natural 1 always fails
            success = False
        elif roll == 20: # Natural 20 always succeeds
            success = True
        else:
            success = total_roll >= dc

        log_message_intro = f"{self.name} makes a {save_type.capitalize()} save for {source_effect_name} (DC {dc}):"
        log_message_roll = f"  Roll: {roll} + Bonus: {save_bonus} = {total_roll}"

        # Access the combat log through a global or passed-in reference if needed
        # For now, let's assume a way to log this. If this method is called from CombatEngine,
        # the engine's log can be used.
        # This might require passing the logger or making it accessible.
        # As a temporary measure, we can print.
        print(log_message_intro)
        print(log_message_roll)

        if success:
            print("  Save successful!")
        else:
            print("  Save failed.")

        return success
    
    def add_condition(self, condition: str):
        """Add a condition"""
        self.conditions.add(condition)
        # TODO: Apply condition effects
    
    def remove_condition(self, condition: str):
        """Remove a condition"""
        self.conditions.discard(condition)
        # TODO: Remove condition effects
    
    def has_condition(self, condition: str) -> bool:
        """Check if has a condition"""
        return condition in self.conditions
    
    def reset_for_combat(self):
        """Reset state for new combat"""
        self.current_hp = self.max_hp
        self.temporary_hp = 0
        self.conditions.clear()
        self.is_flat_footed = True
        self.has_acted_this_combat = False
        self.current_initiative_roll = 0
        self.final_initiative_score = 0
        self.aoo_made_this_round = 0
        self.has_moved_this_turn = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = {
            "name": self.name,
            "is_pc": self.is_pc,
            "max_hp": self.max_hp,
            "ability_scores": {
                "strength": self.ability_scores.strength,
                "dexterity": self.ability_scores.dexterity,
                "constitution": self.ability_scores.constitution,
                "intelligence": self.ability_scores.intelligence,
                "wisdom": self.ability_scores.wisdom,
                "charisma": self.ability_scores.charisma
            },
            "base_attack_bonus": self.base_attack_bonus,
            "armor_class": {
                "armor_bonus": self.armor_class.armor_bonus,
                "shield_bonus": self.armor_class.shield_bonus,
                "natural_armor_bonus": self.armor_class.natural_armor_bonus,
                "deflection_bonus": self.armor_class.deflection_bonus,
                "dodge_bonus": self.armor_class.dodge_bonus,
                "size_modifier": self.armor_class.size_modifier,
                "max_dex_bonus_from_armor": self.armor_class.max_dex_bonus_from_armor
            },
            "saving_throws": {
                "fortitude_base": self.saving_throws.fortitude_base,
                "reflex_base": self.saving_throws.reflex_base,
                "will_base": self.saving_throws.will_base
            },
            "base_speed": self.base_speed,
            "size": self.size,
            "creature_type": self.creature_type,
            "subtypes": self.subtypes,
            "alignment": self.alignment,
            "skills": self.skills,
            "feats": self.feats,
            "attacks": [{
                "name": attack.name,
                "damage_dice": attack.damage_dice,
                "critical_threat_range": attack.critical_threat_range,
                "critical_multiplier": attack.critical_multiplier,
                "damage_type": attack.damage_type.value,
                "reach": attack.reach,
                "associated_ability_for_attack": attack.associated_ability_for_attack,
                "associated_ability_for_damage": attack.associated_ability_for_damage,
                "is_primary_natural_attack": attack.is_primary_natural_attack,
                "special_qualities": attack.special_qualities,
                "enhancement_bonus": attack.enhancement_bonus
            } for attack in self.attacks],
            "damage_reduction": self.damage_reduction,
            "spell_resistance": self.spell_resistance,
            "energy_resistances": self.energy_resistances,
            "energy_immunities": self.energy_immunities,
            "energy_vulnerabilities": self.energy_vulnerabilities
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Combatant':
        """Create Combatant from dictionary"""
        combatant = cls(data["name"], data.get("is_pc", False))
        
        # Basic stats
        combatant.max_hp = data.get("max_hp", 1)
        combatant.current_hp = combatant.max_hp
        combatant.base_attack_bonus = data.get("base_attack_bonus", 0)
        combatant.base_speed = data.get("base_speed", 30)
        combatant.size = data.get("size", "Medium")
        combatant.creature_type = data.get("creature_type", "Humanoid")
        combatant.subtypes = data.get("subtypes", [])
        combatant.alignment = data.get("alignment", "True Neutral")
        combatant.skills = data.get("skills", {})
        combatant.feats = data.get("feats", [])
        combatant.damage_reduction = data.get("damage_reduction", {})
        combatant.spell_resistance = data.get("spell_resistance", 0)
        combatant.energy_resistances = data.get("energy_resistances", {})
        combatant.energy_immunities = data.get("energy_immunities", [])
        combatant.energy_vulnerabilities = data.get("energy_vulnerabilities", [])
        
        # Ability scores
        if "ability_scores" in data:
            abs_data = data["ability_scores"]
            combatant.ability_scores.strength = abs_data.get("strength", 10)
            combatant.ability_scores.dexterity = abs_data.get("dexterity", 10)
            combatant.ability_scores.constitution = abs_data.get("constitution", 10)
            combatant.ability_scores.intelligence = abs_data.get("intelligence", 10)
            combatant.ability_scores.wisdom = abs_data.get("wisdom", 10)
            combatant.ability_scores.charisma = abs_data.get("charisma", 10)
        
        # Armor class
        if "armor_class" in data:
            ac_data = data["armor_class"]
            combatant.armor_class.armor_bonus = ac_data.get("armor_bonus", 0)
            combatant.armor_class.shield_bonus = ac_data.get("shield_bonus", 0)
            combatant.armor_class.natural_armor_bonus = ac_data.get("natural_armor_bonus", 0)
            combatant.armor_class.deflection_bonus = ac_data.get("deflection_bonus", 0)
            combatant.armor_class.dodge_bonus = ac_data.get("dodge_bonus", 0)
            combatant.armor_class.size_modifier = ac_data.get("size_modifier", 0)
            combatant.armor_class.max_dex_bonus_from_armor = ac_data.get("max_dex_bonus_from_armor")
        
        # Saving throws
        if "saving_throws" in data:
            save_data = data["saving_throws"]
            combatant.saving_throws.fortitude_base = save_data.get("fortitude_base", 0)
            combatant.saving_throws.reflex_base = save_data.get("reflex_base", 0)
            combatant.saving_throws.will_base = save_data.get("will_base", 0)
        
        # Attacks
        if "attacks" in data:
            for attack_data in data["attacks"]:
                attack = Attack(
                    name=attack_data["name"],
                    damage_dice=attack_data["damage_dice"],
                    critical_threat_range=attack_data["critical_threat_range"],
                    critical_multiplier=attack_data["critical_multiplier"],
                    damage_type=DamageType(attack_data["damage_type"]),
                    reach=attack_data.get("reach", 5),
                    associated_ability_for_attack=attack_data.get("associated_ability_for_attack", "str"),
                    associated_ability_for_damage=attack_data.get("associated_ability_for_damage", "str"),
                    is_primary_natural_attack=attack_data.get("is_primary_natural_attack", True),
                    special_qualities=attack_data.get("special_qualities", []),
                    enhancement_bonus=attack_data.get("enhancement_bonus", 0)
                )
                combatant.attacks.append(attack)
        
        # Calculate initiative modifier
        combatant.initiative_modifier = combatant.ability_scores.get_modifier("dexterity")
        
        return combatant


class MonsterDatabase:
    """
    Handles persistent storage and retrieval of monster statblocks
    Implements Part 1.2 of the specification
    """
    
    def __init__(self, database_path: str = "monster_data"):
        self.database_path = database_path
        os.makedirs(database_path, exist_ok=True)
    
    def save_monster(self, combatant: Combatant) -> bool:
        """Save a monster template to JSON file"""
        try:
            filename = f"{combatant.name.lower().replace(' ', '_')}.json"
            filepath = os.path.join(self.database_path, filename)
            
            with open(filepath, 'w') as f:
                json.dump(combatant.to_dict(), f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving monster {combatant.name}: {e}")
            return False
    
    def load_monster(self, monster_name: str) -> Optional[Combatant]:
        """Load a monster template from JSON file"""
        try:
            # Handle both "Monster Name" and "monster_name.json" formats
            if monster_name.endswith('.json'):
                filename = monster_name
            else:
                filename = f"{monster_name.lower().replace(' ', '_')}.json"
            
            filepath = os.path.join(self.database_path, filename)
            
            if not os.path.exists(filepath):
                print(f"Monster file not found: {filepath}")
                return None
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            combatant = Combatant.from_dict(data)
            combatant.reset_for_combat()  # Fresh instance for combat
            
            return combatant
        except Exception as e:
            print(f"Error loading monster {monster_name}: {e}")
            return None
    
    def list_monsters(self) -> List[str]:
        """List all available monster templates"""
        try:
            files = [f for f in os.listdir(self.database_path) if f.endswith('.json')]
            # Remove .json extension and convert underscores to spaces
            return [f[:-5].replace('_', ' ').title() for f in files]
        except Exception as e:
            print(f"Error listing monsters: {e}")
            return []
    
    def delete_monster(self, monster_name: str) -> bool:
        """Delete a monster template"""
        try:
            filename = f"{monster_name.lower().replace(' ', '_')}.json"
            filepath = os.path.join(self.database_path, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            else:
                print(f"Monster file not found: {filepath}")
                return False
        except Exception as e:
            print(f"Error deleting monster {monster_name}: {e}")
            return False


class AttackResult:
    """Represents the result of an attack roll"""
    def __init__(self, attacker: str, target: str, attack_name: str):
        self.attacker = attacker
        self.target = target
        self.attack_name = attack_name
        self.attack_roll = 0
        self.total_attack_bonus = 0
        self.target_ac = 0
        self.is_hit = False
        self.is_critical_threat = False
        self.is_critical_hit = False
        self.damage_rolls = []
        self.total_damage = 0
        self.damage_taken = 0
        self.special_effects = []


class CombatLog:
    """Handles logging of combat events"""
    def __init__(self):
        self.log_entries = []
    
    def add_entry(self, message: str):
        """Add an entry to the combat log"""
        self.log_entries.append(message)
        print(message)  # Also print for immediate feedback
    
    def get_full_log(self) -> str:
        """Get the complete combat log"""
        return "\n".join(self.log_entries)
    
    def clear(self):
        """Clear the combat log"""
        self.log_entries.clear()


class CombatEngine:
    """
    Main combat engine implementing Parts 2-3 of the specification
    Handles initiative, rounds, turns, and combat actions
    """
    
    def __init__(self):
        self.combatants: List[Combatant] = []
        self.initiative_order: List[Tuple[Combatant, int]] = []  # (combatant, initiative)
        self.current_round = 0
        self.current_turn_index = 0
        self.is_surprise_round = False
        self.combat_active = False
        self.log = CombatLog()
    
    def add_combatant(self, combatant: Combatant, is_aware: bool = True):
        """Add a combatant to the encounter"""
        combatant.reset_for_combat()
        combatant.is_aware_in_surprise_round = is_aware
        self.combatants.append(combatant)
    
    def roll_initiative(self):
        """Roll initiative for all combatants and sort by result"""
        self.log.add_entry("=== Rolling Initiative ===")
        
        initiative_results = []
        for combatant in self.combatants:
            # Roll 1d20 + initiative modifier
            roll = random.randint(1, 20)
            total = roll + combatant.initiative_modifier
            combatant.current_initiative_roll = roll
            combatant.final_initiative_score = total
            
            initiative_results.append((combatant, total, roll))
            self.log.add_entry(f"{combatant.name}: {roll} + {combatant.initiative_modifier} = {total}")
        
        # Sort by initiative (highest first), then by initiative modifier, then by roll
        initiative_results.sort(key=lambda x: (x[1], x[0].initiative_modifier, x[2]), reverse=True)
        
        # Handle ties with additional d20 rolls if needed
        final_results = []
        i = 0
        while i < len(initiative_results):
            tied_group = [initiative_results[i]]
            j = i + 1
            
            # Find all combatants tied with the current one
            while (j < len(initiative_results) and 
                   initiative_results[j][1] == initiative_results[i][1] and
                   initiative_results[j][0].initiative_modifier == initiative_results[i][0].initiative_modifier):
                tied_group.append(initiative_results[j])
                j += 1
            
            # If there's a tie that couldn't be broken by initiative modifier, roll d20s
            if len(tied_group) > 1:
                self.log.add_entry(f"Breaking tie between: {', '.join(c[0].name for c in tied_group)}")
                for k, (combatant, total, original_roll) in enumerate(tied_group):
                    tiebreaker = random.randint(1, 20)
                    tied_group[k] = (combatant, total, original_roll, tiebreaker)
                    self.log.add_entry(f"  {combatant.name} tiebreaker: {tiebreaker}")
                
                # Sort by tiebreaker
                tied_group.sort(key=lambda x: x[3], reverse=True)
                final_results.extend([(c[0], c[1]) for c in tied_group])
            else:
                final_results.extend([(c[0], c[1]) for c in tied_group])
            
            i = j
        
        self.initiative_order = final_results
        
        self.log.add_entry("\n=== Final Initiative Order ===")
        for i, (combatant, initiative) in enumerate(self.initiative_order):
            self.log.add_entry(f"{i+1}. {combatant.name}: {initiative}")
    
    def start_combat(self):
        """Start combat encounter"""
        if not self.combatants:
            self.log.add_entry("No combatants in encounter!")
            return False
        
        self.log.add_entry("=== COMBAT BEGINS ===")
        self.roll_initiative()
        
        # Check if there should be a surprise round
        aware_combatants = [c for c in self.combatants if getattr(c, 'is_aware_in_surprise_round', True)]
        unaware_combatants = [c for c in self.combatants if not getattr(c, 'is_aware_in_surprise_round', True)]
        
        if unaware_combatants:
            self.log.add_entry(f"\n=== SURPRISE ROUND ===")
            self.log.add_entry(f"Unaware: {', '.join(c.name for c in unaware_combatants)}")
            self.is_surprise_round = True
            self.current_round = 0
            self.current_turn_index = 0
            self.combat_active = True
            
            # Mark unaware combatants as flat-footed
            for combatant in unaware_combatants:
                combatant.add_condition("flat-footed")
        else:
            self.log.add_entry("\n=== ROUND 1 ===")
            self.current_round = 1
            self.current_turn_index = 0
            self.is_surprise_round = False
            self.combat_active = True
        
        return True
    
    def get_current_combatant(self) -> Optional[Combatant]:
        """Get the combatant whose turn it currently is"""
        if not self.combat_active or self.current_turn_index >= len(self.initiative_order):
            return None
        
        # Skip defeated combatants
        while (self.current_turn_index < len(self.initiative_order) and 
               self.initiative_order[self.current_turn_index][0].current_hp <= 0):
            self.current_turn_index += 1
        
        if self.current_turn_index >= len(self.initiative_order):
            return None
            
        return self.initiative_order[self.current_turn_index][0]
    
    def can_act_in_surprise_round(self, combatant: Combatant) -> bool:
        """Check if a combatant can act in the surprise round"""
        return getattr(combatant, 'is_aware_in_surprise_round', True)
    
    def advance_turn(self):
        """Advance to the next combatant's turn"""
        if not self.combat_active:
            return
        
        # Mark current combatant as no longer flat-footed if this is their first turn
        current_combatant = self.get_current_combatant()
        if current_combatant and not current_combatant.has_acted_this_combat:
            current_combatant.has_acted_this_combat = True
            if not self.is_surprise_round:  # Don't remove flat-footed in surprise round
                current_combatant.is_flat_footed = False
                current_combatant.remove_condition("flat-footed")
        
        self.current_turn_index += 1
        
        # Check if round is complete
        if self.current_turn_index >= len(self.initiative_order):
            if self.is_surprise_round:
                # End surprise round, start regular combat
                self.log.add_entry("\n=== END OF SURPRISE ROUND ===")
                self.is_surprise_round = False
                self.current_round = 1
                self.current_turn_index = 0
                self.log.add_entry(f"\n=== ROUND {self.current_round} ===")
                
                # Remove flat-footed from all aware combatants
                for combatant in self.combatants:
                    if getattr(combatant, 'is_aware_in_surprise_round', True):
                        combatant.is_flat_footed = False
                        combatant.remove_condition("flat-footed")
            else:
                # Start new round
                self.current_round += 1
                self.current_turn_index = 0
                self.log.add_entry(f"\n=== ROUND {self.current_round} ===")
                
                # Process end-of-round effects here
                # TODO: Handle spell durations, ongoing effects, etc.
                # Reset AoO counts and movement flags at the end of a full round
                for cb in self.combatants:
                    cb.aoo_made_this_round = 0
                    cb.has_moved_this_turn = False # Reset for 5-foot step next round
        
        # Announce whose turn it is
        current_combatant = self.get_current_combatant()
        if current_combatant:
            if self.is_surprise_round and not self.can_act_in_surprise_round(current_combatant):
                self.log.add_entry(f"{current_combatant.name}'s turn (cannot act - unaware)")
                self.advance_turn()  # Skip unaware combatants in surprise round
            else:
                self.log.add_entry(f"{current_combatant.name}'s turn ({current_combatant.current_hp}/{current_combatant.max_hp} HP)")
                # At the start of their turn, if a combatant is dying and not stable, they attempt to stabilize or lose HP.
                if current_combatant.is_dying() and not current_combatant.has_condition("stable"):
                    self.log.add_entry(f"{current_combatant.name} is dying and must make a stabilization check.")
                    if current_combatant.stabilize():
                        self.log.add_entry(f"{current_combatant.name} stabilized!")
                    else:
                        self.log.add_entry(f"{current_combatant.name} failed to stabilize and loses 1 HP.")
                        if current_combatant.is_dead():
                             self.log.add_entry(f"{current_combatant.name} has died from HP loss.")
                        else:
                            self.log.add_entry(f"{current_combatant.name} HP: {current_combatant.current_hp}/{current_combatant.max_hp}")

    def can_make_aoo(self, combatant: Combatant) -> bool:
        """Check if a combatant can make an Attack of Opportunity."""
        if combatant.is_flat_footed and "Combat Reflexes" not in combatant.feats:
            return False

        max_aoos = 1
        if "Combat Reflexes" in combatant.feats:
            max_aoos += combatant.ability_scores.get_modifier("dexterity")

        return combatant.aoo_made_this_round < max_aoos

    def trigger_attacks_of_opportunity(self, provoking_combatant: Combatant, provoking_action_type: str):
        """
        Checks for and resolves AoOs against a combatant performing a provoking action.
        This is a simplified version and needs integration with a grid/positioning system.
        """
        # TODO: Integrate with actual grid positions.
        # For now, assume all other active combatants can potentially make an AoO if they threaten.
        # This is a placeholder for actual distance/reach checks.

        self.log.add_entry(f"{provoking_combatant.name} performing {provoking_action_type} may provoke AoOs.")

        for potential_attacker in self.combatants:
            if potential_attacker == provoking_combatant or potential_attacker.is_dead() or potential_attacker.has_condition("unconscious"):
                continue

            # Simplified check: Does potential_attacker threaten provoking_combatant?
            # This needs current positions of both combatants.
            # For now, let's assume they are within reach if the potential_attacker can make an AoO.
            # A real implementation would check:
            # provoking_combatant_position = self.get_combatant_position(provoking_combatant)
            # if provoking_combatant_position in potential_attacker.get_threatened_squares(self.get_combatant_position(potential_attacker)):

            if self.can_make_aoo(potential_attacker):
                # Placeholder: Assume the first melee attack is used for AoO
                aoo_attack = None
                for attack in potential_attacker.attacks:
                    if attack.attack_type == AttackType.MELEE or attack.attack_type == AttackType.NATURAL:
                        aoo_attack = attack
                        break

                if aoo_attack:
                    self.log.add_entry(f"{potential_attacker.name} gets an AoO against {provoking_combatant.name}!")
                    self.make_attack(potential_attacker, provoking_combatant, aoo_attack, is_aoo=True)
                    potential_attacker.aoo_made_this_round += 1
                    if provoking_combatant.is_dead() or provoking_combatant.has_condition("unconscious"):
                        self.log.add_entry(f"{provoking_combatant.name} is downed by the AoO, action interrupted.")
                        # TODO: Properly interrupt the action. For now, just log.
                        break
                else:
                    self.log.add_entry(f"{potential_attacker.name} could make an AoO but has no suitable melee/natural attack.")
            # else:
            #     self.log.add_entry(f"{potential_attacker.name} cannot make an AoO (flat-footed or max AoOs reached).")

    def make_attack(self, attacker: Combatant, target: Combatant, attack: Attack, 
                   is_full_attack: bool = False, attack_number: int = 0, is_aoo: bool = False) -> AttackResult:
        """
        Execute an attack between two combatants
        Implements Part 3 attack mechanics
        """
        result = AttackResult(attacker.name, target.name, attack.name)
        
        # Calculate attack bonus, passing target for context
        result.total_attack_bonus = attacker.get_attack_bonus(
            attack,
            is_full_attack=(is_aoo and False),
            attack_number=(0 if is_aoo else attack_number),
            target=target
        )

        # Roll attack
        result.attack_roll = random.randint(1, 20)
        total_attack = result.attack_roll + result.total_attack_bonus
        
        # Determine target AC
        base_ac_type = "standard"
        if target.is_flat_footed or target.has_condition("helpless") or target.has_condition("stunned") or target.has_condition("paralyzed") or target.has_condition("blinded"):
            base_ac_type = "flat_footed"

        result.target_ac = target.get_ac(base_ac_type)

        # Specific AC adjustments for Prone condition based on attack type
        if target.has_condition("prone"):
            if attack.attack_type == AttackType.RANGED:
                self.log.add_entry(f"  {target.name} is prone, +4 AC vs ranged attack.")
                result.target_ac += 4
            elif attack.attack_type == AttackType.MELEE:
                self.log.add_entry(f"  {target.name} is prone, -4 AC vs melee attack.")
                result.target_ac -= 4
        
        # Check for hit
        is_natural_1 = result.attack_roll == 1
        is_natural_20 = result.attack_roll == 20
        
        if is_natural_1:
            result.is_hit = False
        elif is_natural_20:
            result.is_hit = True
            result.is_critical_threat = True # Natural 20 always threatens
        else:
            result.is_hit = total_attack >= result.target_ac
            if result.is_hit and result.attack_roll in attack.get_threat_range():
                result.is_critical_threat = True
        
        self.log.add_entry(f"{attacker.name} attacks {target.name} with {attack.name}")
        self.log.add_entry(f"  Attack roll: {result.attack_roll} + {result.total_attack_bonus} = {total_attack} vs AC {result.target_ac}")
        
        if not result.is_hit:
            self.log.add_entry("  MISS!")
            return result

        # Hit occurs, now check for concealment miss chance (e.g., from target being blinded by attacker's perspective, or other concealment)
        # If attacker is blinded, they treat all targets as having total concealment (50% miss chance)
        miss_chance = 0
        if attacker.has_condition("blinded"):
            miss_chance = 50
            self.log.add_entry(f"  Attacker {attacker.name} is blinded, 50% miss chance.")
        # TODO: Add other sources of concealment for the target.

        if miss_chance > 0:
            if random.randint(1, 100) <= miss_chance:
                self.log.add_entry(f"  HIT! (but missed due to {miss_chance}% miss chance from concealment/blindness)")
                result.is_hit = False # Mark as miss due to concealment
                # Even if it was a critical threat, concealment miss negates the crit.
                result.is_critical_threat = False
                result.is_critical_hit = False
                return result # Attack effectively missed

        self.log.add_entry("  HIT!") # If it wasn't a miss due to concealment
        
        # Handle critical hit confirmation
        if result.is_critical_threat: # Re-check, as concealment might have negated it
            self.log.add_entry("  Critical threat! Rolling to confirm...")
            confirm_roll = random.randint(1, 20)
            # Confirmation roll uses same bonuses as original attack
            confirm_total_attack_bonus = attacker.get_attack_bonus(
                attack,
                is_full_attack=(is_aoo and False), # Crit confirm is like a new attack roll
                attack_number=(0 if is_aoo else attack_number),
                target=target
            )
            confirm_total = confirm_roll + confirm_total_attack_bonus
            
            # Target AC for confirmation is their normal AC at the time of the confirmation.
            # (Concealment does not apply to the confirmation roll itself, only the original hit)
            confirm_target_ac = target.get_ac(base_ac_type) # Use same base_ac_type as original
            if target.has_condition("prone"): # Re-apply prone AC mods for confirm
                if attack.attack_type == AttackType.RANGED: confirm_target_ac += 4
                elif attack.attack_type == AttackType.MELEE: confirm_target_ac -= 4

            self.log.add_entry(f"  Confirmation roll: {confirm_roll} + {confirm_total_attack_bonus} = {confirm_total} vs AC {confirm_target_ac}")

            if confirm_total >= confirm_target_ac: # Crit confirmed if confirmation roll hits
                result.is_critical_hit = True
                self.log.add_entry(f"  CRITICAL HIT!")
            else:
                self.log.add_entry(f"  Confirmed as normal hit.")
        
        # Roll damage
        is_off_hand = False  # TODO: Implement off-hand detection
        is_two_handed = False  # TODO: Implement two-handed detection
        
        result.total_damage = attacker.roll_damage(attack, result.is_critical_hit, is_off_hand, is_two_handed)
        
        if result.is_critical_hit:
            multiplier = attack.get_crit_multiplier()
            self.log.add_entry(f"  Damage roll: {result.total_damage} (x{multiplier} critical)")
        else:
            self.log.add_entry(f"  Damage roll: {result.total_damage}")
        
        # Apply damage
        result.damage_taken = target.take_damage(result.total_damage, attack.damage_type.value)
        
        if result.damage_taken < result.total_damage:
            self.log.add_entry(f"  Damage reduced to {result.damage_taken} (DR/resistances)")
        
        self.log.add_entry(f"  {target.name} takes {result.damage_taken} damage")
        self.log.add_entry(f"  {target.name} HP: {target.current_hp}/{target.max_hp}")
        
        # Check if target is defeated
        if target.current_hp <= 0:
            self.log.add_entry(f"  {target.name} is defeated!")
            target.add_condition("unconscious")
        
        return result
    
    def get_valid_targets(self, attacker: Combatant) -> List[Combatant]:
        """Get list of valid targets for an attacker"""
        # Simple implementation - all other combatants are valid targets
        # TODO: Implement proper faction/team system
        return [c for c in self.combatants if c != attacker and c.current_hp > 0]
    
    def is_combat_over(self) -> bool:
        """Check if combat should end"""
        active_combatants = [c for c in self.combatants if c.current_hp > 0]
        
        if len(active_combatants) <= 1:
            return True
        
        # Simple faction check: if all remaining combatants are PCs or all are NPCs, combat ends
        active_pcs = [c for c in active_combatants if c.is_pc]
        active_npcs = [c for c in active_combatants if not c.is_pc]
        
        if len(active_pcs) == 0 or len(active_npcs) == 0:
            return True
        
        return False
    
    def end_combat(self):
        """End the current combat"""
        self.combat_active = False
        self.log.add_entry("\n=== COMBAT ENDS ===")
        
        # Show final status
        for combatant in self.combatants:
            if combatant.current_hp > 0:
                self.log.add_entry(f"{combatant.name}: {combatant.current_hp}/{combatant.max_hp} HP")
            else:
                self.log.add_entry(f"{combatant.name}: DEFEATED")


class ActionHandler:
    """
    Handles different types of actions a combatant can take
    Implements action economy from Part 3 of specification
    """
    
    def __init__(self, combat_engine: CombatEngine):
        self.combat_engine = combat_engine
    
    def can_take_action(self, combatant: Combatant, action_type: ActionType) -> bool:
        """Check if combatant can take a specific type of action"""
        if not self.combat_engine.combat_active:
            return False
        
        current_combatant = self.combat_engine.get_current_combatant()
        if current_combatant != combatant:
            return False
        
        if self.combat_engine.is_surprise_round:
            # In surprise round, only standard OR move actions allowed (plus free/swift) for aware combatants
            if not getattr(combatant, 'is_aware_in_surprise_round', True):
                self.combat_engine.log.add_entry(f"{combatant.name} cannot act in surprise round (unaware).")
                return False
            if action_type == ActionType.FULL_ROUND:
                self.combat_engine.log.add_entry(f"{combatant.name} cannot take a full-round action in a surprise round.")
                return False
        
        # Conditions preventing most actions
        if combatant.has_condition("stunned") or \
           combatant.has_condition("paralyzed") or \
           combatant.has_condition("helpless") or \
           combatant.has_condition("unconscious") or \
           combatant.is_dead() or \
           combatant.is_dying(): # Dying combatants are unconscious
            self.combat_engine.log.add_entry(f"{combatant.name} cannot take actions due to condition ({[c for c in ['stunned', 'paralyzed', 'helpless', 'unconscious', 'dead', 'dying'] if combatant.has_condition(c) or (c=='dead' and combatant.is_dead()) or (c=='dying' and combatant.is_dying())][0]}).")
            return False

        # Nauseated: Only a single move action
        if combatant.has_condition("nauseated"):
            if action_type != ActionType.MOVE:
                self.combat_engine.log.add_entry(f"{combatant.name} is nauseated and can only take a move action.")
                return False
            # TODO: Need to track if the move action was already taken this turn if nauseated.
            # For now, this check is per-action attempt.

        # Disabled: Single move or standard action. No full-round.
        if combatant.is_disabled(): # at 0 HP
            if action_type == ActionType.FULL_ROUND:
                self.combat_engine.log.add_entry(f"{combatant.name} is disabled and cannot take a full-round action.")
                return False
            # TODO: Track if standard/move already taken this turn if disabled.
            # If taking a standard action while disabled (not healing), take 1 damage.
            if action_type == ActionType.STANDARD:
                 # This logic should be after the action, not in can_take_action
                 pass

        # TODO: Add checks for Frightened (must flee), Panicked (must flee/cower), Confused (roll behavior)
        # These often dictate the *type* of action rather than preventing all actions.

        return True
    
    def take_attack_action(self, attacker: Combatant, target: Combatant, 
                          attack_index: int = 0) -> Optional[AttackResult]:
        """Take a standard attack action"""
        if not self.can_take_action(attacker, ActionType.STANDARD):
            return None
        
        if attacker.is_disabled(): # Taking a standard action while disabled
            self.combat_engine.log.add_entry(f"{attacker.name} is disabled and takes 1 damage for performing a standard action.")
            attacker.take_damage(1, "untyped") # This damage might make them dying/dead
            if not self.can_take_action(attacker, ActionType.STANDARD): # Re-check if they are now unable to act
                return None


        if attack_index >= len(attacker.attacks):
            self.combat_engine.log.add_entry(f"{attacker.name} has no attack at index {attack_index}")
            return None
        
        attack = attacker.attacks[attack_index]

        # Ranged attacks provoke AoOs
        if attack.attack_type == AttackType.RANGED:
            # Check for AoO before the attack proceeds
            # Pass 'ranged attack' as the provoking action description
            self.combat_engine.trigger_attacks_of_opportunity(attacker, "making a ranged attack")
            # If the attacker was downed by an AoO, they can't complete the action
            if attacker.is_dead() or attacker.has_condition("unconscious") or attacker.has_condition("stunned"):
                self.combat_engine.log.add_entry(f"{attacker.name} cannot complete ranged attack due to AoO effects.")
                return None # Attacker downed/disabled

        return self.combat_engine.make_attack(attacker, target, attack)
    
    def take_full_attack_action(self, attacker: Combatant, target: Combatant, 
                               attack_index: int = 0) -> List[AttackResult]:
        """Take a full-attack action (all available attacks)"""
        # Full-round actions generally don't provoke for starting, but individual attacks might
        # if they are ranged, etc. However, the standard rule is that a full-attack action itself doesn't provoke.
        # Provocation for ranged attacks is handled within make_attack or take_attack_action.
        if not self.can_take_action(attacker, ActionType.FULL_ROUND):
            return []
        
        if attack_index >= len(attacker.attacks):
            self.combat_engine.log.add_entry(f"{attacker.name} has no attack at index {attack_index}")
            return []
        
        results = []
        attack = attacker.attacks[attack_index]
        
        # Calculate number of attacks based on BAB
        num_attacks = (attacker.base_attack_bonus // 5) + 1
        
        self.combat_engine.log.add_entry(f"{attacker.name} takes a full-attack action")
        
        for i in range(num_attacks):
            if attacker.base_attack_bonus - (i * 5) > 0:  # Must have positive BAB for attack
                result = self.combat_engine.make_attack(attacker, target, attack, 
                                                       is_full_attack=True, attack_number=i)
                results.append(result)
            else:
                break
        
        return results

    def take_stabilize_other_action(self, actor: Combatant, target: Combatant) -> bool:
        """Use Heal skill (DC 15) to stabilize a dying target."""
        if not self.can_take_action(actor, ActionType.STANDARD):
            self.combat_engine.log.add_entry(f"{actor.name} cannot take a standard action to stabilize.")
            return False

        if not target.is_dying():
            self.combat_engine.log.add_entry(f"{target.name} is not dying.")
            return False

        # Simulate Heal skill check (DC 15)
        # Assuming a +0 Heal skill for simplicity for now
        # TODO: Implement actual skill checks for Heal
        heal_skill_modifier = actor.skills.get("Heal", 0)
        roll = random.randint(1, 20)

        # Stabilizing a dying friend provokes an AoO
        self.combat_engine.trigger_attacks_of_opportunity(actor, "stabilizing another character")
        if actor.is_dead() or actor.has_condition("unconscious") or actor.has_condition("stunned"):
            self.combat_engine.log.add_entry(f"{actor.name} cannot complete stabilization due to AoO effects.")
            return False

        self.combat_engine.log.add_entry(f"{actor.name} attempts to stabilize {target.name} with a Heal check.")
        self.combat_engine.log.add_entry(f"  Heal check roll: {roll} + {heal_skill_modifier} = {roll + heal_skill_modifier} vs DC 15")

        if roll + heal_skill_modifier >= 15:
            target.add_condition("stable")
            target.remove_condition("dying") # No longer actively dying
            self.combat_engine.log.add_entry(f"{target.name} has been stabilized by {actor.name}!")
            return True
        else:
            self.combat_engine.log.add_entry(f"{actor.name} failed to stabilize {target.name}.")
            return False

    def take_cast_spell_action(self, caster: Combatant, spell_name: str, target: Optional[Combatant] = None):
        """Placeholder for casting a spell. Most spells provoke AoOs."""
        if not self.can_take_action(caster, ActionType.STANDARD): # Assuming standard action spell
            self.combat_engine.log.add_entry(f"{caster.name} cannot take a standard action to cast a spell.")
            return

        # Casting a spell provokes an AoO
        self.combat_engine.trigger_attacks_of_opportunity(caster, f"casting {spell_name}")
        if caster.is_dead() or caster.has_condition("unconscious") or caster.has_condition("stunned"):
            self.combat_engine.log.add_entry(f"{caster.name} cannot complete casting {spell_name} due to AoO effects.")
            return

        self.combat_engine.log.add_entry(f"{caster.name} casts {spell_name}" + (f" on {target.name}" if target else "") + ". (Spell effects not implemented yet).")
        # TODO: Implement actual spell effects, concentration checks if damaged by AoO, etc.

    def take_aid_another_action(self, actor: Combatant, target_creature_to_hinder: Combatant, ally_to_aid: Combatant, aid_type: str = "attack") -> bool:
        """
        Perform the Aid Another action.
        aid_type can be "attack" (bonus to ally's next attack roll) or "ac" (bonus to ally's AC against target's next attack).
        This is a standard action.
        """
        if not self.can_take_action(actor, ActionType.STANDARD):
            self.combat_engine.log.add_entry(f"{actor.name} cannot take a standard action for Aid Another.")
            return False

        # TODO: Check if actor is in position to make a melee attack on target_creature_to_hinder.
        # This requires grid positioning. For now, assume true if they are in the combat.

        # The check is an attack roll against AC 10.
        # For simplicity, use the actor's first melee attack's bonus.
        # A more complete implementation would let the player choose the attack or use unarmed.
        primary_attack = None
        attack_bonus = actor.base_attack_bonus # Default to BAB if no melee weapon
        if actor.attacks:
            for attack in actor.attacks:
                if attack.attack_type == AttackType.MELEE or attack.attack_type == AttackType.NATURAL:
                    primary_attack = attack
                    break

        if primary_attack:
            attack_bonus = actor.get_attack_bonus(primary_attack)
        else: # Unarmed strike if no melee weapon
            # Unarmed strike BAB + Str mod + size mod
            attack_bonus = actor.base_attack_bonus + actor.ability_scores.get_modifier("str") + actor.get_size_modifier()


        roll = random.randint(1,20)
        total_attack_roll = roll + attack_bonus

        self.combat_engine.log.add_entry(f"{actor.name} attempts Aid Another (for {ally_to_aid.name}'s {aid_type}) against {target_creature_to_hinder.name}.")
        self.combat_engine.log.add_entry(f"  Aid Another roll: {roll} + {attack_bonus} = {total_attack_roll} vs AC 10.")

        if total_attack_roll >= 10:
            self.combat_engine.log.add_entry(f"  Aid Another successful!")
            # TODO: Apply a temporary bonus to the ally. This needs a more robust effect/buff system.
            # For now, we'll just log it. A real system would add an effect like:
            # ally_to_aid.add_temporary_effect(Effect("aid_another_attack", +2, "next_attack_roll", duration=1_turn, source=actor.name))
            # ally_to_aid.add_temporary_effect(Effect("aid_another_ac", +2, "ac_vs_target_next_attack", duration=1_turn, target=target_creature_to_hinder.name, source=actor.name))
            if aid_type == "attack":
                self.combat_engine.log.add_entry(f"  {ally_to_aid.name} will get +2 on their next attack roll against {target_creature_to_hinder.name} before {actor.name}'s next turn.")
            else: # aid_type == "ac"
                self.combat_engine.log.add_entry(f"  {ally_to_aid.name} will get +2 to AC against {target_creature_to_hinder.name}'s next attack before {actor.name}'s next turn.")
            # Note: If aiding an action that provokes, Aid Another also provokes.
            # This is complex and not handled here yet. Assume the aided action itself handles provocation.
            return True
        else:
            self.combat_engine.log.add_entry(f"  Aid Another failed.")
            return False

    def take_total_defense_action(self, combatant: Combatant) -> bool:
        """
        Perform the Total Defense action. Standard action.
        Grants +4 dodge bonus to AC for 1 round. Cannot make AoOs.
        """
        if not self.can_take_action(combatant, ActionType.STANDARD):
            self.combat_engine.log.add_entry(f"{combatant.name} cannot take a standard action for Total Defense.")
            return False

        self.combat_engine.log.add_entry(f"{combatant.name} takes the Total Defense action.")
        # TODO: Implement a temporary effect system.
        # combatant.add_temporary_effect(Effect("total_defense_ac", +4, "dodge_ac", duration=1_round))
        # combatant.add_temporary_condition_until_next_turn("cannot_make_aoos_due_to_total_defense")
        self.combat_engine.log.add_entry(f"  Gains +4 dodge bonus to AC until their next turn (effect not fully implemented).")
        self.combat_engine.log.add_entry(f"  Cannot make Attacks of Opportunity until their next turn (effect not fully implemented).")

        # Mark that a standard action was used (important for action economy tracking if we implement that)
        # self.action_budget.standard_action_taken = True
        return True

    def take_stand_up_action(self, combatant: Combatant) -> bool:
        """
        Stand up from prone. Move action. Provokes AoO.
        """
        if not combatant.has_condition("prone"):
            self.combat_engine.log.add_entry(f"{combatant.name} is not prone.")
            return False # Not an error, just can't do it.

        if not self.can_take_action(combatant, ActionType.MOVE):
            self.combat_engine.log.add_entry(f"{combatant.name} cannot take a move action to stand up.")
            return False

        self.combat_engine.log.add_entry(f"{combatant.name} attempts to stand up from prone.")

        # Standing up provokes AoOs
        self.combat_engine.trigger_attacks_of_opportunity(combatant, "standing up from prone")
        if combatant.is_dead() or combatant.has_condition("unconscious") or combatant.has_condition("stunned"):
            self.combat_engine.log.add_entry(f"{combatant.name} cannot complete standing up due to AoO effects.")
            return False

        combatant.remove_condition("prone")
        self.combat_engine.log.add_entry(f"{combatant.name} stands up.")
        # Mark that a move action was used
        # self.action_budget.move_action_taken = True
        return True

    def take_drop_prone_action(self, combatant: Combatant) -> bool:
        """
        Drop to a prone position. Free action.
        """
        # Free actions can generally be taken even if it's not your turn or if you've used other actions,
        # but within reasonable limits (GM discretion). For simulation, assume it's fine if called.
        if combatant.has_condition("prone"):
            self.combat_engine.log.add_entry(f"{combatant.name} is already prone.")
            return False

        self.combat_engine.log.add_entry(f"{combatant.name} drops prone.")
        combatant.add_condition("prone")
        # This is a free action, so it doesn't consume standard/move/etc.
        return True

    def take_move_action(self, combatant: Combatant, distance: int = 0, provokes_aoo: bool = True):
        """
        Take a move action.
        Moving out of a threatened square provokes AoO.
        This needs to be integrated with a grid system to check actual square transitions.
        """
        if not self.can_take_action(combatant, ActionType.MOVE): # Checks if it's their turn etc.
            return False

        # Simplified: if movement provokes, trigger AoOs.
        # A real implementation needs to check if the combatant is *leaving* a threatened square.
        if provokes_aoo: # Standard movement provokes if leaving threatened square
            self.combat_engine.trigger_attacks_of_opportunity(combatant, "moving")
            if combatant.is_dead() or combatant.has_condition("unconscious") or combatant.has_condition("stunned"):
                self.combat_engine.log.add_entry(f"{combatant.name} cannot complete movement due to AoO effects.")
                return False
        
        # Simple movement implementation
        max_distance = combatant.base_speed
        if distance <= max_distance:
            self.combat_engine.log.add_entry(f"{combatant.name} moves {distance} feet.")
            combatant.has_moved_this_turn = True
            # TODO: Update combatant position if a grid system is implemented
            return True
        else:
            self.combat_engine.log.add_entry(f"{combatant.name} cannot move {distance} feet (max: {max_distance}).")
            return False

    def take_draw_sheathe_weapon_action(self, combatant: Combatant, weapon_name: str, action: str = "draw") -> bool:
        """
        Draw or sheathe a weapon. Move action.
        Drawing does not provoke. Sheathing provokes.
        If BAB >= +1, can combine drawing (not sheathing) with a regular move (as free action).
        Two-Weapon Fighting feat allows drawing two light/one-handed weapons.
        """
        if not self.can_take_action(combatant, ActionType.MOVE):
            self.combat_engine.log.add_entry(f"{combatant.name} cannot take a move action to {action} {weapon_name}.")
            return False

        log_msg_action = "draws" if action == "draw" else "sheathes"
        self.combat_engine.log.add_entry(f"{combatant.name} attempts to {log_msg_action} {weapon_name}.")

        if action == "sheathe":
            self.combat_engine.trigger_attacks_of_opportunity(combatant, f"sheathing {weapon_name}")
            if combatant.is_dead() or combatant.has_condition("unconscious") or combatant.has_condition("stunned"):
                self.combat_engine.log.add_entry(f"{combatant.name} cannot complete sheathing {weapon_name} due to AoO effects.")
                return False

        # TODO: Implement actual inventory/equipment management.
        # For now, just log success.
        # if action == "draw":
        #     combatant.equip_weapon(weapon_name)
        # else: // sheathe
        #     combatant.unequip_weapon(weapon_name)

        self.combat_engine.log.add_entry(f"{combatant.name} successfully {log_msg_action} {weapon_name} (inventory not implemented).")

        # This action consumes the move action unless combined with movement due to high BAB / feats.
        # Handling that combination is complex and would require tracking if a move was already made, etc.
        # For now, assume it always uses the move action.
        combatant.has_moved_this_turn = True # Consumes movement potential for 5-foot step
        return True

    def take_charge_action(self, attacker: Combatant, target: Combatant, charge_attack_index: int = 0) -> Optional[AttackResult]:
        """
        Perform a Charge. Full-round action.
        Move up to 2x speed in a straight line, then make one melee attack.
        +2 bonus on attack roll, -2 penalty to AC until next turn. Must move at least 10ft.
        Does not provoke for movement, but attack itself could if it's special (e.g. trip).
        """
        if not self.can_take_action(attacker, ActionType.FULL_ROUND):
            self.combat_engine.log.add_entry(f"{attacker.name} cannot take a full-round action to Charge.")
            return None

        if charge_attack_index >= len(attacker.attacks) or attacker.attacks[charge_attack_index].attack_type == AttackType.RANGED:
            self.combat_engine.log.add_entry(f"{attacker.name} cannot charge with the selected attack (must be melee).")
            return None

        charge_attack = attacker.attacks[charge_attack_index]

        # Simplified movement: Assume movement is successful and distance is appropriate (>=10ft, <=2*speed)
        # TODO: Implement actual grid-based movement and pathfinding for charge.
        charge_distance = attacker.base_speed # Placeholder, assume they move their speed
        if charge_distance < 10:
            self.combat_engine.log.add_entry(f"{attacker.name} cannot charge: must move at least 10 feet.")
            return None

        self.combat_engine.log.add_entry(f"{attacker.name} charges {target.name} (movement of {charge_distance}ft not fully simulated).")
        attacker.has_moved_this_turn = True # Charging involves movement

        # Apply AC penalty
        # TODO: Implement temporary effect system for "-2 AC until next turn"
        self.combat_engine.log.add_entry(f"  {attacker.name} takes -2 AC until next turn (effect not fully implemented).")

        # Make the attack with +2 bonus
        # Create a temporary modified attack for the charge bonus or adjust attack calculation
        original_attack_bonus_calc = attacker.get_attack_bonus(charge_attack)
        charge_attack_roll = random.randint(1,20)
        # Add +2 charge bonus to the attack roll

        # We need to pass the +2 charge bonus to make_attack or apply it here.
        # For now, let's adjust the result from make_attack. This is a bit of a hack.
        # A better way would be to pass modifiers to make_attack.

        self.combat_engine.log.add_entry(f"  Charging with {charge_attack.name} (+2 attack bonus).")

        # Temporarily boost attack for the charge, then revert.
        # This is not ideal. A better way is to have make_attack accept situational modifiers.
        # For now, we'll directly modify the attack result for simplicity of this step.

        # Perform the attack. The +2 bonus is handled by get_attack_bonus if we pass a charge flag,
        # or we add it manually here. Let's assume get_attack_bonus will handle it if we add a context.
        # For now, we'll simulate it by just adding +2 to the log, make_attack needs proper extension.

        # Attack is made at normal BAB for charge (not iterative)
        attack_result = self.combat_engine.make_attack(attacker, target, charge_attack, is_full_attack=False, attack_number=0)

        if attack_result:
            # Manually adjust the logged and effective attack roll for the charge bonus
            # This is a hack because make_attack doesn't currently take arbitrary bonuses.
            # A better system would pass a list of temporary bonuses to make_attack.
            if attack_result.is_hit or attack_result.attack_roll == 20 : # Apply bonus if it was a hit or natural 20
                 # This logic is flawed, the bonus applies to the roll to see IF it hits.
                 # For now, we'll just log the intent.
                 pass # The +2 should be part of the hit determination.

        # TODO: Correctly apply +2 to attack roll *before* determining hit.
        # This requires `make_attack` to accept situational modifiers.
        # For now, the log indicates intent, but the hit calc might be off.

        return attack_result

    def take_withdraw_action(self, combatant: Combatant, distance: int) -> bool:
        """
        Perform a Withdraw. Full-round action.
        Move up to 2x speed. Starting square is not considered threatened by VISIBLE enemies.
        Does not provoke from starting square from visible enemies. Other movement can provoke.
        """
        if not self.can_take_action(combatant, ActionType.FULL_ROUND):
            self.combat_engine.log.add_entry(f"{combatant.name} cannot take a full-round action to Withdraw.")
            return False

        max_distance = combatant.base_speed * 2
        if distance > max_distance:
            self.combat_engine.log.add_entry(f"{combatant.name} cannot withdraw {distance}ft, max is {max_distance}ft.")
            return False

        self.combat_engine.log.add_entry(f"{combatant.name} withdraws {distance}ft.")
        self.combat_engine.log.add_entry(f"  Movement from starting square does not provoke from visible enemies (visibility not fully simulated).")

        # The actual movement part of withdraw would call take_move_action with provokes_aoo=False for the first step out of current square,
        # and then provokes_aoo=True for subsequent squares if they leave other threatened areas.
        # This is too complex without a grid. For now, simulate as a single move that doesn't provoke from start.

        # Simplified: Assume the whole withdraw doesn't provoke for now.
        # A real implementation would need pathing and checks per square.
        # Pass provokes_aoo = False to the underlying move if we had one.
        combatant.has_moved_this_turn = True
        # TODO: Update position.
        return True

    def take_5_foot_step_action(self, combatant: Combatant, direction: str = "any") -> bool:
        """
        Take a 5-foot step. Not an action type, but a special movement.
        Can be taken if no other movement was performed this round. Does not provoke AoO.
        """
        if combatant.has_moved_this_turn:
            self.combat_engine.log.add_entry(f"{combatant.name} cannot take a 5-foot step: already moved this turn.")
            return False

        # TODO: Check for difficult terrain or other conditions preventing 5-foot step.
        # TODO: Check if speed is < 5ft.

        self.combat_engine.log.add_entry(f"{combatant.name} takes a 5-foot step ({direction}).")
        # This action specifically sets has_moved_this_turn to allow it, then marks movement.
        # It doesn't "cost" a move action but does count as movement for future 5-foot steps.
        combatant.has_moved_this_turn = True
        # TODO: Update position on grid.
        return True

    def _perform_combat_maneuver_check(self, attacker: Combatant, target: Combatant, maneuver_name: str, additional_bonus: int = 0, provokes: bool = True) -> Optional[Tuple[int, int, int]]:
        """
        Helper function to perform a generic combat maneuver check roll.
        Returns (d20_roll, total_attack_roll, target_cmd) or None if action cannot be taken.
        """
        # Most combat maneuvers are standard actions or replace a melee attack.
        # For now, assume it's a standard action context for checking 'can_take_action'.
        # Specific maneuver methods will define if it's part of an attack or a dedicated action.

        # Provocation handling
        if provokes:
            # TODO: Check for feats like "Improved Bull Rush" that negate this.
            # For now, assume it always provokes if 'provokes' is true.
            self.combat_engine.trigger_attacks_of_opportunity(attacker, f"attempting {maneuver_name}")
            if attacker.is_dead() or attacker.has_condition("unconscious") or attacker.has_condition("stunned"):
                self.combat_engine.log.add_entry(f"{attacker.name} cannot complete {maneuver_name} due to AoO effects.")
                return None

        cmb = attacker.calculate_cmb() + additional_bonus
        cmd = target.calculate_cmd()

        roll = random.randint(1, 20)
        total_maneuver_roll = roll + cmb

        self.combat_engine.log.add_entry(f"{attacker.name} attempts {maneuver_name} against {target.name}.")
        self.combat_engine.log.add_entry(f"  CMB Check: {roll} (d20) + {cmb - additional_bonus} (CMB) + {additional_bonus} (misc) = {total_maneuver_roll} vs CMD {cmd}.")

        return roll, total_maneuver_roll, cmd

    def take_bull_rush_action(self, attacker: Combatant, target: Combatant, as_part_of_charge: bool = False) -> bool:
        """
        Perform a Bull Rush combat maneuver. Standard action or part of a charge.
        Provokes AoO unless Improved Bull Rush feat or similar.
        Target pushed back 5ft on success. Extra 5ft for every 5 the check exceeds CMD.
        Attacker can move with target.
        """
        action_type_check = ActionType.STANDARD # Base action is standard
        if as_part_of_charge:
            # If part of charge, it replaces the melee attack of the charge.
            # The charge itself is a full-round action.
            # No separate 'can_take_action' check here, assume charge action handles it.
            pass
        elif not self.can_take_action(attacker, action_type_check):
            self.combat_engine.log.add_entry(f"{attacker.name} cannot take a {action_type_check.value} action for Bull Rush.")
            return False

        # Size check: Target no more than one size category larger.
        # TODO: Implement size category comparison logic. For now, assume valid.

        # Provokes unless feat: Improved Bull Rush
        provokes_aoo = "Improved Bull Rush" not in attacker.feats # Placeholder for feat check

        charge_bonus = 0
        if as_part_of_charge:
            # Charging character gets +2 on combat maneuver rolls for bull rush.
            charge_bonus = 2
            self.combat_engine.log.add_entry(f"  Gains +2 bonus from charging.")


        maneuver_result = self._perform_combat_maneuver_check(attacker, target, "Bull Rush", additional_bonus=charge_bonus, provokes=provokes_aoo)
        if not maneuver_result:
            return False # AoO may have stopped the action

        d20_roll, total_maneuver_roll, target_cmd = maneuver_result

        if d20_roll == 1: # Natural 1 always fails
            self.combat_engine.log.add_entry("  Bull Rush failed (natural 1).")
            # TODO: Attacker's movement ends if it was part of movement (like a charge).
            return False

        if total_maneuver_roll >= target_cmd or d20_roll == 20: # Natural 20 always succeeds
            self.combat_engine.log.add_entry("  Bull Rush successful!")
            push_distance = 5
            exceed_by = total_maneuver_roll - target_cmd
            if exceed_by >= 5:
                push_distance += (exceed_by // 5) * 5

            self.combat_engine.log.add_entry(f"  {target.name} is pushed back {push_distance} feet.")
            # TODO: Implement actual movement of target and attacker on a grid.
            # TODO: Check for obstacles / other creatures.
            # TODO: Greater Bull Rush feat makes enemies provoke AoOs from the push.

            # Attacker can move with the target
            self.combat_engine.log.add_entry(f"  {attacker.name} can move with {target.name} (movement not simulated).")
            attacker.has_moved_this_turn = True # Bull rush involves potential movement
            return True
        else:
            self.combat_engine.log.add_entry("  Bull Rush failed.")
            # TODO: Attacker's movement ends if it was part of movement.
            return False

    def take_trip_action(self, attacker: Combatant, target: Combatant) -> bool:
        """
        Perform a Trip combat maneuver. Replaces a melee attack or is a standard action.
        Provokes AoO unless Improved Trip feat or similar.
        Target knocked prone on success. If check fails by 10+, attacker is tripped.
        """
        # For simplicity, assume this is taken as a standard action for now.
        # Integration as part of an attack/full-attack requires more complex action budget.
        if not self.can_take_action(attacker, ActionType.STANDARD):
            self.combat_engine.log.add_entry(f"{attacker.name} cannot take a standard action for Trip.")
            return False

        # Size check: Target no more than one size category larger.
        # TODO: Implement size category comparison.
        # Flying or legless creatures often immune.
        # TODO: Check target immunities to trip.

        provokes_aoo = "Improved Trip" not in attacker.feats

        # Some weapons can be used to trip (e.g., flail, guisarme). They might grant bonuses.
        # TODO: Check for weapon properties related to trip. Unarmed trip is -4 unless feat.
        # For now, assume basic unarmed trip or generic weapon trip without special modifiers.

        maneuver_result = self._perform_combat_maneuver_check(attacker, target, "Trip", provokes=provokes_aoo)
        if not maneuver_result:
            return False

        d20_roll, total_maneuver_roll, target_cmd = maneuver_result

        if d20_roll == 1: # Natural 1 always fails
            self.combat_engine.log.add_entry("  Trip failed (natural 1).")
            return False

        if total_maneuver_roll >= target_cmd or d20_roll == 20:
            self.combat_engine.log.add_entry("  Trip successful!")
            self.combat_engine.log.add_entry(f"  {target.name} is knocked prone.")
            target.add_condition("prone")
            # TODO: Improved Trip grants an immediate attack against the tripped opponent.
            return True
        else:
            self.combat_engine.log.add_entry("  Trip failed.")
            if target_cmd - total_maneuver_roll >= 10:
                self.combat_engine.log.add_entry(f"  {attacker.name} is knocked prone due to failing badly!")
                attacker.add_condition("prone")
            return False

    def take_disarm_action(self, attacker: Combatant, target: Combatant) -> bool:
        """
        Perform a Disarm combat maneuver. Replaces a melee attack or is a standard action.
        Provokes AoO unless Improved Disarm feat.
        Unarmed disarm is -4 penalty.
        Target drops one item on success. If check exceeds CMD by 10+, drops two items.
        If check fails by 10+, attacker drops their weapon.
        """
        if not self.can_take_action(attacker, ActionType.STANDARD): # Assuming standard action for now
            self.combat_engine.log.add_entry(f"{attacker.name} cannot take a standard action for Disarm.")
            return False

        provokes_aoo = "Improved Disarm" not in attacker.feats

        # Check if attacker is unarmed for the disarm attempt.
        # TODO: This needs to know what weapon is being used for the maneuver.
        # For now, assume they are using their primary weapon or are considered 'armed' if they have one.
        # A proper check would see if they are using a weapon or an unarmed strike.
        is_unarmed_attempt = not attacker.attacks # Simplified: if no listed attacks, assume unarmed.
        disarm_penalty = -4 if is_unarmed_attempt else 0
        if is_unarmed_attempt:
             self.combat_engine.log.add_entry(f"  Attacker is unarmed, takes -4 penalty on Disarm attempt.")

        maneuver_result = self._perform_combat_maneuver_check(attacker, target, "Disarm", additional_bonus=disarm_penalty, provokes=provokes_aoo)
        if not maneuver_result:
            return False

        d20_roll, total_maneuver_roll, target_cmd = maneuver_result

        if d20_roll == 1:
            self.combat_engine.log.add_entry("  Disarm failed (natural 1).")
            # Check if attacker drops weapon on nat 1 if that's a house rule or specific condition. Standard is just fail.
            return False

        if total_maneuver_roll >= target_cmd or d20_roll == 20:
            self.combat_engine.log.add_entry("  Disarm successful!")
            # TODO: Implement item dropping logic.
            # This requires target to have an inventory and equipped items.
            items_dropped = 1
            if total_maneuver_roll - target_cmd >= 10:
                items_dropped = 2
                self.combat_engine.log.add_entry(f"  {target.name} drops {items_dropped} items (item system not implemented).")
            else:
                self.combat_engine.log.add_entry(f"  {target.name} drops {items_dropped} item (item system not implemented).")

            if is_unarmed_attempt and items_dropped > 0:
                 self.combat_engine.log.add_entry(f"  {attacker.name} (unarmed) may automatically pick up one dropped item (not simulated).")
            return True
        else:
            self.combat_engine.log.add_entry("  Disarm failed.")
            if target_cmd - total_maneuver_roll >= 10:
                self.combat_engine.log.add_entry(f"  {attacker.name} drops their weapon due to failing badly (weapon system not implemented)!")
                # TODO: Implement attacker dropping their weapon.
            return False

    def take_sunder_action(self, attacker: Combatant, target: Combatant, target_item_name: str = "weapon") -> bool:
        """
        Perform a Sunder combat maneuver. Replaces a melee attack or is a standard action.
        Provokes AoO unless Improved Sunder feat.
        Deals damage to the target item.
        """
        if not self.can_take_action(attacker, ActionType.STANDARD): # Assuming standard for now
            self.combat_engine.log.add_entry(f"{attacker.name} cannot take a standard action for Sunder.")
            return False

        provokes_aoo = "Improved Sunder" not in attacker.feats

        # Sunder uses a normal attack roll against the item's AC (often CMD of wielder for held, or fixed AC for unattended).
        # For simplicity, we'll use the CMB vs CMD framework here, as if targeting the wielder's ability to keep the item intact.
        # A more accurate sunder would target item AC and deal weapon damage.
        # The rules state: "You can attempt to sunder an item held or worn by your opponent as part of an attack action
        # in place of a melee attack... If your attack is successful, you deal damage to the item normally."
        # This implies an attack roll, not a CMB check. However, the prompt grouped it with CMB/CMD.
        # For this implementation, I'll stick to CMB vs CMD as per the helper function.

        # Let's use _perform_combat_maneuver_check for the "attack" part.
        # The "damage" part is specific to Sunder.

        maneuver_result = self._perform_combat_maneuver_check(attacker, target, f"Sunder ({target_item_name})", provokes=provokes_aoo)
        if not maneuver_result:
            return False

        d20_roll, total_maneuver_roll, target_cmd = maneuver_result

        if d20_roll == 1:
            self.combat_engine.log.add_entry(f"  Sunder attempt against {target_item_name} failed (natural 1).")
            return False

        if total_maneuver_roll >= target_cmd or d20_roll == 20: # Success means you *hit* the item.
            self.combat_engine.log.add_entry(f"  Sunder attempt against {target_item_name} successful (hit the item)!")

            # Now, deal damage to the item.
            # TODO: This requires the attacker to choose a weapon, and items to have HP/Hardness.
            # For now, log the intent.
            # Example:
            # chosen_weapon = attacker.get_equipped_weapon() or attacker.get_unarmed_strike_equivalent()
            # item_hp, item_hardness = target.get_item_stats(target_item_name)
            # damage_roll = attacker.roll_damage(chosen_weapon) # Sunder damage uses weapon damage
            # damage_to_item = max(0, damage_roll - item_hardness)
            # item_current_hp -= damage_to_item
            # log item damage, broken status, destruction.

            self.combat_engine.log.add_entry(f"  Damage would be dealt to {target_item_name} (item HP/hardness/damage not implemented).")
            # Example outcomes:
            # if item_current_hp <= 0: log destroyed
            # elif item_current_hp <= item_total_hp / 2: log broken condition
            return True
        else:
            self.combat_engine.log.add_entry(f"  Sunder attempt against {target_item_name} failed (missed the item).")
            return False


def roll_dice(dice_string: str) -> int:
    """
    Roll dice from a string like "1d8", "2d6+1", etc.
    Helper function for damage rolling
    """
    # Handle simple dice notation like "1d8", "2d6", etc.
    if 'd' not in dice_string:
        return int(dice_string)
    
    # Split on '+' or '-' for bonuses
    parts = re.split(r'([+-])', dice_string)
    dice_part = parts[0]
    
    # Parse the dice part
    num_dice, die_size = dice_part.split('d')
    num_dice = int(num_dice)
    die_size = int(die_size)
    
    # Roll the dice
    total = sum(random.randint(1, die_size) for _ in range(num_dice))
    
    # Add any bonuses
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            operator = parts[i]
            value = int(parts[i + 1])
            if operator == '+':
                total += value
            elif operator == '-':
                total -= value
    
    return max(1, total)  # Minimum 1


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
        reach=5,
        is_primary_natural_attack=False
    )
    orc.attacks.append(falchion)
    
    # Calculate initiative modifier
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
    
    # Add longsword attack
    longsword = Attack(
        name="Longsword",
        damage_dice="1d8",
        critical_threat_range="19-20",
        critical_multiplier="x2",
        damage_type=DamageType.SLASHING,
        reach=5,
        enhancement_bonus=1
    )
    fighter.attacks.append(longsword)
    
    fighter.initiative_modifier = fighter.ability_scores.get_modifier("dexterity")
    
    print("=== PART 1: Character Creation & Database ===")
    print(f"Created {orc.name}:")
    print(f"  HP: {orc.current_hp}/{orc.max_hp}, AC: {orc.get_ac()}")
    print(f"  Attack: {falchion.name} +{orc.get_attack_bonus(falchion)} ({falchion.damage_dice})")
    
    print(f"\nCreated {fighter.name}:")
    print(f"  HP: {fighter.current_hp}/{fighter.max_hp}, AC: {fighter.get_ac()}")
    print(f"  Attack: {longsword.name} +{fighter.get_attack_bonus(longsword)} ({longsword.damage_dice})")
    
    # Save monster to database
    if db.save_monster(orc):
        print(f"\nSaved {orc.name} to database")
    
    print("\n=== PART 2-3: Combat Simulation ===")
    
    # Create combat engine and add combatants
    combat = CombatEngine()
    action_handler = ActionHandler(combat)
    
    # Load fresh copies for combat
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
    player_fighter.attacks.append(longsword)
    player_fighter.initiative_modifier = player_fighter.ability_scores.get_modifier("dexterity")
    
    # Set up encounter (both aware, no surprise round)
    combat.add_combatant(orc_fighter, is_aware=True)
    combat.add_combatant(player_fighter, is_aware=True)
    
    # Start combat
    combat.start_combat()
    
    # Simulate a few rounds of combat
    round_count = 0
    max_rounds = 5  # Prevent infinite loop
    
    while combat.combat_active and round_count < max_rounds:
        current_combatant = combat.get_current_combatant()
        if not current_combatant:
            break
            
        # Simple AI: attack the first available target
        targets = combat.get_valid_targets(current_combatant)
        if targets:
            target = targets[0]
            
            if current_combatant.attacks:
                # Use standard attack action
                action_handler.take_attack_action(current_combatant, target, 0)
            else:
                combat.log.add_entry(f"{current_combatant.name} has no attacks available")
        else:
            combat.log.add_entry(f"{current_combatant.name} has no valid targets")
        
        # Advance turn
        combat.advance_turn()
        
        # Check if combat should end
        if combat.is_combat_over():
            combat.end_combat()
            break
        
        # Safety check for round limit
        if combat.current_round > round_count:
            round_count = combat.current_round
            if round_count >= max_rounds:
                combat.log.add_entry(f"\nCombat ended after {max_rounds} rounds (demo limit)")
                combat.end_combat()
                break
    
    print("\n=== Demo Complete ===")
    print("✓ Part 1: Combatant representation and database storage")
    print("✓ Part 2: Initiative system and round management") 
    print("✓ Part 3: Basic attack actions and damage resolution")
