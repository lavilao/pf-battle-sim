import { Combatant } from "./combatant.ts";
import { ActionType, AttackType } from "./enums.ts";
import { Attack } from "./attack.ts";
import { AttackResult } from "./attackResult.ts";
import { rollDiceString } from "./utils.ts"; // For d20 rolls mainly

// Placeholder for CombatEngine - will be replaced with actual import
interface CombatEngineInterface {
  combat_active: boolean;
  is_surprise_round: boolean;
  get_current_combatant(): Combatant | null;
  log: { addEntry: (message: string) => void }; // Placeholder for CombatLog
  make_attack(
    attacker: Combatant,
    target: Combatant,
    attack: Attack,
    is_full_attack?: boolean,
    attack_number?: number,
    additional_attack_bonus_list?: Array<[number, string]>
  ): AttackResult | null;
  trigger_attacks_of_opportunity(offender: Combatant, provoking_action_description: string): void;
}


export class ActionHandler {
  private combatEngine: CombatEngineInterface;

  constructor(combatEngine: CombatEngineInterface) {
    this.combatEngine = combatEngine;
  }

  private d20(): number {
    return rollDiceString("1d20");
  }

  canTakeAction(combatant: Combatant, actionType: ActionType): boolean {
    if (!this.combatEngine.combat_active) {
      return false;
    }

    const currentCombatant = this.combatEngine.get_current_combatant();
    if (currentCombatant !== combatant) {
      return false;
    }

    if (this.combatEngine.is_surprise_round) {
      // In surprise round, only standard OR move actions allowed for aware combatants
      // Assuming a property `isAwareInSurpriseRound` or similar on Combatant if needed
      // For now, let's assume this logic is handled by who gets a turn in surprise round.
      // The Python code had: if not getattr(combatant, 'is_aware_in_surprise_round', True):
      if ((combatant as any).is_aware_in_surprise_round === false) { // Temporary check
          this.combatEngine.log.addEntry(`${combatant.name} cannot act in surprise round (unaware).`);
          return false;
      }
      if (actionType === ActionType.FULL_ROUND) {
        this.combatEngine.log.addEntry(`${combatant.name} cannot take a full-round action in a surprise round.`);
        return false;
      }
    }

    const conditionsPreventingAction = ['stunned', 'paralyzed', 'helpless', 'unconscious'];
    if (combatant.isDead() || combatant.isDying()) conditionsPreventingAction.push(combatant.isDead() ? 'dead' : 'dying');

    for (const cond of conditionsPreventingAction) {
      if (cond === 'dead' && combatant.isDead()) {
        this.combatEngine.log.addEntry(`${combatant.name} cannot take actions due to condition (dead).`);
        return false;
      }
      if (cond === 'dying' && combatant.isDying()) {
        this.combatEngine.log.addEntry(`${combatant.name} cannot take actions due to condition (dying).`);
        return false;
      }
      if (combatant.hasCondition(cond)) {
        this.combatEngine.log.addEntry(`${combatant.name} cannot take actions due to condition (${cond}).`);
        return false;
      }
    }

    if (combatant.hasCondition("nauseated")) {
      if (actionType !== ActionType.MOVE) {
        this.combatEngine.log.addEntry(`${combatant.name} is nauseated and can only take a move action.`);
        return false;
      }
      // TODO: Track if move action already taken this turn if nauseated.
    }

    if (combatant.isDisabled()) { // at 0 HP
      if (actionType === ActionType.FULL_ROUND) {
        this.combatEngine.log.addEntry(`${combatant.name} is disabled and cannot take a full-round action.`);
        return false;
      }
      // Further logic for damage after action is in specific action methods.
    }
    return true;
  }

  takeAttackAction(attacker: Combatant, target: Combatant, attackIndex: number = 0): AttackResult | null {
    if (!this.canTakeAction(attacker, ActionType.STANDARD)) {
      return null;
    }

    if (attacker.isDisabled()) {
      this.combatEngine.log.addEntry(`${attacker.name} is disabled and takes 1 damage for performing a standard action.`);
      attacker.takeDamage(1, "untyped");
      if (!this.canTakeAction(attacker, ActionType.STANDARD)) { // Re-check
        return null;
      }
    }

    if (!attacker.attacks || attackIndex >= attacker.attacks.length) {
      this.combatEngine.log.addEntry(`${attacker.name} has no attack at index ${attackIndex}.`);
      return null;
    }
    const attack = attacker.attacks[attackIndex];

    if (attack.attack_type === AttackType.RANGED) {
      this.combatEngine.trigger_attacks_of_opportunity(attacker, "making a ranged attack");
      if (attacker.isDead() || attacker.hasCondition("unconscious") || attacker.hasCondition("stunned")) {
        this.combatEngine.log.addEntry(`${attacker.name} cannot complete ranged attack due to AoO effects.`);
        return null;
      }
    }
    return this.combatEngine.make_attack(attacker, target, attack);
  }

