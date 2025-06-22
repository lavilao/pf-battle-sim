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
        """Calculate total AC"""
        effective_dex = dex_modifier
        if is_flat_footed:
            effective_dex = 0
        elif self.max_dex_bonus_from_armor is not None:
            effective_dex = min(effective_dex, self.max_dex_bonus_from_armor)
        
        return (10 + self.armor_bonus + self.shield_bonus + effective_dex + 
                self.natural_armor_bonus + self.deflection_bonus + 
                self.dodge_bonus + self.size_modifier)
    
    def calculate_touch_ac(self, dex_modifier: int, is_flat_footed: bool = False) -> int:
        """Calculate touch AC (no armor, shield, or natural armor)"""
        effective_dex = dex_modifier
        if is_flat_footed:
            effective_dex = 0
        elif self.max_dex_bonus_from_armor is not None:
            effective_dex = min(effective_dex, self.max_dex_bonus_from_armor)
        
        return (10 + effective_dex + self.deflection_bonus + 
                self.dodge_bonus + self.size_modifier)
    
    def calculate_flat_footed_ac(self, dex_modifier: int) -> int:
        """Calculate flat-footed AC (no dex bonus)"""
        return self.calculate_ac(dex_modifier, is_flat_footed=True)


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
    
    def calculate_cmb(self) -> int:
        """Calculate Combat Maneuver Bonus"""
        str_mod = self.ability_scores.get_modifier("strength")
        size_mod = self.get_size_modifier()
        return self.base_attack_bonus + str_mod + size_mod
    
    def calculate_cmd(self) -> int:
        """Calculate Combat Maneuver Defense"""
        str_mod = self.ability_scores.get_modifier("strength")
        dex_mod = self.ability_scores.get_modifier("dexterity")
        size_mod = self.get_size_modifier()
        
        # CMD uses AC modifiers (dodge, deflection, etc.) but not armor/shield/natural
        base_cmd = 10 + self.base_attack_bonus + str_mod + dex_mod + size_mod
        base_cmd += self.armor_class.deflection_bonus + self.armor_class.dodge_bonus
        
        if self.is_flat_footed:
            base_cmd -= dex_mod  # lose dex bonus when flat-footed
        
        return base_cmd
    
    def get_ac(self, ac_type: str = "standard") -> int:
        """Get armor class of specified type"""
        dex_mod = self.ability_scores.get_modifier("dexterity")
        
        if ac_type == "standard":
            return self.armor_class.calculate_ac(dex_mod, self.is_flat_footed)
        elif ac_type == "touch":
            return self.armor_class.calculate_touch_ac(dex_mod, self.is_flat_footed)
        elif ac_type == "flat_footed":
            return self.armor_class.calculate_flat_footed_ac(dex_mod)
        else:
            return self.armor_class.calculate_ac(dex_mod, self.is_flat_footed)
    
    def get_attack_bonus(self, attack: Attack, is_full_attack: bool = False, 
                        attack_number: int = 0) -> int:
        """Calculate total attack bonus for a specific attack"""
        ability_mod = self.ability_scores.get_modifier(attack.associated_ability_for_attack)
        size_mod = self.get_size_modifier()
        
        # Base attack bonus (reduced for iterative attacks in full attack)
        bab = self.base_attack_bonus
        if is_full_attack and attack_number > 0:
            bab -= (attack_number * 5)
        
        return bab + ability_mod + size_mod + attack.enhancement_bonus
    
    def get_damage_bonus(self, attack: Attack, is_off_hand: bool = False, 
                        is_two_handed: bool = False) -> int:
        """Calculate damage bonus for an attack"""
        ability_mod = self.ability_scores.get_modifier(attack.associated_ability_for_damage)
        
        # Modify strength bonus based on attack type
        if attack.associated_ability_for_damage == "strength":
            if is_off_hand:
                ability_mod = ability_mod // 2 if ability_mod > 0 else ability_mod
            elif is_two_handed and self.size != "Small":  # Two-handed weapons
                ability_mod = int(ability_mod * 1.5)
        
        return ability_mod + attack.enhancement_bonus
    
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
        return effective_damage
    
    def heal(self, amount: int) -> int:
        """Heal damage"""
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - old_hp
    
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
        
        # Announce whose turn it is
        current_combatant = self.get_current_combatant()
        if current_combatant:
            if self.is_surprise_round and not self.can_act_in_surprise_round(current_combatant):
                self.log.add_entry(f"{current_combatant.name}'s turn (cannot act - unaware)")
                self.advance_turn()  # Skip unaware combatants in surprise round
            else:
                self.log.add_entry(f"{current_combatant.name}'s turn")
    
    def make_attack(self, attacker: Combatant, target: Combatant, attack: Attack, 
                   is_full_attack: bool = False, attack_number: int = 0) -> AttackResult:
        """
        Execute an attack between two combatants
        Implements Part 3 attack mechanics
        """
        result = AttackResult(attacker.name, target.name, attack.name)
        
        # Calculate attack bonus
        result.total_attack_bonus = attacker.get_attack_bonus(attack, is_full_attack, attack_number)
        
        # Roll attack
        result.attack_roll = random.randint(1, 20)
        total_attack = result.attack_roll + result.total_attack_bonus
        
        # Determine target AC
        if target.is_flat_footed:
            result.target_ac = target.get_ac("flat_footed")
        else:
            result.target_ac = target.get_ac("standard")
        
        # Check for hit
        is_natural_1 = result.attack_roll == 1
        is_natural_20 = result.attack_roll == 20
        
        if is_natural_1:
            result.is_hit = False
        elif is_natural_20:
            result.is_hit = True
            result.is_critical_threat = True
        else:
            result.is_hit = total_attack >= result.target_ac
            # Check for critical threat
            if result.is_hit and result.attack_roll in attack.get_threat_range():
                result.is_critical_threat = True
        
        self.log.add_entry(f"{attacker.name} attacks {target.name} with {attack.name}")
        self.log.add_entry(f"  Attack roll: {result.attack_roll} + {result.total_attack_bonus} = {total_attack} vs AC {result.target_ac}")
        
        if not result.is_hit:
            self.log.add_entry("  MISS!")
            return result
        
        self.log.add_entry("  HIT!")
        
        # Handle critical hit confirmation
        if result.is_critical_threat:
            self.log.add_entry("  Critical threat! Rolling to confirm...")
            confirm_roll = random.randint(1, 20)
            confirm_total = confirm_roll + result.total_attack_bonus
            
            if confirm_total >= result.target_ac:
                result.is_critical_hit = True
                self.log.add_entry(f"  Confirmation roll: {confirm_roll} + {result.total_attack_bonus} = {confirm_total} - CRITICAL HIT!")
            else:
                self.log.add_entry(f"  Confirmation roll: {confirm_roll} + {result.total_attack_bonus} = {confirm_total} - confirmed as normal hit")
        
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
            # In surprise round, only standard OR move actions allowed (plus free/swift)
            if action_type in [ActionType.FULL_ROUND]:
                return False
        
        return True
    
    def take_attack_action(self, attacker: Combatant, target: Combatant, 
                          attack_index: int = 0) -> Optional[AttackResult]:
        """Take a standard attack action"""
        if not self.can_take_action(attacker, ActionType.STANDARD):
            return None
        
        if attack_index >= len(attacker.attacks):
            self.combat_engine.log.add_entry(f"{attacker.name} has no attack at index {attack_index}")
            return None
        
        attack = attacker.attacks[attack_index]
        return self.combat_engine.make_attack(attacker, target, attack)
    
    def take_full_attack_action(self, attacker: Combatant, target: Combatant, 
                               attack_index: int = 0) -> List[AttackResult]:
        """Take a full-attack action (all available attacks)"""
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
    
    def take_move_action(self, combatant: Combatant, distance: int = 0):
        """Take a move action"""
        if not self.can_take_action(combatant, ActionType.MOVE):
            return False
        
        # Simple movement implementation
        max_distance = combatant.base_speed
        if distance <= max_distance:
            self.combat_engine.log.add_entry(f"{combatant.name} moves {distance} feet")
            return True
        else:
            self.combat_engine.log.add_entry(f"{combatant.name} cannot move {distance} feet (max: {max_distance})")
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
