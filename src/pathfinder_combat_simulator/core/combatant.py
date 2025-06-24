import random
from dataclasses import dataclass, field # Added dataclass here
from typing import Dict, List, Optional, Any, Tuple

from .enums import AttackType, DamageType # Added DamageType
from .ability_scores import AbilityScores
from .armor_class import ArmorClass
from .saving_throws import SavingThrows
from .attack import Attack


@dataclass # Added this decorator as Combatant seems to use it implicitly via other dataclasses
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
            for attack_obj in self.attacks: # Renamed to avoid conflict with Attack class
                if attack_obj.reach > 0 and attack_obj.attack_type in [AttackType.MELEE, AttackType.NATURAL]:
                    reach = attack_obj.reach
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
                    # manhattan_dist = abs(dx) + abs(dy) # Not used
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
            # dr_type = self.damage_reduction.get("type", "") # Not used

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
                "damage_type": attack.damage_type.value, # Changed from attack_obj to attack
                "reach": attack.reach,
                "associated_ability_for_attack": attack.associated_ability_for_attack,
                "associated_ability_for_damage": attack.associated_ability_for_damage,
                "is_primary_natural_attack": attack.is_primary_natural_attack,
                "special_qualities": attack.special_qualities,
                "enhancement_bonus": attack.enhancement_bonus
            } for attack in self.attacks], # Changed from attack_obj to attack
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
            combatant.armor_class.size_modifier = ac_data.get("size_modifier", 0) # This was missing, added based on definition
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
                attack_instance = Attack( # Renamed to avoid conflict
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
                combatant.attacks.append(attack_instance)

        # Calculate initiative modifier
        combatant.initiative_modifier = combatant.ability_scores.get_modifier("dexterity")

        return combatant