  takeFullAttackAction(attacker: Combatant, target: Combatant, primaryAttackIndex: number = 0): AttackResult[] {
    if (!this.canTakeAction(attacker, ActionType.FULL_ROUND)) {
      return [];
    }
    if (!attacker.attacks || primaryAttackIndex >= attacker.attacks.length) {
        this.combatEngine.log.addEntry(`${attacker.name} has no primary attack for full-attack at index ${primaryAttackIndex}.`);
        return [];
    }
    const primaryAttack = attacker.attacks[primaryAttackIndex];
    const results: AttackResult[] = [];
    const numAttacks = Math.floor(attacker.base_attack_bonus / 5) + 1;

    this.combatEngine.log.addEntry(`${attacker.name} takes a full-attack action with ${primaryAttack.name} sequence.`);

    for (let i = 0; i < numAttacks; i++) {
      const currentIterativeBab = attacker.base_attack_bonus - (i * 5);
      // In Pathfinder, you always get at least one attack in a full attack, even if BAB is <=0.
      // Iterative attacks stop when BAB penalty makes it too low (e.g. -6 for 2nd attack if BAB is 0).
      // The get_attack_bonus in Combatant already handles this by applying the -5 per iterative.
      // So, we just loop through num_attacks.
      // However, the Python code had: if current_iterative_bab < 0 and i > 0 : break
      // This means if BAB is 0, you get one attack (i=0, bab=0). Second attack (i=1, bab=-5) is skipped. Correct.
      // If BAB is 4, one attack (i=0, bab=4). Second attack (i=1, bab=-1) is skipped. Correct.
      // If BAB is 6, first (i=0, bab=6), second (i=1, bab=1). Third (i=2, bab=-4) skipped. Correct.
      if (attacker.base_attack_bonus - (i * 5) < 1 && i > 0 && attacker.base_attack_bonus > 0) {
          // If your BAB is 1-5, you get 1 attack. Iterative would be BAB-5, so <1.
          // If your BAB is 0 or negative, you still get 1 attack. This condition handles not taking iteratives if BAB is low.
          // The condition `current_iterative_bab < 0 and i > 0` (from python) is slightly different
          // Let's use: if current_iterative_bab would be too low for an iterative.
          // A BAB of +0 means one attack. A BAB of -1 means one attack.
          // Iterative attacks are only gained for BAB +6, +11, +16.
          // So if i > 0 (it's an iterative) and the BAB for this iterative is < 1, break.
          // This implies (attacker.base_attack_bonus - (i*5)) < 1.
          if (i > 0 && (attacker.base_attack_bonus - (i*5)) < 1 && !(attacker.base_attack_bonus < 1 && i===0) ) break;
      }


      const result = this.combatEngine.make_attack(attacker, target, primaryAttack, true, i);
      if (result) {
        results.push(result);
      }
      if (target.isDead() || target.hasCondition("unconscious")) {
        this.combatEngine.log.addEntry(`${target.name} is downed. ${attacker.name} stops full attack.`);
        break;
      }
      if (attacker.isDead() || attacker.hasCondition("unconscious") || attacker.hasCondition("stunned")){
        this.combatEngine.log.addEntry(`${attacker.name} is downed and cannot continue full attack.`);
        break;
      }
    }
    return results;
  }

