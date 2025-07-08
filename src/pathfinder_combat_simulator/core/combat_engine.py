import random
from typing import List, Tuple, Optional

from .combatant import Combatant
from .attack import Attack
from .enums import AttackType # For make_attack -> target.has_condition("prone") and attack.attack_type
from .attack_result import AttackResult
from .combat_log import CombatLog

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
        # Add a way to store surprise round awareness if not already on combatant
        # This was done using setattr in the original file, which is not ideal.
        # Let's add an attribute to Combatant or handle it here.
        # For now, let's assume Combatant might get an 'is_aware_in_surprise_round' attribute.
        # If not, this needs adjustment.
        # The original code used: combatant.is_aware_in_surprise_round = is_aware
        # We'll replicate this understanding for now.
        setattr(combatant, 'is_aware_in_surprise_round', is_aware) # Keep original logic for now
        self.combatants.append(combatant)

    def roll_initiative(self):
        """Roll initiative for all combatants and sort by result"""
        self.log.add_entry("=== Rolling Initiative ===")

        initiative_results = []
        for combatant in self.combatants:
            # Roll 1d20 + initiative modifier
            roll = random.randint(1, 20)
            # Ensure initiative_modifier is calculated if not already
            if combatant.initiative_modifier == 0 and combatant.ability_scores.get_modifier("dexterity") != 0 :
                 # This check is a bit fragile, assumes it's only 0 if not set.
                 # Better to ensure it's always calculated on Combatant init or update.
                 combatant.initiative_modifier = combatant.ability_scores.get_modifier("dexterity")

            total = roll + combatant.initiative_modifier
            combatant.current_initiative_roll = roll
            combatant.final_initiative_score = total

            initiative_results.append((combatant, total, roll)) # Added original roll for tie-breaking
            self.log.add_entry(f"{combatant.name}: {roll} (roll) + {combatant.initiative_modifier} (mod) = {total}")

        # Sort by initiative (highest first), then by initiative modifier, then by original roll
        # The original sort was: (x[1], x[0].initiative_modifier, x[2]), reverse=True
        # x[1] = total, x[0] = combatant, x[2] = roll. This seems correct.
        initiative_results.sort(key=lambda x: (x[1], x[0].initiative_modifier, x[2]), reverse=True)

        # Handle ties with additional d20 rolls if needed (Pathfinder official rule for ties after Dex mod)
        # The original code had a more complex tie-breaking that re-rolled d20s.
        # Standard Pathfinder: Highest initiative result wins. If tied, highest Dex mod wins.
        # If still tied, highest init roll (1d20) wins. If still tied, players decide or GM rolls off.
        # The provided code's tie-breaking (re-rolling d20s if total and mod are tied) is a house rule.
        # Let's stick to the provided code's logic for now.

        final_results_tuples = [] # Using tuples (Combatant, int_score) for self.initiative_order
        i = 0
        while i < len(initiative_results):
            # Check for ties based on final initiative score AND initiative modifier
            # (as per the original complex tie-breaking condition)
            tied_group_indices = [i]
            j = i + 1
            while (j < len(initiative_results) and
                   initiative_results[j][1] == initiative_results[i][1] and # Same total score
                   initiative_results[j][0].initiative_modifier == initiative_results[i][0].initiative_modifier): # Same Dex mod
                tied_group_indices.append(j)
                j += 1

            if len(tied_group_indices) > 1:
                self.log.add_entry(f"Breaking tie for score {initiative_results[i][1]} and mod {initiative_results[i][0].initiative_modifier} between: {', '.join(initiative_results[k][0].name for k in tied_group_indices)}")

                # Extract the tied combatants for re-sorting with tie-breaker rolls
                tied_combatants_data = [initiative_results[k] for k in tied_group_indices]

                # Add tiebreaker d20 roll for each in the tied group
                for k_idx, (combatant, total, original_roll) in enumerate(tied_combatants_data):
                    tiebreaker_roll = random.randint(1, 20)
                    # Store as (combatant, total, original_roll, tiebreaker_roll)
                    tied_combatants_data[k_idx] = (combatant, total, original_roll, tiebreaker_roll)
                    self.log.add_entry(f"  {combatant.name} tiebreaker roll: {tiebreaker_roll}")

                # Sort this group by the tiebreaker roll (descending)
                tied_combatants_data.sort(key=lambda x: x[3], reverse=True)

                # Add sorted tied group to final results
                for combatant_data in tied_combatants_data:
                    final_results_tuples.append((combatant_data[0], combatant_data[1]))
            else:
                # No tie requiring d20 roll-off for this combatant, add directly
                final_results_tuples.append((initiative_results[i][0], initiative_results[i][1]))

            i = j # Move to the next segment

        self.initiative_order = final_results_tuples

        self.log.add_entry("\n=== Final Initiative Order ===")
        for idx, (combatant, initiative_val) in enumerate(self.initiative_order):
            self.log.add_entry(f"{idx+1}. {combatant.name}: {initiative_val}")

    def start_combat(self):
        """Start combat encounter"""
        if not self.combatants:
            self.log.add_entry("No combatants in encounter!")
            return False # Indicate failure to start

        self.log.add_entry("=== COMBAT BEGINS ===")
        self.roll_initiative() # Sets self.initiative_order

        # Check for surprise round
        # A combatant is surprised if they haven't noticed any opponents.
        # The 'is_aware_in_surprise_round' flag handles this.
        aware_combatants = [c for c in self.combatants if getattr(c, 'is_aware_in_surprise_round', True)]
        unaware_combatants = [c for c in self.combatants if not getattr(c, 'is_aware_in_surprise_round', True)]

        if aware_combatants and unaware_combatants: # Surprise round only if some are aware and some are not
            self.log.add_entry("\n=== SURPRISE ROUND ===")
            self.log.add_entry(f"Unaware and flat-footed: {', '.join(c.name for c in unaware_combatants)}")
            self.is_surprise_round = True
            self.current_round = 0 # Surprise round is before round 1
            self.current_turn_index = 0 # Start with first in initiative order
            self.combat_active = True

            for combatant in unaware_combatants:
                combatant.is_flat_footed = True # Ensure they are flat-footed
                combatant.add_condition("flat-footed") # Redundant if is_flat_footed handles this
        else:
            # No surprise round if all are aware or all are unaware
            if unaware_combatants and not aware_combatants:
                 self.log.add_entry("All combatants are unaware! No surprise round, proceed to normal rounds with everyone flat-footed.")
                 for c in self.combatants:
                     c.is_flat_footed = True
                     c.add_condition("flat-footed")
            else: # All aware
                 self.log.add_entry("All combatants are aware. No surprise round.")

            self.is_surprise_round = False
            self.current_round = 1
            self.current_turn_index = 0
            self.combat_active = True
            self.log.add_entry(f"\n=== ROUND {self.current_round} ===")

        # Initial turn announcement
        self.announce_turn()
        return True

    def get_current_combatant(self) -> Optional[Combatant]:
        """Get the combatant whose turn it currently is, skipping defeated ones."""
        if not self.combat_active or not self.initiative_order:
            return None

        # Loop to find the next non-defeated combatant
        original_index = self.current_turn_index
        while True:
            if self.current_turn_index >= len(self.initiative_order):
                # This should be handled by advance_turn's round completion logic
                return None

            combatant, _ = self.initiative_order[self.current_turn_index]
            # Check if combatant is defeated (HP <= 0, or has 'dead', 'unconscious' conditions)
            # Original code used current_hp <= 0. Let's refine to check conditions.
            if combatant.current_hp > 0 and not combatant.is_dead() and not combatant.has_condition("unconscious"):
                return combatant

            # Move to next index, loop around if end of list reached (should not happen here, but in advance_turn)
            self.current_turn_index += 1
            if self.current_turn_index >= len(self.initiative_order):
                # This case means all remaining combatants are defeated or end of round.
                # Handled by advance_turn. If called directly, indicates an issue or end of combat.
                return None

            # Safety break if we loop through everyone and find no one (should be caught by is_combat_over)
            if self.current_turn_index == original_index:
                # This implies all combatants are defeated.
                return None

    def can_act_in_surprise_round(self, combatant: Combatant) -> bool:
        """Check if a combatant can act in the surprise round"""
        # Only aware combatants can act (standard or move action).
        return getattr(combatant, 'is_aware_in_surprise_round', True)

    def announce_turn(self):
        """Announces the current combatant's turn."""
        current_combatant = self.get_current_combatant()
        if current_combatant:
            if self.is_surprise_round and not self.can_act_in_surprise_round(current_combatant):
                self.log.add_entry(f"{current_combatant.name}'s turn (cannot act - unaware in surprise round)")
                # Automatically advance turn if they can't act.
                self.advance_turn()
            else:
                self.log.add_entry(f"{current_combatant.name}'s turn ({current_combatant.current_hp}/{current_combatant.max_hp} HP)")
                # Start of turn effects for the current combatant
                self.process_start_of_turn_effects(current_combatant)
        elif self.combat_active:
            # This might happen if all combatants are defeated or an error occurred.
            # is_combat_over should catch this.
            self.log.add_entry("No valid combatant for current turn. Checking combat status.")
            if self.is_combat_over():
                self.end_combat()


    def process_start_of_turn_effects(self, combatant: Combatant):
        """Processes effects that occur at the start of a combatant's turn."""
        # Example: Dying and not stable
        if combatant.is_dying() and not combatant.has_condition("stable"):
            self.log.add_entry(f"{combatant.name} is dying and must make a stabilization check (or loses HP).")
            # Pathfinder rule: DC 10 + negative HP Con check to stabilize.
            # If no one is attempting to stabilize them with Heal skill.
            # If they fail, they lose 1 HP.
            # For simplicity, the Combatant.stabilize() method handles this logic.
            if combatant.stabilize(): # Stabilize is a Con check vs 10 + neg HP.
                self.log.add_entry(f"{combatant.name} made a Constitution check and stabilized!")
            else:
                self.log.add_entry(f"{combatant.name} failed stabilization check and loses 1 HP.")
                # combatant.take_damage(1, "untyped_hp_loss") # take_damage might be too complex, direct HP loss
                # The Combatant.stabilize() method already handles HP loss on failure.
                if combatant.is_dead():
                    self.log.add_entry(f"{combatant.name} has died from HP loss.")
                else:
                    self.log.add_entry(f"{combatant.name} HP: {combatant.current_hp}/{combatant.max_hp}")

        # TODO: Other start-of-turn effects (e.g., ongoing damage, regeneration, condition recovery rolls)


    def advance_turn(self):
        """Advance to the next combatant's turn or next round."""
        if not self.combat_active:
            return

        current_combatant_obj = self.get_current_combatant() # Get combatant before advancing index

        # End of current combatant's turn processing
        if current_combatant_obj:
            # Mark as acted if it was their turn (even if they did nothing)
            if not current_combatant_obj.has_acted_this_combat:
                current_combatant_obj.has_acted_this_combat = True

            # In a regular round (not surprise), if they acted, they are no longer flat-footed.
            # This is usually handled at the *start* of their first regular turn.
            if not self.is_surprise_round and current_combatant_obj.is_flat_footed:
                 # If it's their first turn in normal combat and they were flat-footed
                 if getattr(current_combatant_obj, 'is_aware_in_surprise_round', True) or self.current_round > 0 : # check if they were aware or if surprise round is over
                    current_combatant_obj.is_flat_footed = False
                    current_combatant_obj.remove_condition("flat-footed") # if condition is used
                    self.log.add_entry(f"  {current_combatant_obj.name} is no longer flat-footed.")

            # Reset 5-foot step flag for this combatant for *their* next turn (if they moved)
            # This is usually reset at end of round for everyone, or start of their turn.
            # The original code had `cb.has_moved_this_turn = False` at end of round.
            # Let's assume `has_moved_this_turn` is for the *current* turn actions.
            # It should be reset for the *next* turn.
            # The current logic in original code resets it for everyone at end of full round.

        self.current_turn_index += 1

        # Check if round is complete
        if self.current_turn_index >= len(self.initiative_order):
            self.log.add_entry(f"--- End of Round {self.current_round if not self.is_surprise_round else 'Surprise'} ---")

            # Process end-of-round effects for all combatants
            for cb in self.combatants:
                # Reset AoO counts
                cb.aoo_made_this_round = 0
                # Reset 5-foot step availability (has_moved_this_turn)
                cb.has_moved_this_turn = False
                # TODO: Other end-of-round effects (spell durations, condition timers)

            if self.is_surprise_round:
                self.is_surprise_round = False
                self.current_round = 1 # Start of the first regular round
                self.current_turn_index = 0
                self.log.add_entry(f"\n=== ROUND {self.current_round} (Normal Combat Begins) ===")
                # At start of first normal round, those who were surprised but didn't act might lose flat-footed if they can now act.
                # Generally, flat-footed is lost when a character takes their first action in combat.
                # Or, if they were not surprised, they are not flat-footed at start of round 1.
                for combatant_in_list, _ in self.initiative_order:
                    if getattr(combatant_in_list, 'is_aware_in_surprise_round', True): # If they were aware
                        if combatant_in_list.is_flat_footed: # And somehow still flat-footed
                            combatant_in_list.is_flat_footed = False
                            combatant_in_list.remove_condition("flat-footed")
                    else: # If they were unaware (surprised)
                        # They remain flat-footed until their first turn in normal combat.
                        # This is handled when their turn comes up.
                        pass
            else:
                self.current_round += 1
                self.current_turn_index = 0
                self.log.add_entry(f"\n=== ROUND {self.current_round} ===")

            # Check for combat end after round processing
            if self.is_combat_over():
                self.end_combat()
                return # Combat ended

        # Announce whose turn it is now
        if self.combat_active: # Combat might have ended in round processing
            self.announce_turn()


    def can_make_aoo(self, combatant: Combatant) -> bool:
        """Check if a combatant can make an Attack of Opportunity."""
        # Cannot make AoOs if flat-footed, unless they have Combat Reflexes feat.
        if combatant.is_flat_footed and "Combat Reflexes" not in combatant.feats:
            return False

        # Other conditions preventing AoOs: stunned, paralyzed, helpless, unconscious, etc.
        if combatant.has_condition("stunned") or \
           combatant.has_condition("paralyzed") or \
           combatant.has_condition("helpless") or \
           combatant.has_condition("unconscious") or \
           combatant.is_dead():
            return False

        max_aoos = 1
        if "Combat Reflexes" in combatant.feats:
            dex_mod = combatant.ability_scores.get_modifier("dexterity")
            max_aoos += dex_mod
            if max_aoos < 1 and "Combat Reflexes" in combatant.feats : max_aoos = 1
            elif max_aoos < 0 : max_aoos = 0

        return combatant.aoo_made_this_round < max_aoos

    def trigger_attacks_of_opportunity(self, provoking_combatant: Combatant, provoking_action_type: str):
        """
        Checks for and resolves AoOs against a combatant performing a provoking action.
        Requires grid/positioning for actual threat checks.
        """
        self.log.add_entry(f"{provoking_combatant.name} performing '{provoking_action_type}' may provoke AoOs.")

        # Iterate through all combatants that are not the one provoking the AoO.
        for potential_attacker in self.combatants:
            if potential_attacker == provoking_combatant or \
               potential_attacker.is_dead() or \
               potential_attacker.has_condition("unconscious") or \
               potential_attacker.has_condition("stunned") or \
               potential_attacker.has_condition("paralyzed"): # Cannot act
                continue

            # 1. Does potential_attacker threaten provoking_combatant's STARTING square?
            #    This needs a grid system. For now, assume they do if within reach.
            #    A more robust check:
            #    provoking_pos = self.get_combatant_position(provoking_combatant)
            #    attacker_pos = self.get_combatant_position(potential_attacker)
            #    if provoking_pos in potential_attacker.get_threatened_squares(attacker_pos):
            # For this placeholder, we'll assume "yes" if they can make an AoO.
            # This is a major simplification.

            # 2. Can potential_attacker make an AoO?
            if self.can_make_aoo(potential_attacker):
                # Placeholder: Assume the first melee/natural attack is used for AoO.
                # A real system might allow choice or use unarmed if no weapon.
                aoo_attack_to_use = None
                for att in potential_attacker.attacks:
                    print(f"    Checking attack: {att.name}, type: {att.attack_type}, reach: {att.reach}")
                    if att.attack_type in [AttackType.MELEE, AttackType.NATURAL] and att.reach > 0:
                        aoo_attack_to_use = att
                        break

                if not aoo_attack_to_use: # No suitable weapon, try unarmed strike (placeholder)
                    # Create a temporary unarmed strike attack for AoO
                    # This is a simplification. Unarmed strikes have specific rules.
                    # For now, if no weapon, log and skip.
                    self.log.add_entry(f"  {potential_attacker.name} could make an AoO but has no suitable melee/natural attack listed.")
                    print(f"  {potential_attacker.name} has no suitable AoO attack. Skipping.")
                    continue


                self.log.add_entry(f"  {potential_attacker.name} gets an Attack of Opportunity against {provoking_combatant.name} with {aoo_attack_to_use.name}!")
                print(f"Attempting to increment aoo_made_this_round for {potential_attacker.name}")
                # Make the attack. AoOs are single attacks.
                attack_outcome = self.make_attack(potential_attacker, provoking_combatant, aoo_attack_to_use, is_aoo=True)
                potential_attacker.aoo_made_this_round += 1
                self.log.add_entry(f"  {potential_attacker.name} has made {potential_attacker.aoo_made_this_round} AoOs this round.")

                # If the provoking combatant is downed by the AoO, their action is often interrupted.
                if provoking_combatant.is_dead() or \
                   provoking_combatant.has_condition("unconscious") or \
                   provoking_combatant.has_condition("stunned") or \
                   provoking_combatant.has_condition("paralyzed"):
                    self.log.add_entry(f"  {provoking_combatant.name} is downed or incapacitated by the AoO! Action ({provoking_action_type}) is interrupted.")
                    # TODO: Need a mechanism to flag the original action as interrupted.
                    # For now, this loop breaks, preventing further AoOs against this specific action.
                    break
            # else:
            #     self.log.add_entry(f"  {potential_attacker.name} cannot make an AoO (flat-footed, max AoOs, or no reach).")


    def make_attack(self, attacker: Combatant, target: Combatant, attack: Attack,
                   is_full_attack: bool = False, attack_number: int = 0, is_aoo: bool = False,
                   additional_attack_bonus_list: Optional[List[Tuple[int, str]]] = None, # e.g. [(2, "charge bonus")]
                   additional_damage_bonus_list: Optional[List[Tuple[int, str]]] = None # e.g. [(1, "strength surge")]
                   ) -> AttackResult:
        """
        Execute an attack between two combatants.
        `additional_bonus_list` contains tuples of (bonus_value, bonus_description_str).
        """
        result = AttackResult(attacker.name, target.name, attack.name)

        # Calculate total attack bonus
        base_attack_bonus_val = attacker.get_attack_bonus(
            attack,
            is_full_attack=is_full_attack and not is_aoo, # AoO is never part of full attack sequence for BAB penalty
            attack_number=(0 if is_aoo else attack_number), # AoO is always first attack BAB
            target=target # For target-specific effects on attacker's roll
        )

        current_total_attack_bonus = base_attack_bonus_val
        bonus_descriptions = []

        if additional_attack_bonus_list:
            for bonus_val, bonus_desc in additional_attack_bonus_list:
                current_total_attack_bonus += bonus_val
                bonus_descriptions.append(f"{bonus_val} ({bonus_desc})")

        result.total_attack_bonus = current_total_attack_bonus

        # Roll attack (1d20)
        result.attack_roll = random.randint(1, 20)
        total_attack_value = result.attack_roll + result.total_attack_bonus

        # Determine target AC
        # Base AC type determination
        ac_type_to_use = "standard"
        # Conditions making target flat-footed or lose Dex to AC
        if target.is_flat_footed or \
           target.has_condition("helpless") or \
           target.has_condition("stunned") or \
           target.has_condition("paralyzed") or \
           target.has_condition("blinded"): # Blinded creatures are effectively flat-footed
            ac_type_to_use = "flat_footed"
            # Note: get_ac should correctly calculate flat-footed AC by ignoring Dex if positive.

        result.target_ac = target.get_ac(ac_type_to_use) # get_ac should handle size mods internally

        # Specific AC adjustments based on target's state vs attack type (e.g., Prone)
        # This was in original code, good to keep if get_ac doesn't handle context.
        # However, get_ac in Combatant *does* have a TODO for prone.
        # For now, let's assume get_ac does NOT handle this context yet.
        if target.has_condition("prone"):
            if attack.attack_type == AttackType.RANGED:
                self.log.add_entry(f"  Target {target.name} is prone, gains +4 AC vs this ranged attack.")
                result.target_ac += 4
            elif attack.attack_type == AttackType.MELEE:
                self.log.add_entry(f"  Target {target.name} is prone, takes -4 AC vs this melee attack.")
                result.target_ac -= 4 # This is a penalty to AC, so subtract from AC value

        # Log attack attempt
        attack_log_str = f"{attacker.name} attacks {target.name} with {attack.name}"
        if is_aoo: attack_log_str += " (AoO)"
        self.log.add_entry(attack_log_str)

        bonus_desc_str = f"{base_attack_bonus_val} (base)"
        if bonus_descriptions:
            bonus_desc_str += " + " + " + ".join(bonus_descriptions)

        self.log.add_entry(f"  Attack Roll: {result.attack_roll} (d20) + {result.total_attack_bonus} (total bonus [{bonus_desc_str}]) = {total_attack_value} vs AC {result.target_ac}")

        # Check for Hit or Miss
        is_natural_1 = (result.attack_roll == 1)
        is_natural_20 = (result.attack_roll == 20)

        if is_natural_1: # Automatic miss
            result.is_hit = False
            self.log.add_entry("  MISS! (Natural 1)")
            return result

        # Hit occurs if total_attack_value >= target_ac, or natural 20
        result.is_hit = (total_attack_value >= result.target_ac) or is_natural_20

        if not result.is_hit:
            self.log.add_entry("  MISS!")
            return result

        # HIT! Now check for critical threat (if not natural 1)
        if is_natural_20: # Natural 20 always threatens
            result.is_critical_threat = True
        elif result.attack_roll in attack.get_threat_range(): # Check weapon's threat range
            result.is_critical_threat = True

        # Check for concealment miss chance (e.g., from attacker being blinded, or target having concealment)
        # This should be checked *after* determining a hit, but *before* critical confirmation.
        miss_chance_percent = 0
        concealment_reason = ""
        if attacker.has_condition("blinded"): # Attacker is blind
            miss_chance_percent = 50 # Total concealment for attacker
            concealment_reason = f"attacker {attacker.name} is blinded"
        # TODO: Add other sources of concealment for the target (e.g. blur, displacement, fog)
        # Example: if target.has_effect("blur"): miss_chance_percent = max(miss_chance_percent, 20)

        if miss_chance_percent > 0:
            self.log.add_entry(f"  Target has {miss_chance_percent}% miss chance due to {concealment_reason}.")
            if random.randint(1, 100) <= miss_chance_percent:
                self.log.add_entry(f"  HIT! (but the hit was negated by {miss_chance_percent}% miss chance)")
                result.is_hit = False # Mark as miss due to concealment
                result.is_critical_threat = False # Concealment miss negates critical threat
                result.is_critical_hit = False
                return result # Attack effectively missed

        self.log.add_entry("  HIT!") # If not missed due to concealment

        # Handle critical hit confirmation if it's a critical threat
        if result.is_critical_threat:
            self.log.add_entry("  Critical threat! Rolling to confirm...")
            # Confirmation roll uses same total attack bonus as original attack roll
            confirm_roll_d20 = random.randint(1, 20)
            confirm_total_value = confirm_roll_d20 + result.total_attack_bonus # Use the same total_attack_bonus

            # Target AC for confirmation is their normal AC (concealment does not apply to confirmation roll itself)
            # Use the same AC calculated for the original hit (result.target_ac)
            confirm_target_ac = result.target_ac

            self.log.add_entry(f"  Confirmation Roll: {confirm_roll_d20} (d20) + {result.total_attack_bonus} (bonus) = {confirm_total_value} vs AC {confirm_target_ac}")

            if confirm_roll_d20 == 1: # Natural 1 on confirmation always fails to confirm
                result.is_critical_hit = False
                self.log.add_entry("  Critical confirmation failed (Natural 1 on confirm roll). Normal hit.")
            elif confirm_total_value >= confirm_target_ac or confirm_roll_d20 == 20: # Confirmed if hits or natural 20 on confirm
                result.is_critical_hit = True
                self.log.add_entry("  CRITICAL HIT CONFIRMED!")
            else:
                result.is_critical_hit = False
                self.log.add_entry("  Critical confirmation failed. Normal hit.")

        # Roll damage
        # TODO: Determine is_off_hand, is_two_handed from attacker/weapon state
        is_off_hand_weapon = False
        is_two_handed_weapon = False

        base_damage = attacker.roll_damage(attack, result.is_critical_hit,
                                          is_off_hand_weapon, is_two_handed_weapon)

        current_total_damage = base_damage
        damage_bonus_descriptions = []

        if additional_damage_bonus_list:
            for bonus_val, bonus_desc in additional_damage_bonus_list:
                current_total_damage += bonus_val
                damage_bonus_descriptions.append(f"{bonus_val} ({bonus_desc})")

        result.total_damage = max(1, current_total_damage) # Minimum 1 damage dealt on a hit

        damage_log_str = f"Base: {base_damage}"
        if damage_bonus_descriptions:
            damage_log_str += " + " + " + ".join(damage_bonus_descriptions)

        crit_mult_str = f"(x{attack.get_crit_multiplier()} critical)" if result.is_critical_hit else ""
        self.log.add_entry(f"  Damage Roll: {result.total_damage} {crit_mult_str} [{damage_log_str}]")

        # Apply damage to target (handles DR, resistances, HP update, conditions)
        result.damage_taken = target.take_damage(result.total_damage, attack.damage_type.value)

        if result.damage_taken < result.total_damage:
            self.log.add_entry(f"  Damage reduced to {result.damage_taken} by DR/resistances/etc.")

        self.log.add_entry(f"  {target.name} takes {result.damage_taken} damage.")
        self.log.add_entry(f"  {target.name} HP: {target.current_hp}/{target.max_hp}")

        # Check if target is defeated or other status changes
        if target.is_dead():
            self.log.add_entry(f"  {target.name} is DEAD!")
        elif target.is_dying():
            self.log.add_entry(f"  {target.name} is DYING!")
        elif target.is_disabled(): # current_hp == 0
            self.log.add_entry(f"  {target.name} is DISABLED (at 0 HP)!")
        elif target.has_condition("unconscious"): # May become unconscious from non-HP reasons too
             self.log.add_entry(f"  {target.name} falls UNCONSCIOUS!")

        return result

    def get_valid_targets(self, attacker: Combatant) -> List[Combatant]:
        """Get list of valid targets for an attacker (not self, not dead/unconscious)."""
        # Simple implementation: all other living combatants are valid targets.
        # TODO: Implement factions/teams for more complex target selection.
        # TODO: Consider reach/range for actual valid targets.
        valid_targets = []
        for c in self.combatants:
            if c is not attacker and c.current_hp > 0 and \
               not c.is_dead() and not c.has_condition("unconscious"):
                valid_targets.append(c)
        return valid_targets

    def is_combat_over(self) -> bool:
        """Check if combat should end."""
        # Get all combatants still capable of fighting
        active_combatants = [c for c in self.combatants if c.current_hp > 0 and \
                             not c.is_dead() and not c.has_condition("unconscious") and \
                             not c.has_condition("helpless")] # Helpless might also end combat for a side

        if not active_combatants: # Everyone is down
            self.log.add_entry("All combatants are defeated or incapacitated.")
            return True

        if len(active_combatants) <= 1: # Only one or zero combatants left standing
            if active_combatants:
                 self.log.add_entry(f"Only {active_combatants[0].name} remains.")
            return True

        # Check factions: if all remaining active combatants are on the same "side"
        # Requires combatants to have a 'is_pc' or 'faction_id' attribute.

        pcs_present = any(c.is_pc for c in active_combatants)
        non_pcs_present = any(not c.is_pc for c in active_combatants)

        if pcs_present:
            # If PCs are present, combat ends if all PCs are down or all non-PCs are down.
            if not non_pcs_present: # No NPCs left
                self.log.add_entry("All hostile NPCs are defeated.")
                return True
            # The case of "All PCs are defeated" is already covered by len(active_combatants) <=1
            # if the remaining combatants are all non-PCs, or by active_combatants being empty.
            # Let's refine this: if only non-PCs remain, and there were PCs initially, combat ends for PCs.
            if not any(c.is_pc for c in active_combatants) and any(c.is_pc for c in self.combatants):
                 self.log.add_entry("All PCs are defeated.")
                 return True
        else:
            # No PCs present in the active combatants list (e.g., monster-only battle)
            # Combat ends if only one monster (or fewer) remains.
            # This is already covered by the `len(active_combatants) <= 1` check earlier.
            # So, if we reach here and there are no PCs, it implies len(active_combatants) > 1.
            # In a monster-only battle, this means combat continues.
            # The earlier check `if len(active_combatants) <= 1:` handles the end condition.
            pass # Implicitly, if no PCs and more than 1 monster, combat continues.

        return False # Combat continues

    def end_combat(self):
        """End the current combat encounter."""
        if not self.combat_active: # Already ended
            return

        self.combat_active = False
        self.log.add_entry("\n=== COMBAT ENDS ===")

        # Display final status of all combatants
        self.log.add_entry("Final Status:")
        for combatant in self.combatants:
            status = "OK"
            if combatant.is_dead(): status = "DEAD"
            elif combatant.has_condition("unconscious"): status = "UNCONSCIOUS"
            elif combatant.is_dying(): status = "DYING"
            elif combatant.is_disabled(): status = "DISABLED (0 HP)"

            self.log.add_entry(f"  {combatant.name}: {combatant.current_hp}/{combatant.max_hp} HP ({status})")

        # Could add more summary info here (rounds taken, etc.)
        self.log.add_entry(f"Combat lasted {self.current_round-1 if not self.is_surprise_round else self.current_round} full round(s).")
        if self.is_surprise_round : self.log.add_entry("(Ended before normal rounds fully completed or during surprise)")

        # Reset for next potential combat, if any (clear lists, etc.)
        # This might be better handled by creating a new CombatEngine instance.
        # For now, let's clear some state.
        # self.combatants.clear() # Or reset them
        # self.initiative_order.clear()
        # self.current_round = 0
        # self.current_turn_index = 0
        # self.is_surprise_round = False
        # self.log.clear() # Optional: clear log or keep it for review.
        # The original main loop creates a new CombatEngine, so this reset is not strictly needed here.
