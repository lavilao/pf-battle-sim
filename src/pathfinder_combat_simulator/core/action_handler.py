import random
from typing import (
    List,
    Optional,
    Tuple,
)  # Added for full context from original file

from .attack_result import AttackResult

# Assuming these are the correct relative imports for core components
from .combat_engine import CombatEngine
from .combatant import Combatant
from .enums import ActionType, AttackType


class ActionHandler:
    """Handles different types of actions a combatant can take
    Implements action economy from Part 3 of specification.
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
            if not getattr(combatant, "is_aware_in_surprise_round", True):
                self.combat_engine.log.add_entry(
                    f"{combatant.name} cannot act in surprise round (unaware)."
                )
                return False
            if action_type == ActionType.FULL_ROUND:
                self.combat_engine.log.add_entry(
                    f"{combatant.name} cannot take a full-round action in a surprise round."
                )
                return False

        # Conditions preventing most actions
        if (
            combatant.has_condition("stunned")
            or combatant.has_condition("paralyzed")
            or combatant.has_condition("helpless")
            or combatant.has_condition("unconscious")
            or combatant.is_dead()
            or combatant.is_dying()
        ):  # Dying combatants are unconscious
            # Log entry was slightly different in source, ensuring it matches:
            conditions_list = [
                c
                for c in [
                    "stunned",
                    "paralyzed",
                    "helpless",
                    "unconscious",
                    "dead",
                    "dying",
                ]
                if (c == "dead" and combatant.is_dead())
                or (c == "dying" and combatant.is_dying())
                or (combatant.has_condition(c) and c not in ["dead", "dying"])
            ]
            if conditions_list:
                self.combat_engine.log.add_entry(
                    f"{combatant.name} cannot take actions due to condition ({conditions_list[0]})."
                )
            return False

        # Nauseated: Only a single move action
        if combatant.has_condition("nauseated"):
            if action_type != ActionType.MOVE:
                self.combat_engine.log.add_entry(
                    f"{combatant.name} is nauseated and can only take a move action."
                )
                return False
            # TODO: Need to track if the move action was already taken this turn if nauseated.
            # For now, this check is per-action attempt.

        # Disabled: Single move or standard action. No full-round.
        if combatant.is_disabled():  # at 0 HP
            if action_type == ActionType.FULL_ROUND:
                self.combat_engine.log.add_entry(
                    f"{combatant.name} is disabled and cannot take a full-round action."
                )
                return False
            # TODO: Track if standard/move already taken this turn if disabled.
            # If taking a standard action while disabled (not healing), take 1 damage.
            if action_type == ActionType.STANDARD:
                # This logic should be after the action, not in can_take_action
                pass

        # TODO: Add checks for Frightened (must flee), Panicked (must flee/cower), Confused (roll behavior)
        # These often dictate the *type* of action rather than preventing all actions.

        return True

    def take_attack_action(
        self, attacker: Combatant, target: Combatant, attack_index: int = 0
    ) -> Optional[AttackResult]:
        """Take a standard attack action"""
        if not self.can_take_action(attacker, ActionType.STANDARD):
            return None

        if attacker.is_disabled():  # Taking a standard action while disabled
            self.combat_engine.log.add_entry(
                f"{attacker.name} is disabled and takes 1 damage for performing a standard action."
            )
            attacker.take_damage(1, "untyped")  # This damage might make them dying/dead
            if not self.can_take_action(
                attacker, ActionType.STANDARD
            ):  # Re-check if they are now unable to act
                return None

        if not attacker.attacks or attack_index >= len(
            attacker.attacks
        ):  # Check if list is empty
            self.combat_engine.log.add_entry(
                f"{attacker.name} has no attack at index {attack_index}"
            )
            return None

        attack = attacker.attacks[attack_index]

        # Ranged attacks provoke AoOs
        if attack.attack_type == AttackType.RANGED:
            # Check for AoO before the attack proceeds
            # Pass 'ranged attack' as the provoking action description
            self.combat_engine.trigger_attacks_of_opportunity(
                attacker, "making a ranged attack"
            )
            # If the attacker was downed by an AoO, they can't complete the action
            if (
                attacker.is_dead()
                or attacker.has_condition("unconscious")
                or attacker.has_condition("stunned")
            ):
                self.combat_engine.log.add_entry(
                    f"{attacker.name} cannot complete ranged attack due to AoO effects."
                )
                return None  # Attacker downed/disabled

        return self.combat_engine.make_attack(attacker, target, attack)

    def take_full_attack_action(
        self, attacker: Combatant, target: Combatant, attack_index: int = 0
    ) -> List[AttackResult]:  # Added default for attack_index
        """Take a full-attack action (all available attacks)"""
        if not self.can_take_action(attacker, ActionType.FULL_ROUND):
            return []

        if not attacker.attacks or attack_index >= len(
            attacker.attacks
        ):  # Check if list is empty
            self.combat_engine.log.add_entry(
                f"{attacker.name} has no attack at index {attack_index}"
            )
            return []

        results = []
        attack = attacker.attacks[
            attack_index
        ]  # This uses the attack_index for the *primary* sequence

        # Calculate number of attacks based on BAB
        num_attacks = (attacker.base_attack_bonus // 5) + 1

        self.combat_engine.log.add_entry(f"{attacker.name} takes a full-attack action")

        for i in range(num_attacks):
            # Original code checks: attacker.base_attack_bonus - (i * 5) > 0
            # This is implicitly handled by how get_attack_bonus modifies BAB for iterative attacks.
            # Let's ensure make_attack correctly gets the BAB for this iterative attack.
            # The attack_number parameter in make_attack should handle this.
            # No, make_attack doesn't reduce BAB, get_attack_bonus does.
            # So the check here is still relevant if get_attack_bonus doesn't return a massively negative number.
            current_iterative_bab = attacker.base_attack_bonus - (i * 5)
            if (
                current_iterative_bab < 0 and i > 0
            ):  # Only allow negative BAB if it's the first attack and BAB is negative
                break

            result = self.combat_engine.make_attack(
                attacker, target, attack, is_full_attack=True, attack_number=i
            )
            if result:  # make_attack can return None or AttackResult
                results.append(result)

            # If target is downed, typically stop attacking or switch (not implemented here)
            if target.is_dead() or target.has_condition("unconscious"):
                break

        return results

    def take_stabilize_other_action(self, actor: Combatant, target: Combatant) -> bool:
        """Use Heal skill (DC 15) to stabilize a dying target."""
        if not self.can_take_action(actor, ActionType.STANDARD):
            self.combat_engine.log.add_entry(
                f"{actor.name} cannot take a standard action to stabilize."
            )
            return False

        if not target.is_dying():
            self.combat_engine.log.add_entry(f"{target.name} is not dying.")
            return False

        heal_skill_modifier = actor.skills.get("Heal", 0)
        roll = random.randint(1, 20)

        self.combat_engine.trigger_attacks_of_opportunity(
            actor, "stabilizing another character"
        )
        if (
            actor.is_dead()
            or actor.has_condition("unconscious")
            or actor.has_condition("stunned")
        ):
            self.combat_engine.log.add_entry(
                f"{actor.name} cannot complete stabilization due to AoO effects."
            )
            return False

        self.combat_engine.log.add_entry(
            f"{actor.name} attempts to stabilize {target.name} with a Heal check."
        )
        self.combat_engine.log.add_entry(
            f"  Heal check roll: {roll} + {heal_skill_modifier} = {roll + heal_skill_modifier} vs DC 15"
        )

        if roll + heal_skill_modifier >= 15:
            target.add_condition("stable")
            target.remove_condition("dying")
            self.combat_engine.log.add_entry(
                f"{target.name} has been stabilized by {actor.name}!"
            )
            return True
        else:
            self.combat_engine.log.add_entry(
                f"{actor.name} failed to stabilize {target.name}."
            )
            return False

    def take_cast_spell_action(
        self, caster: Combatant, spell_name: str, target: Optional[Combatant] = None
    ):  # spell_level removed as per original
        """Placeholder for casting a spell. Most spells provoke AoOs."""
        if not self.can_take_action(caster, ActionType.STANDARD):
            self.combat_engine.log.add_entry(
                f"{caster.name} cannot take a standard action to cast a spell."
            )
            return

        self.combat_engine.trigger_attacks_of_opportunity(
            caster, f"casting {spell_name}"
        )
        if (
            caster.is_dead()
            or caster.has_condition("unconscious")
            or caster.has_condition("stunned")
        ):
            self.combat_engine.log.add_entry(
                f"{caster.name} cannot complete casting {spell_name} due to AoO effects."
            )
            return

        self.combat_engine.log.add_entry(
            f"{caster.name} casts {spell_name}"
            + (f" on {target.name}" if target else "")
            + ". (Spell effects not implemented yet)."
        )

    def take_aid_another_action(
        self,
        actor: Combatant,
        target_creature_to_hinder: Combatant,
        ally_to_aid: Combatant,
        aid_type: str = "attack",
    ) -> bool:
        if not self.can_take_action(actor, ActionType.STANDARD):
            self.combat_engine.log.add_entry(
                f"{actor.name} cannot take a standard action for Aid Another."
            )
            return False

        primary_attack = None
        attack_bonus = actor.base_attack_bonus
        if actor.attacks:
            for attack_obj in actor.attacks:  # renamed attack to attack_obj
                if (
                    attack_obj.attack_type == AttackType.MELEE
                    or attack_obj.attack_type == AttackType.NATURAL
                ):
                    primary_attack = attack_obj
                    break

        if primary_attack:
            attack_bonus = actor.get_attack_bonus(primary_attack)
        else:
            attack_bonus = (
                actor.base_attack_bonus
                + actor.ability_scores.get_modifier("str")
                + actor.get_size_modifier()
            )

        roll = random.randint(1, 20)
        total_attack_roll = roll + attack_bonus

        self.combat_engine.log.add_entry(
            f"{actor.name} attempts Aid Another (for {ally_to_aid.name}'s {aid_type}) against {target_creature_to_hinder.name}."
        )
        self.combat_engine.log.add_entry(
            f"  Aid Another roll: {roll} + {attack_bonus} = {total_attack_roll} vs AC 10."
        )

        if total_attack_roll >= 10:
            self.combat_engine.log.add_entry("  Aid Another successful!")
            if aid_type == "attack":
                self.combat_engine.log.add_entry(
                    f"  {ally_to_aid.name} will get +2 on their next attack roll against {target_creature_to_hinder.name} before {actor.name}'s next turn."
                )
            else:
                self.combat_engine.log.add_entry(
                    f"  {ally_to_aid.name} will get +2 to AC against {target_creature_to_hinder.name}'s next attack before {actor.name}'s next turn."
                )
            return True
        else:
            self.combat_engine.log.add_entry("  Aid Another failed.")
            return False

    def take_total_defense_action(self, combatant: Combatant) -> bool:
        if not self.can_take_action(combatant, ActionType.STANDARD):
            self.combat_engine.log.add_entry(
                f"{combatant.name} cannot take a standard action for Total Defense."
            )
            return False

        self.combat_engine.log.add_entry(
            f"{combatant.name} takes the Total Defense action."
        )
        self.combat_engine.log.add_entry(
            "  Gains +4 dodge bonus to AC until their next turn (effect not fully implemented)."
        )
        self.combat_engine.log.add_entry(
            "  Cannot make Attacks of Opportunity until their next turn (effect not fully implemented)."
        )
        return True

    def take_stand_up_action(self, combatant: Combatant) -> bool:
        if not combatant.has_condition("prone"):
            self.combat_engine.log.add_entry(f"{combatant.name} is not prone.")
            return False

        if not self.can_take_action(combatant, ActionType.MOVE):
            self.combat_engine.log.add_entry(
                f"{combatant.name} cannot take a move action to stand up."
            )
            return False

        self.combat_engine.log.add_entry(
            f"{combatant.name} attempts to stand up from prone."
        )
        self.combat_engine.trigger_attacks_of_opportunity(
            combatant, "standing up from prone"
        )
        if (
            combatant.is_dead()
            or combatant.has_condition("unconscious")
            or combatant.has_condition("stunned")
        ):
            self.combat_engine.log.add_entry(
                f"{combatant.name} cannot complete standing up due to AoO effects."
            )
            return False

        combatant.remove_condition("prone")
        self.combat_engine.log.add_entry(f"{combatant.name} stands up.")
        return True

    def take_drop_prone_action(self, combatant: Combatant) -> bool:
        if combatant.has_condition("prone"):
            self.combat_engine.log.add_entry(f"{combatant.name} is already prone.")
            return False

        self.combat_engine.log.add_entry(f"{combatant.name} drops prone.")
        combatant.add_condition("prone")
        return True

    def take_move_action(
        self, combatant: Combatant, distance: int = 0, provokes_aoo: bool = True
    ):  # Added typehint for distance
        if not self.can_take_action(combatant, ActionType.MOVE):
            return False  # Return a bool as per original

        if provokes_aoo:
            self.combat_engine.trigger_attacks_of_opportunity(combatant, "moving")
            if (
                combatant.is_dead()
                or combatant.has_condition("unconscious")
                or combatant.has_condition("stunned")
            ):
                self.combat_engine.log.add_entry(
                    f"{combatant.name} cannot complete movement due to AoO effects."
                )
                return False  # Return a bool

        max_distance = combatant.base_speed
        if (
            distance <= max_distance
        ):  # Distance can be 0 for taking a move action to do something else
            self.combat_engine.log.add_entry(f"{combatant.name} moves {distance} feet.")
            combatant.has_moved_this_turn = True
            return True  # Return a bool
        else:
            self.combat_engine.log.add_entry(
                f"{combatant.name} cannot move {distance} feet (max: {max_distance})."
            )
            return False  # Return a bool

    def take_draw_sheathe_weapon_action(
        self, combatant: Combatant, weapon_name: str, action: str = "draw"
    ) -> bool:
        if not self.can_take_action(combatant, ActionType.MOVE):
            self.combat_engine.log.add_entry(
                f"{combatant.name} cannot take a move action to {action} {weapon_name}."
            )
            return False

        log_msg_action = "draws" if action == "draw" else "sheathes"
        self.combat_engine.log.add_entry(
            f"{combatant.name} attempts to {log_msg_action} {weapon_name}."
        )

        if action == "sheathe":
            self.combat_engine.trigger_attacks_of_opportunity(
                combatant, f"sheathing {weapon_name}"
            )
            if (
                combatant.is_dead()
                or combatant.has_condition("unconscious")
                or combatant.has_condition("stunned")
            ):
                self.combat_engine.log.add_entry(
                    f"{combatant.name} cannot complete sheathing {weapon_name} due to AoO effects."
                )
                return False

        self.combat_engine.log.add_entry(
            f"{combatant.name} successfully {log_msg_action} {weapon_name} (inventory not implemented)."
        )
        combatant.has_moved_this_turn = True
        return True

    def take_charge_action(
        self, attacker: Combatant, target: Combatant, charge_attack_index: int = 0
    ) -> Optional[AttackResult]:
        if not self.can_take_action(attacker, ActionType.FULL_ROUND):
            self.combat_engine.log.add_entry(
                f"{attacker.name} cannot take a full-round action to Charge."
            )
            return None

        if (
            not attacker.attacks
            or charge_attack_index >= len(attacker.attacks)
            or attacker.attacks[charge_attack_index].attack_type == AttackType.RANGED
        ):
            self.combat_engine.log.add_entry(
                f"{attacker.name} cannot charge with the selected attack (must be melee)."
            )
            return None

        charge_attack = attacker.attacks[charge_attack_index]
        charge_distance = attacker.base_speed
        if charge_distance < 10:  # Pathfiner: must move at least 10ft.
            self.combat_engine.log.add_entry(
                f"{attacker.name} cannot charge: must move at least 10 feet."
            )
            return None

        self.combat_engine.log.add_entry(
            f"{attacker.name} charges {target.name} (movement of {charge_distance}ft not fully simulated)."
        )
        attacker.has_moved_this_turn = True
        self.combat_engine.log.add_entry(
            f"  {attacker.name} takes -2 AC until next turn (effect not fully implemented)."
        )
        self.combat_engine.log.add_entry(
            f"  Charging with {charge_attack.name} (+2 attack bonus)."
        )

        # The +2 charge bonus should be passed to make_attack or handled by get_attack_bonus
        # Assuming make_attack can take additional bonuses for now
        attack_result = self.combat_engine.make_attack(
            attacker,
            target,
            charge_attack,
            is_full_attack=False,
            attack_number=0,
            additional_attack_bonus_list=[(2, "charge")],
        )
        return attack_result

    def take_withdraw_action(self, combatant: Combatant, distance: int) -> bool:
        if not self.can_take_action(combatant, ActionType.FULL_ROUND):
            self.combat_engine.log.add_entry(
                f"{combatant.name} cannot take a full-round action to Withdraw."
            )
            return False

        max_distance = combatant.base_speed * 2
        if distance > max_distance:
            self.combat_engine.log.add_entry(
                f"{combatant.name} cannot withdraw {distance}ft, max is {max_distance}ft."
            )
            return False

        self.combat_engine.log.add_entry(f"{combatant.name} withdraws {distance}ft.")
        self.combat_engine.log.add_entry(
            "  Movement from starting square does not provoke from visible enemies (visibility not fully simulated)."
        )
        combatant.has_moved_this_turn = True
        return True

    def take_5_foot_step_action(
        self, combatant: Combatant, direction: str = "any"
    ) -> bool:
        if combatant.has_moved_this_turn:
            self.combat_engine.log.add_entry(
                f"{combatant.name} cannot take a 5-foot step: already moved this turn."
            )
            return False

        self.combat_engine.log.add_entry(
            f"{combatant.name} takes a 5-foot step ({direction})."
        )
        combatant.has_moved_this_turn = True
        return True

    def _perform_combat_maneuver_check(
        self,
        attacker: Combatant,
        target: Combatant,
        maneuver_name: str,
        additional_bonus: int = 0,
        provokes: bool = True,
    ) -> Optional[Tuple[int, int, int]]:
        if provokes:
            self.combat_engine.trigger_attacks_of_opportunity(
                attacker, f"attempting {maneuver_name}"
            )
            if (
                attacker.is_dead()
                or attacker.has_condition("unconscious")
                or attacker.has_condition("stunned")
            ):
                self.combat_engine.log.add_entry(
                    f"{attacker.name} cannot complete {maneuver_name} due to AoO effects."
                )
                return None

        cmb = attacker.calculate_cmb() + additional_bonus
        cmd = target.calculate_cmd()
        roll = random.randint(1, 20)
        total_maneuver_roll = roll + cmb

        self.combat_engine.log.add_entry(
            f"{attacker.name} attempts {maneuver_name} against {target.name}."
        )
        self.combat_engine.log.add_entry(
            f"  CMB Check: {roll} (d20) + {cmb - additional_bonus} (CMB) + {additional_bonus} (misc) = {total_maneuver_roll} vs CMD {cmd}."
        )
        return roll, total_maneuver_roll, cmd

    def take_bull_rush_action(
        self, attacker: Combatant, target: Combatant, as_part_of_charge: bool = False
    ) -> bool:
        action_type_check = ActionType.STANDARD
        if as_part_of_charge:
            pass
        elif not self.can_take_action(attacker, action_type_check):
            self.combat_engine.log.add_entry(
                f"{attacker.name} cannot take a {action_type_check.value} action for Bull Rush."
            )
            return False

        provokes_aoo = "Improved Bull Rush" not in attacker.feats
        charge_bonus = 2 if as_part_of_charge else 0
        if as_part_of_charge:
            self.combat_engine.log.add_entry("  Gains +2 bonus from charging.")

        maneuver_result = self._perform_combat_maneuver_check(
            attacker,
            target,
            "Bull Rush",
            additional_bonus=charge_bonus,
            provokes=provokes_aoo,
        )
        if not maneuver_result:
            return False
        d20_roll, total_maneuver_roll, target_cmd = maneuver_result

        if d20_roll == 1:
            self.combat_engine.log.add_entry("  Bull Rush failed (natural 1).")
            return False

        if total_maneuver_roll >= target_cmd or d20_roll == 20:
            self.combat_engine.log.add_entry("  Bull Rush successful!")
            push_distance = (
                5 + ((total_maneuver_roll - target_cmd) // 5) * 5
                if (total_maneuver_roll - target_cmd) >= 5
                else 5
            )
            self.combat_engine.log.add_entry(
                f"  {target.name} is pushed back {push_distance} feet."
            )
            self.combat_engine.log.add_entry(
                f"  {attacker.name} can move with {target.name} (movement not simulated)."
            )
            attacker.has_moved_this_turn = True
            return True
        else:
            self.combat_engine.log.add_entry("  Bull Rush failed.")
            return False

    def take_trip_action(self, attacker: Combatant, target: Combatant) -> bool:
        if not self.can_take_action(attacker, ActionType.STANDARD):
            self.combat_engine.log.add_entry(
                f"{attacker.name} cannot take a standard action for Trip."
            )
            return False
        provokes_aoo = "Improved Trip" not in attacker.feats
        maneuver_result = self._perform_combat_maneuver_check(
            attacker, target, "Trip", provokes=provokes_aoo
        )
        if not maneuver_result:
            return False
        d20_roll, total_maneuver_roll, target_cmd = maneuver_result

        if d20_roll == 1:
            self.combat_engine.log.add_entry("  Trip failed (natural 1).")
            return False
        if total_maneuver_roll >= target_cmd or d20_roll == 20:
            self.combat_engine.log.add_entry("  Trip successful!")
            self.combat_engine.log.add_entry(f"  {target.name} is knocked prone.")
            target.add_condition("prone")
            return True
        else:
            self.combat_engine.log.add_entry("  Trip failed.")
            if target_cmd - total_maneuver_roll >= 10:
                self.combat_engine.log.add_entry(
                    f"  {attacker.name} is knocked prone due to failing badly!"
                )
                attacker.add_condition("prone")
            return False

    def take_disarm_action(self, attacker: Combatant, target: Combatant) -> bool:
        if not self.can_take_action(attacker, ActionType.STANDARD):
            self.combat_engine.log.add_entry(
                f"{attacker.name} cannot take a standard action for Disarm."
            )
            return False
        provokes_aoo = "Improved Disarm" not in attacker.feats
        is_unarmed_attempt = not attacker.attacks
        disarm_penalty = -4 if is_unarmed_attempt else 0
        if is_unarmed_attempt:
            self.combat_engine.log.add_entry(
                "  Attacker is unarmed, takes -4 penalty on Disarm attempt."
            )

        maneuver_result = self._perform_combat_maneuver_check(
            attacker,
            target,
            "Disarm",
            additional_bonus=disarm_penalty,
            provokes=provokes_aoo,
        )
        if not maneuver_result:
            return False
        d20_roll, total_maneuver_roll, target_cmd = maneuver_result

        if d20_roll == 1:
            self.combat_engine.log.add_entry("  Disarm failed (natural 1).")
            return False
        if total_maneuver_roll >= target_cmd or d20_roll == 20:
            self.combat_engine.log.add_entry("  Disarm successful!")
            items_dropped = 2 if total_maneuver_roll - target_cmd >= 10 else 1
            self.combat_engine.log.add_entry(
                f"  {target.name} drops {items_dropped} item{'s' if items_dropped > 1 else ''} (item system not implemented)."
            )
            if is_unarmed_attempt and items_dropped > 0:
                self.combat_engine.log.add_entry(
                    f"  {attacker.name} (unarmed) may automatically pick up one dropped item (not simulated)."
                )
            return True
        else:
            self.combat_engine.log.add_entry("  Disarm failed.")
            if target_cmd - total_maneuver_roll >= 10:
                self.combat_engine.log.add_entry(
                    f"  {attacker.name} drops their weapon due to failing badly (weapon system not implemented)!"
                )
            return False

    def take_sunder_action(
        self, attacker: Combatant, target: Combatant, target_item_name: str = "weapon"
    ) -> bool:
        if not self.can_take_action(attacker, ActionType.STANDARD):
            self.combat_engine.log.add_entry(
                f"{attacker.name} cannot take a standard action for Sunder."
            )
            return False
        provokes_aoo = "Improved Sunder" not in attacker.feats
        maneuver_result = self._perform_combat_maneuver_check(
            attacker, target, f"Sunder ({target_item_name})", provokes=provokes_aoo
        )
        if not maneuver_result:
            return False
        d20_roll, total_maneuver_roll, target_cmd = maneuver_result

        if d20_roll == 1:
            self.combat_engine.log.add_entry(
                f"  Sunder attempt against {target_item_name} failed (natural 1)."
            )
            return False
        if total_maneuver_roll >= target_cmd or d20_roll == 20:
            self.combat_engine.log.add_entry(
                f"  Sunder attempt against {target_item_name} successful (hit the item)!"
            )
            self.combat_engine.log.add_entry(
                f"  Damage would be dealt to {target_item_name} (item HP/hardness/damage not implemented)."
            )
            return True
        else:
            self.combat_engine.log.add_entry(
                f"  Sunder attempt against {target_item_name} failed (missed the item)."
            )
            return False