  takeStabilizeOtherAction(actor: Combatant, target: Combatant): boolean {
    if (!this.canTakeAction(actor, ActionType.STANDARD)) {
        this.combatEngine.log.addEntry(`${actor.name} cannot take a standard action to stabilize.`);
        return false;
    }
    if (actor.isDisabled()) { // Taking standard action while disabled
        this.combatEngine.log.addEntry(`${actor.name} is disabled and takes 1 damage for attempting to stabilize another.`);
        actor.takeDamage(1, "untyped");
        if (!this.canTakeAction(actor, ActionType.STANDARD)) return false;
    }
    if (!target.isDying()) {
        this.combatEngine.log.addEntry(`${target.name} is not dying.`);
        return false;
    }

    this.combatEngine.trigger_attacks_of_opportunity(actor, "stabilizing another character");
    if (actor.isDead() || actor.hasCondition("unconscious") || actor.hasCondition("stunned")) {
        this.combatEngine.log.addEntry(`${actor.name} cannot complete stabilization due to AoO effects.`);
        return false;
    }

    const healSkillModifier = actor.skills["Heal"] ?? actor.ability_scores.getModifier("wisdom"); // Default to Wis if no Heal skill rank
    const roll = this.d20();
    this.combatEngine.log.addEntry(`${actor.name} attempts to stabilize ${target.name} with a Heal check.`);
    this.combatEngine.log.addEntry(`  Heal check roll: ${roll} + ${healSkillModifier} = ${roll + healSkillModifier} vs DC 15`);

    if (roll === 1) { // Natural 1 always fails
        this.combatEngine.log.addEntry(`${actor.name} failed to stabilize ${target.name} (natural 1).`);
        return false;
    }
    if (roll === 20 || (roll + healSkillModifier >= 15)) { // Natural 20 or success
        target.addCondition("stable");
        target.removeCondition("dying");
        this.combatEngine.log.addEntry(`${target.name} has been stabilized by ${actor.name}!`);
        return true;
    } else {
        this.combatEngine.log.addEntry(`${actor.name} failed to stabilize ${target.name}.`);
        return false;
    }
  }

  takeCastSpellAction(caster: Combatant, spellName: string, target?: Combatant): void {
    if (!this.canTakeAction(caster, ActionType.STANDARD)) { // Assuming most spells are standard actions
        this.combatEngine.log.addEntry(`${caster.name} cannot take a standard action to cast ${spellName}.`);
        return;
    }
    if (caster.isDisabled()) {
        this.combatEngine.log.addEntry(`${caster.name} is disabled and takes 1 damage for casting ${spellName}.`);
        caster.takeDamage(1, "untyped");
        if (!this.canTakeAction(caster, ActionType.STANDARD)) return;
    }

    // TODO: Check if spell provokes AoO based on spell properties (e.g. casting defensively)
    const provokesAoO = true; // Default for most spells
    if (provokesAoO) {
        this.combatEngine.trigger_attacks_of_opportunity(caster, `casting ${spellName}`);
        if (caster.isDead() || caster.hasCondition("unconscious") || caster.hasCondition("stunned")) {
            this.combatEngine.log.addEntry(`${caster.name} cannot complete casting ${spellName} due to AoO effects.`);
            return;
        }
    }
    this.combatEngine.log.addEntry(`${caster.name} casts ${spellName}` + (target ? ` on ${target.name}` : "") + ". (Spell effects not implemented yet).");
    // TODO: Mark action as used (e.g. standard action)
  }

  // ... other actions like Aid Another, Total Defense, Stand Up, etc. will follow a similar pattern ...

  // Helper for Combat Maneuvers
  private performCombatManeuverCheck(
    attacker: Combatant,
    target: Combatant,
    maneuverName: string,
    additionalBonus: number = 0,
    provokes: boolean = true
  ): {roll: number, total: number, targetCMD: number} | null {
    if (provokes) {
        this.combatEngine.trigger_attacks_of_opportunity(attacker, `attempting ${maneuverName}`);
        if (attacker.isDead() || attacker.hasCondition("unconscious") || attacker.hasCondition("stunned")) {
            this.combatEngine.log.addEntry(`${attacker.name} cannot complete ${maneuverName} due to AoO effects.`);
            return null;
        }
    }

    const cmbBase = attacker.calculateCMB();
    const cmbTotal = cmbBase + additionalBonus;
    const targetCMD = target.calculateCMD();
    const roll = this.d20();
    const totalManeuverRoll = roll + cmbTotal;

    this.combatEngine.log.addEntry(`${attacker.name} attempts ${maneuverName} against ${target.name}.`);
    this.combatEngine.log.addEntry(`  CMB Check: ${roll} (d20) + ${cmbBase} (CMB) ${additionalBonus ? `+ ${additionalBonus} (misc) ` : ''}= ${totalManeuverRoll} vs CMD ${targetCMD}.`);
    return { roll, total: totalManeuverRoll, targetCMD };
  }

  takeTripAction(attacker: Combatant, target: Combatant): boolean {
    if (!this.canTakeAction(attacker, ActionType.STANDARD)) {
        this.combatEngine.log.addEntry(`${attacker.name} cannot take a standard action for Trip.`);
        return false;
    }
    if (attacker.isDisabled()) {
        this.combatEngine.log.addEntry(`${attacker.name} is disabled and takes 1 damage for attempting Trip.`);
        attacker.takeDamage(1, "untyped");
        if (!this.canTakeAction(attacker, ActionType.STANDARD)) return false;
    }

    const provokesAoO = !attacker.feats.includes("Improved Trip"); // Simplified feat check
    const maneuverResult = this.performCombatManeuverCheck(attacker, target, "Trip", 0, provokesAoO);
    if (!maneuverResult) return false;

    const { roll, total, targetCMD } = maneuverResult;

    if (roll === 1) { // Auto-fail on Nat 1 for CMB checks
        this.combatEngine.log.addEntry("  Trip failed (natural 1).");
        return false;
    }
    // Auto-success on Nat 20 for CMB checks (Pathfinder Core, p. 199: "A natural 20 is always a success")
    if (roll === 20 || total >= targetCMD) {
        this.combatEngine.log.addEntry("  Trip successful!");
        this.combatEngine.log.addEntry(`  ${target.name} is knocked prone.`);
        target.addCondition("prone");
        // TODO: If attacker has Greater Trip, they get a free attack.
        return true;
    } else {
        this.combatEngine.log.addEntry("  Trip failed.");
        // Pathfinder Trip specific: If you fail by 10 or more, you are knocked prone.
        if ((targetCMD - total) >= 10 && !attacker.feats.includes("Improved Trip")) { // Improved Trip prevents self-trip
            this.combatEngine.log.addEntry(`  ${attacker.name} is knocked prone due to failing badly!`);
            attacker.addCondition("prone");
        }
        return false;
    }
  }

  // TODO: Implement other actions:
  // take_aid_another_action
  // take_total_defense_action
  // take_stand_up_action
  // take_drop_prone_action
  // take_move_action
  // take_draw_sheathe_weapon_action
  // take_charge_action
  // take_withdraw_action
  // take_5_foot_step_action
  // take_bull_rush_action
  // take_disarm_action
  // take_sunder_action

  takeStandUpAction(combatant: Combatant): boolean {
    if (!combatant.hasCondition("prone")) {
        this.combatEngine.log.addEntry(`${combatant.name} is not prone.`);
        return false;
    }
    // Standing up is a move action.
    if (!this.canTakeAction(combatant, ActionType.MOVE)) {
        this.combatEngine.log.addEntry(`${combatant.name} cannot take a move action to stand up.`);
        return false;
    }

    this.combatEngine.log.addEntry(`${combatant.name} attempts to stand up from prone.`);
    // Standing up provokes AoOs.
    this.combatEngine.trigger_attacks_of_opportunity(combatant, "standing up from prone");
    if (combatant.isDead() || combatant.hasCondition("unconscious") || combatant.hasCondition("stunned")) {
        this.combatEngine.log.addEntry(`${combatant.name} cannot complete standing up due to AoO effects.`);
        return false;
    }

    combatant.removeCondition("prone");
    this.combatEngine.log.addEntry(`${combatant.name} stands up.`);
    // TODO: Mark move action as used for the turn.
    combatant.has_moved_this_turn = true; // Assuming standing up counts as movement for 5-foot step.
    return true;
  }

  takeDropProneAction(combatant: Combatant): boolean {
    if (combatant.hasCondition("prone")) {
        this.combatEngine.log.addEntry(`${combatant.name} is already prone.`);
        return false; // Or true, as the state is achieved. Let's say false if no change.
    }
    // Dropping prone is a free action.
    // No canTakeAction check for free actions usually, but let's assume it's part of another action or turn sequence.
    // For simplicity, we'll allow it if the combatant can generally act.
    if (!this.canTakeAction(combatant, ActionType.FREE)) { // Check if they can take ANY action
        this.combatEngine.log.addEntry(`${combatant.name} cannot take a free action to drop prone.`);
        return false;
    }

    this.combatEngine.log.addEntry(`${combatant.name} drops prone.`);
    combatant.addCondition("prone");
    return true;
  }

  takeMoveAction(combatant: Combatant, distance: number, provokesAoO: boolean = true): boolean {
    if (!this.canTakeAction(combatant, ActionType.MOVE)) {
        return false;
    }
    if (combatant.isDisabled()) { // Taking move action while disabled is allowed, but no further damage unless it's strenuous.
        // Standard Pathfinder: "A disabled character who takes a standard action (or any other action deemed as strenuous, including some move actions, such as walking) takes 1 point of damage after completing the act."
        // Simple move is usually not strenuous. Running or charging is.
        // For now, simple move does not cause damage.
    }

    if (provokesAoO) {
        this.combatEngine.trigger_attacks_of_opportunity(combatant, "moving");
        if (combatant.isDead() || combatant.hasCondition("unconscious") || combatant.hasCondition("stunned")) {
            this.combatEngine.log.addEntry(`${combatant.name} cannot complete movement due to AoO effects.`);
            return false;
        }
    }

    const maxDistance = combatant.base_speed; // This is for a single move action.
    if (distance <= maxDistance && distance >= 0) {
        this.combatEngine.log.addEntry(`${combatant.name} moves ${distance} feet.`);
        combatant.has_moved_this_turn = true;
        // TODO: Mark move action as used.
        return true;
    } else {
        this.combatEngine.log.addEntry(`${combatant.name} cannot move ${distance} feet (max: ${maxDistance} for a single move action).`);
        return false;
    }
  }

  takeFiveFootStepAction(combatant: Combatant, direction: string = "any available direction"): boolean {
    // 5-foot step is a free action, but has special conditions.
    if (combatant.has_moved_this_turn) { // Cannot take if already moved this turn.
        this.combatEngine.log.addEntry(`${combatant.name} cannot take a 5-foot step: already moved or taken a move action this turn.`);
        return false;
    }
    if (!this.canTakeAction(combatant, ActionType.FREE)) { // General check if they can take free actions
         this.combatEngine.log.addEntry(`${combatant.name} cannot take a free action (e.g. 5-foot step).`);
        return false;
    }
    // You can take a 5-foot step before, during, or after your other actions in the round.
    // It does not provoke AoO.

    this.combatEngine.log.addEntry(`${combatant.name} takes a 5-foot step ${direction}.`);
    combatant.has_moved_this_turn = true; // Taking a 5-foot step counts as movement for not being able to take another one.
    // TODO: This doesn't consume the main move action.
    return true;
  }

  takeChargeAction(attacker: Combatant, target: Combatant, chargeAttackIndex: number = 0): AttackResult | null {
    if (!this.canTakeAction(attacker, ActionType.FULL_ROUND)) {
        this.combatEngine.log.addEntry(`${attacker.name} cannot take a full-round action to Charge.`);
        return null;
    }
    if (attacker.isDisabled()) { // Cannot charge if disabled.
        this.combatEngine.log.addEntry(`${attacker.name} is disabled and cannot take a Charge action.`);
        return null;
    }

    if (!attacker.attacks || chargeAttackIndex >= attacker.attacks.length || attacker.attacks[chargeAttackIndex].attack_type === AttackType.RANGED) {
        this.combatEngine.log.addEntry(`${attacker.name} cannot charge with the selected attack (must be melee, index ${chargeAttackIndex}).`);
        return null;
    }
    const chargeAttack = attacker.attacks[chargeAttackIndex];

    // Must move at least 10 feet and up to double speed.
    const chargeDistance = attacker.base_speed * 2; // Potential distance.
    if (chargeDistance < 10) { // Effectively, if base_speed < 5, can't charge 10ft.
                               // Or rather, must move AT LEAST 10 ft.
        this.combatEngine.log.addEntry(`${attacker.name} cannot charge: must be able to move at least 10 feet in a straight line.`);
        return null;
    }

    this.combatEngine.log.addEntry(`${attacker.name} charges ${target.name} (movement of up to ${chargeDistance}ft not fully simulated).`);
    attacker.has_moved_this_turn = true;
    // AC penalty: -2 to AC until the start of your next turn.
    // This needs to be tracked on the combatant or via a temporary effect.
    // For now, just log it.
    this.combatEngine.log.addEntry(`  ${attacker.name} takes -2 AC until next turn (effect needs full implementation).`);
    this.combatEngine.log.addEntry(`  Charging with ${chargeAttack.name} (+2 attack bonus).`);

    // Charge provides +2 bonus on the attack roll.
    const attackResult = this.combatEngine.make_attack(attacker, target, chargeAttack, false, 0, [[2, "charge"]]);

    // TODO: Mark full-round action as used.
    return attackResult;
  }

  takeWithdrawAction(combatant: Combatant, distance: number): boolean {
    if (!this.canTakeAction(combatant, ActionType.FULL_ROUND)) {
        this.combatEngine.log.addEntry(`${combatant.name} cannot take a full-round action to Withdraw.`);
        return false;
    }
     if (combatant.isDisabled()) { // Cannot withdraw if disabled.
        this.combatEngine.log.addEntry(`${combatant.name} is disabled and cannot take a Withdraw action.`);
        return false;
    }

    const maxDistance = combatant.base_speed * 2; // Withdraw is full-round, move up to double speed.
    if (distance <= 0 || distance > maxDistance) {
        this.combatEngine.log.addEntry(`${combatant.name} cannot withdraw ${distance}ft (must be >0 and <= ${maxDistance}ft).`);
        return false;
    }

    this.combatEngine.log.addEntry(`${combatant.name} withdraws ${distance}ft.`);
    this.combatEngine.log.addEntry(`  Movement from starting squares does not provoke AoOs from any creatures that could see the character at the start of their turn (visibility/line of sight not fully simulated).`);
    combatant.has_moved_this_turn = true;
    // TODO: Mark full-round action as used.
    return true;
  }

  takeBullRushAction(attacker: Combatant, target: Combatant, asPartOfCharge: boolean = false): boolean {
    const actionTypeCheck = asPartOfCharge ? ActionType.FREE : ActionType.STANDARD; // Bull rush as part of charge is free.
    if (!asPartOfCharge && !this.canTakeAction(attacker, actionTypeCheck)) {
        this.combatEngine.log.addEntry(`${attacker.name} cannot take a ${actionTypeCheck} action for Bull Rush.`);
        return false;
    }
    if (!asPartOfCharge && attacker.isDisabled()) {
        this.combatEngine.log.addEntry(`${attacker.name} is disabled and takes 1 damage for attempting Bull Rush.`);
        attacker.takeDamage(1, "untyped");
        if (!this.canTakeAction(attacker, actionTypeCheck)) return false;
    }

    const provokesAoO = !attacker.feats.includes("Improved Bull Rush");
    const chargeBonus = asPartOfCharge ? 2 : 0;
    if (asPartOfCharge) this.combatEngine.log.addEntry(`  Gains +2 bonus to Bull Rush CMB from charging.`);

    const maneuverResult = this.performCombatManeuverCheck(attacker, target, "Bull Rush", chargeBonus, provokesAoO);
    if (!maneuverResult) return false;
    const { roll, total, targetCMD } = maneuverResult;

    if (roll === 1) {
        this.combatEngine.log.addEntry("  Bull Rush failed (natural 1).");
        return false;
    }
    if (roll === 20 || total >= targetCMD) {
        this.combatEngine.log.addEntry("  Bull Rush successful!");
        // Pathfinder: push back 5 feet, +5 feet for every 5 points CMB exceeds CMD.
        let pushDistance = 5;
        if (total - targetCMD >= 5) {
            pushDistance += Math.floor((total - targetCMD) / 5) * 5;
        }
        this.combatEngine.log.addEntry(`  ${target.name} is pushed back ${pushDistance} feet.`);
        this.combatEngine.log.addEntry(`  ${attacker.name} can move with ${target.name} (movement not simulated).`);
        attacker.has_moved_this_turn = true; // Attacker moves with target
        // TODO: Mark action as used.
        return true;
    } else {
        this.combatEngine.log.addEntry("  Bull Rush failed.");
        return false;
    }
  }

  takeDisarmAction(attacker: Combatant, target: Combatant): boolean {
    if (!this.canTakeAction(attacker, ActionType.STANDARD)) {
        this.combatEngine.log.addEntry(`${attacker.name} cannot take a standard action for Disarm.`);
        return false;
    }
    if (attacker.isDisabled()) {
        this.combatEngine.log.addEntry(`${attacker.name} is disabled and takes 1 damage for attempting Disarm.`);
        attacker.takeDamage(1, "untyped");
        if (!this.canTakeAction(attacker, ActionType.STANDARD)) return false;
    }

    const provokesAoO = !attacker.feats.includes("Improved Disarm");
    // Check if attacker is considered "unarmed" for disarm (e.g. no weapon, or using natural attack not suited for disarm)
    // This is complex. Assume for now they are using a weapon unless explicitly stated.
    // Python version had: is_unarmed_attempt = not attacker.attacks
    // This is too simple, as attacker.attacks lists their capabilities, not what's wielded.
    // Let's assume any melee attack capability means they are "armed" for disarm.
    // A true "unarmed" disarm (e.g. with hands) takes -4.
    // For now, no penalty unless we model wielded items.
    const disarmPenalty = 0;

    const maneuverResult = this.performCombatManeuverCheck(attacker, target, "Disarm", disarmPenalty, provokesAoO);
    if (!maneuverResult) return false;
    const { roll, total, targetCMD } = maneuverResult;

    if (roll === 1) {
        this.combatEngine.log.addEntry("  Disarm failed (natural 1).");
        return false;
    }
    if (roll === 20 || total >= targetCMD) {
        this.combatEngine.log.addEntry("  Disarm successful!");
        // Item dropped to ground in target's square.
        // If CMB exceeds CMD by 10+, target drops item in hand AND one other item.
        // This is simplified as item system is not implemented.
        const itemsDropped = (total - targetCMD >= 10) ? 2 : 1;
        this.combatEngine.log.addEntry(`  ${target.name} drops ${itemsDropped} item(s) (item system not implemented).`);
        // TODO: Mark action as used.
        return true;
    } else {
        this.combatEngine.log.addEntry("  Disarm failed.");
        // Pathfinder Disarm: If you fail the attempt by 10 or more, you drop the weapon you were using to attempt the disarm.
        if ((targetCMD - total) >= 10 && !attacker.feats.includes("Improved Disarm")) {
             this.combatEngine.log.addEntry(`  ${attacker.name} drops their weapon due to failing badly! (item system not implemented)`);
        }
        return false;
    }
  }

  // Sunder is similar to Disarm/Trip, uses CMB vs CMD.
  // Placeholder for now.
  takeSunderAction(attacker: Combatant, target: Combatant, targetItemName: string = "weapon"): boolean {
    if (!this.canTakeAction(attacker, ActionType.STANDARD)) {
        this.combatEngine.log.addEntry(`${attacker.name} cannot take a standard action for Sunder.`);
        return false;
    }
     if (attacker.isDisabled()) {
        this.combatEngine.log.addEntry(`${attacker.name} is disabled and takes 1 damage for attempting Sunder.`);
        attacker.takeDamage(1, "untyped");
        if (!this.canTakeAction(attacker, ActionType.STANDARD)) return false;
    }

    const provokesAoO = !attacker.feats.includes("Improved Sunder");
    const maneuverResult = this.performCombatManeuverCheck(attacker, target, `Sunder (${targetItemName})`, 0, provokesAoO);
    if (!maneuverResult) return false;
    const { roll, total, targetCMD } = maneuverResult;

    if (roll === 1) {
        this.combatEngine.log.addEntry(`  Sunder attempt against ${targetItemName} failed (natural 1).`);
        return false;
    }
    if (roll === 20 || total >= targetCMD) { // Here, CMD is of the wielder, not the item. This is different from some interpretations.
                                        // Pathfinder: "You can attempt to sunder an item held or worn by an opponent."
                                        // "Make an attack roll against the item." AC of item = 7 + size mod + wielder's Dex.
                                        // Hardness and HP then apply.
                                        // The Python code used CMB vs CMD, which is for the *maneuver*, not hitting item.
                                        // Let's assume for now it's CMB vs CMD to make item sunderable.
        this.combatEngine.log.addEntry(`  Sunder attempt against ${targetItemName} successful (CMB check passed)!`);
        this.combatEngine.log.addEntry(`  Damage would be dealt to ${targetItemName} (item HP/hardness/damage not implemented).`);
        // TODO: Mark action as used.
        return true;
    } else {
        this.combatEngine.log.addEntry(`  Sunder attempt against ${targetItemName} failed (CMB check failed).`);
        return false;
    }
  }

  // These were present in the Python version's method list.

  takeAidAnotherAction(actor: Combatant, targetCreatureToHinder: Combatant, allyToAid: Combatant, aidType: "attack" | "ac" = "attack"): boolean {
    if (!this.canTakeAction(actor, ActionType.STANDARD)) {
        this.combatEngine.log.addEntry(`${actor.name} cannot take a standard action for Aid Another.`);
        return false;
    }
    if (actor.isDisabled()) {
        this.combatEngine.log.addEntry(`${actor.name} is disabled and takes 1 damage for attempting Aid Another.`);
        actor.takeDamage(1, "untyped");
        if (!this.canTakeAction(actor, ActionType.STANDARD)) return false;
    }

    // Aid Another requires an attack roll against AC 10.
    // "You make an attack roll against AC 10."
    // "If your attack roll succeeds, your friend gains either a +2 bonus on his next attack roll against that opponent or a +2 bonus to AC against that opponent’s next attack (your choice), as long as that attack comes before the beginning of your next turn."
    // For simplicity, we won't use a full attack object, just a conceptual attack roll.
    // BAB + Str/Dex mod. Let's use Str for simplicity or primary attack's ability.
    let attackBonus = actor.base_attack_bonus + actor.ability_scores.getModifier(actor.attacks[0]?.associated_ability_for_attack || "strength");
    // A more accurate bonus would be from getAttackBonus with a conceptual melee attack.
    // For now, simplified.

    const roll = this.d20();
    const totalAttackRoll = roll + attackBonus;
    const dc = 10;

    this.combatEngine.log.addEntry(`${actor.name} attempts Aid Another (for ${allyToAid.name}'s ${aidType === "attack" ? "attack" : "AC"}) against ${targetCreatureToHinder.name}.`);
    this.combatEngine.log.addEntry(`  Aid Another roll: ${roll} (d20) + ${attackBonus} (bonus) = ${totalAttackRoll} vs AC ${dc}.`);

    // AoO: "Aid another is a standard action. In many cases, you must be adjacent to your ally or the foe you are hindering to use this ability."
    // It doesn't inherently provoke an AoO unless the action to achieve it does (e.g., moving into position).
    // The attack roll itself for Aid Another is not an attack that provokes.

    if (roll === 1) { // Nat 1 on attack roll for Aid Another
        this.combatEngine.log.addEntry("  Aid Another failed (natural 1).");
        return false;
    }
    if (roll === 20 || totalAttackRoll >= dc) { // Nat 20 or success
        this.combatEngine.log.addEntry("  Aid Another successful!");
        const bonusType = aidType === "attack" ? "attack roll" : "AC";
        const bonusTarget = aidType === "attack" ? targetCreatureToHinder.name : actor.name; // AC bonus is against target's attack on ally.
        this.combatEngine.log.addEntry(`  ${allyToAid.name} will get +2 bonus to ${bonusType} against ${bonusTarget} before ${actor.name}'s next turn (effect tracking not fully implemented).`);
        // TODO: Implement temporary bonus tracking on CombatEngine or Combatants.
        return true;
    } else {
        this.combatEngine.log.addEntry("  Aid Another failed.");
        return false;
    }
  }

  takeTotalDefenseAction(combatant: Combatant): boolean {
    if (!this.canTakeAction(combatant, ActionType.STANDARD)) { // Total Defense is a Standard Action
        this.combatEngine.log.addEntry(`${combatant.name} cannot take a standard action for Total Defense.`);
        return false;
    }
    if (combatant.isDisabled()) {
        this.combatEngine.log.addEntry(`${combatant.name} is disabled and takes 1 damage for attempting Total Defense.`);
        combatant.takeDamage(1, "untyped");
        if (!this.canTakeAction(combatant, ActionType.STANDARD)) return false;
    }

    this.combatEngine.log.addEntry(`${combatant.name} takes the Total Defense action.`);
    this.combatEngine.log.addEntry("  Gains +4 dodge bonus to AC until their next turn (effect tracking not fully implemented).");
    this.combatEngine.log.addEntry("  Cannot make Attacks of Opportunity while using Total Defense (effect tracking not fully implemented).");

    // TODO: Implement actual +4 dodge bonus and restriction on AoOs.
    // This would typically involve adding a temporary condition or modifier to the combatant.
    // e.g., combatant.addTemporaryModifier({ type: "dodge", value: 4, source: "Total Defense", duration: 1_round });
    // combatant.setFlag("cannotMakeAoOs", true, 1_round);

    // TODO: Mark standard action as used.
    return true;
  }

  takeDrawOrSheatheWeaponAction(combatant: Combatant, weaponName: string, action: "draw" | "sheathe" = "draw"): boolean {
    // Drawing a weapon is a move action, or a free action if BAB +1 or higher (part of movement).
    // Sheathing a weapon is a move action.
    // Feats like Quick Draw can change this.
    // For simplicity, assume it's a move action for now.
    if (!this.canTakeAction(combatant, ActionType.MOVE)) {
        this.combatEngine.log.addEntry(`${combatant.name} cannot take a move action to ${action} ${weaponName}.`);
        return false;
    }

    const logMsgAction = action === "draw" ? "draws" : "sheathes";
    this.combatEngine.log.addEntry(`${combatant.name} attempts to ${logMsgAction} ${weaponName}.`);

    // Sheathing a weapon provokes AoOs. Drawing does not unless you do something else stupid.
    // "Sheathing a weapon provokes attacks of opportunity." (Pathfinder Core, p. 141)
    if (action === "sheathe") {
        this.combatEngine.trigger_attacks_of_opportunity(combatant, `sheathing ${weaponName}`);
        if (combatant.isDead() || combatant.hasCondition("unconscious") || combatant.hasCondition("stunned")) {
            this.combatEngine.log.addEntry(`${combatant.name} cannot complete sheathing ${weaponName} due to AoO effects.`);
            return false;
        }
    }

    this.combatEngine.log.addEntry(`${combatant.name} successfully ${logMsgAction}s ${weaponName} (inventory/equipment slots not fully implemented).`);
    // TODO: Update combatant's equipment slots.
    // TODO: Mark move action as used.
    combatant.has_moved_this_turn = true; // Consumes movement potential for 5-foot step if it was a move action.
    return true;
  }
}
