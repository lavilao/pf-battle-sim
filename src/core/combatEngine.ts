import { Combatant } from "./combatant.ts";
import { Attack } from "./attack.ts";
import { AttackType } from "./enums.ts";
import { AttackResult } from "./attackResult.ts";
import { CombatLog } from "./combatLog.ts";
import { rollDiceString } from "./utils.ts"; // For d20 rolls

interface InitiativeEntry {
  combatant: Combatant;
  totalScore: number;
  dexMod: number; // For tie-breaking after score
  roll: number;   // For tie-breaking after dexMod
  tiebreakerRoll?: number; // For final tie-breaking if all else is equal
}

export class CombatEngine {
  public combatants: Combatant[] = [];
  private initiativeOrder: Combatant[] = []; // Just combatants, sorted
  private initiativeDetails: InitiativeEntry[] = []; // For complex sorting and logging

  public currentRound = 0;
  public currentTurnIndex = 0;
  public isSurpriseRound = false;
  public combatActive = false;
  public log: CombatLog;

  constructor() {
    this.log = new CombatLog();
  }

  private d20(): number {
    return rollDiceString("1d20");
  }

  addCombatant(combatant: Combatant, isAwareInSurprise: boolean = true): void {
    combatant.resetForCombat();
    // Storing surprise round awareness. Python used setattr.
    // A cleaner way would be an optional property on Combatant or a WeakMap.
    // For now, using a dynamic property with a comment.
    (combatant as any).isAwareInSurpriseRound = isAwareInSurprise;
    this.combatants.push(combatant);
    this.log.addEntry(`${combatant.name} joins the combat ${isAwareInSurprise ? "(aware)" : "(unaware)"}.`);
  }

  private rollInitiative(): void {
    this.log.addEntry("=== Rolling Initiative ===");
    this.initiativeDetails = [];

    for (const combatant of this.combatants) {
      combatant.recalculateInitiativeModifier(); // Ensure it's up to date
      const roll = this.d20();
      const totalScore = roll + combatant.initiative_modifier;
      combatant.current_initiative_roll = roll; // Store on combatant for reference
      combatant.final_initiative_score = totalScore;

      this.initiativeDetails.push({
        combatant,
        totalScore,
        dexMod: combatant.ability_scores.getModifier("dexterity"), // Store actual Dex mod for tie-breaking
        roll,
      });
      this.log.addEntry(
        `${combatant.name}: ${roll} (roll) + ${combatant.initiative_modifier} (mod) = ${totalScore}`
      );
    }

    // Sort: 1. Total Score (desc), 2. Dex Mod (desc), 3. Original Roll (desc)
    this.initiativeDetails.sort((a, b) => {
      if (b.totalScore !== a.totalScore) return b.totalScore - a.totalScore;
      if (b.dexMod !== a.dexMod) return b.dexMod - a.dexMod;
      return b.roll - a.roll; // Higher original roll wins if score and Dex mod are tied
    });

    // Pathfinder official tie-breaking: If total init and Dex mod are tied, roll off (d20).
    // The Python code implemented a custom tie-breaker. Let's try to match that specific logic.
    // Python logic: if total score AND initiative_modifier (not necessarily dexMod) were tied, roll off.
    // My current sort already handles dexMod. Let's re-evaluate the tie-break part.
    // Python sort: (total, combatant.initiative_modifier, original_roll)
    // Then it iterated and if total AND combatant.initiative_modifier were tied, it did d20 roll-off.

    // Let's refine sorting and tie-breaking to match Python's specific custom rule if possible.
    // Sort by totalScore desc, then by combatant.initiative_modifier desc.
    this.initiativeDetails.sort((a, b) => {
        if (b.totalScore !== a.totalScore) return b.totalScore - a.totalScore;
        // combatant.initiative_modifier might include more than just Dex (e.g. Improved Initiative feat)
        return b.combatant.initiative_modifier - a.combatant.initiative_modifier;
    });

    // Now, iterate and apply d20 roll-offs for ties in both score and initiative_modifier
    let i = 0;
    while (i < this.initiativeDetails.length) {
        let j = i + 1;
        while (
            j < this.initiativeDetails.length &&
            this.initiativeDetails[j].totalScore === this.initiativeDetails[i].totalScore &&
            this.initiativeDetails[j].combatant.initiative_modifier === this.initiativeDetails[i].combatant.initiative_modifier
        ) {
            j++;
        }

        if (j > i + 1) { // A tie was found for this group
            const tiedGroup = this.initiativeDetails.slice(i, j);
            this.log.addEntry(
              `Breaking tie for score ${tiedGroup[0].totalScore} and mod ${tiedGroup[0].combatant.initiative_modifier} between: ${tiedGroup.map(e => e.combatant.name).join(', ')}`
            );
            for (const entry of tiedGroup) {
                entry.tiebreakerRoll = this.d20();
                this.log.addEntry(`  ${entry.combatant.name} tiebreaker roll: ${entry.tiebreakerRoll}`);
            }
            tiedGroup.sort((a, b) => (b.tiebreakerRoll ?? 0) - (a.tiebreakerRoll ?? 0));
            // Replace the original segment with the re-sorted tied group
            this.initiativeDetails.splice(i, tiedGroup.length, ...tiedGroup);
        }
        i = j;
    }

    this.initiativeOrder = this.initiativeDetails.map(entry => entry.combatant);

    this.log.addEntry("\n=== Final Initiative Order ===");
    this.initiativeOrder.forEach((cb, index) => {
      const detail = this.initiativeDetails.find(d => d.combatant === cb);
      this.log.addEntry(`${index + 1}. ${cb.name}: ${detail?.totalScore}`);
    });
  }

  startCombat(): boolean {
    if (this.combatants.length === 0) {
      this.log.addEntry("No combatants to start combat.");
      return false;
    }
    this.log.addEntry("=== COMBAT BEGINS ===");
    this.rollInitiative();

    const awareCombatants = this.combatants.filter(c => (c as any).isAwareInSurpriseRound !== false);
    const unawareCombatants = this.combatants.filter(c => (c as any).isAwareInSurpriseRound === false);

    if (awareCombatants.length > 0 && unawareCombatants.length > 0) {
      this.log.addEntry("\n=== SURPRISE ROUND ===");
      if (unawareCombatants.length > 0) {
        this.log.addEntry(`Unaware and flat-footed: ${unawareCombatants.map(c => c.name).join(', ')}`);
      }
      this.isSurpriseRound = true;
      this.currentRound = 0; // Surprise round is before round 1
      unawareCombatants.forEach(c => {
        c.is_flat_footed = true;
        c.addCondition("flat-footed");
      });
    } else {
      if (unawareCombatants.length > 0 && awareCombatants.length === 0) {
        this.log.addEntry("All combatants are unaware! No surprise round, everyone starts flat-footed.");
        this.combatants.forEach(c => {
            c.is_flat_footed = true;
            c.addCondition("flat-footed");
        });
      } else {
        this.log.addEntry("All combatants are aware. No surprise round.");
      }
      this.isSurpriseRound = false;
      this.currentRound = 1;
    }

    this.currentTurnIndex = 0;
    this.combatActive = true;
    if (!this.isSurpriseRound) {
        this.log.addEntry(`\n=== ROUND ${this.currentRound} ===`);
    }
    this.announceTurn();
    return true;
  }

  getCurrentCombatant(): Combatant | null {
    if (!this.combatActive || this.initiativeOrder.length === 0 || this.currentTurnIndex >= this.initiativeOrder.length) {
      return null;
    }
    // Find next active combatant from currentTurnIndex
    for (let i = 0; i < this.initiativeOrder.length; i++) {
        const checkIndex = (this.currentTurnIndex + i) % this.initiativeOrder.length;
        const combatant = this.initiativeOrder[checkIndex];
        if (combatant.current_hp > 0 && !combatant.isDead() && !combatant.hasCondition("unconscious")) {
            if (i > 0) this.currentTurnIndex = checkIndex; // Update index if we skipped some
            return combatant;
        }
    }
    return null; // All remaining combatants are defeated
  }

  private canActInSurpriseRound(combatant: Combatant): boolean {
    return (combatant as any).isAwareInSurpriseRound !== false;
  }

  private announceTurn(): void {
    const currentCombatant = this.getCurrentCombatant();
    if (currentCombatant) {
      if (this.isSurpriseRound && !this.canActInSurpriseRound(currentCombatant)) {
        this.log.addEntry(`${currentCombatant.name}'s turn (cannot act - unaware in surprise round).`);
        this.advanceTurn(); // Automatically skip if cannot act
      } else {
        this.log.addEntry(
          `${currentCombatant.name}'s turn (${currentCombatant.current_hp}/${currentCombatant.max_hp} HP)`
        );
        this.processStartOfTurnEffects(currentCombatant);
      }
    } else if (this.combatActive) {
      this.log.addEntry("No valid combatant for current turn. Checking combat status.");
      if (this.isCombatOver()) {
        this.endCombat();
      }
    }
  }

  private processStartOfTurnEffects(combatant: Combatant): void {
    if (combatant.isDying() && !combatant.hasCondition("stable")) {
      this.log.addEntry(`${combatant.name} is dying and must attempt to stabilize.`);
      if (combatant.stabilize()) { // stabilize() handles roll and HP loss on fail
        this.log.addEntry(`${combatant.name} made a Constitution check and stabilized!`);
      } else {
        this.log.addEntry(`${combatant.name} failed stabilization check and loses 1 HP.`);
        if (combatant.isDead()) {
          this.log.addEntry(`${combatant.name} has died from HP loss.`);
        } else {
          this.log.addEntry(`${combatant.name} HP: ${combatant.current_hp}/${combatant.max_hp}`);
        }
      }
    }
    // If it's their first turn in normal combat (not surprise) and they were flat-footed.
    if (!this.isSurpriseRound && combatant.is_flat_footed) {
        // Check if they were aware or if it's after surprise round.
        // Basically, if it's their turn and it's not surprise round, they lose flat-footed.
        combatant.is_flat_footed = false;
        combatant.removeCondition("flat-footed");
        this.log.addEntry(`  ${combatant.name} is no longer flat-footed.`);
    }
    // TODO: Other start-of-turn effects (regeneration, ongoing damage, condition recovery rolls)
  }

  advanceTurn(): void {
    if (!this.combatActive) return;

    const actor = this.initiativeOrder[this.currentTurnIndex]; // Combatant whose turn just ended
    if (actor) {
        actor.has_acted_this_combat = true; // Mark as acted
        // Flat-footed status handling moved to processStartOfTurnEffects for their actual turn.
    }

    this.currentTurnIndex++;
    if (this.currentTurnIndex >= this.initiativeOrder.length) { // End of round
      this.log.addEntry(`--- End of Round ${this.isSurpriseRound ? "Surprise" : this.currentRound} ---`);

      // End of round effects
      this.combatants.forEach(cb => {
          cb.aoo_made_this_round = 0;
          cb.has_moved_this_turn = false; // Reset for next round
          // TODO: Tick down durations of spells/effects
      });

      if (this.isSurpriseRound) {
        this.isSurpriseRound = false;
        this.currentRound = 1;
        this.log.addEntry(`\n=== ROUND ${this.currentRound} (Normal Combat Begins) ===`);
      } else {
        this.currentRound++;
        this.log.addEntry(`\n=== ROUND ${this.currentRound} ===`);
      }
      this.currentTurnIndex = 0;

      if (this.isCombatOver()) {
        this.endCombat();
        return;
      }
    }

    if (this.combatActive) { // If combat didn't end
        this.announceTurn();
    }
  }

  canMakeAoO(combatant: Combatant): boolean {
    if (combatant.is_flat_footed && !combatant.feats.includes("Combat Reflexes")) {
        return false;
    }
    if (combatant.hasCondition("stunned") || combatant.hasCondition("paralyzed") ||
        combatant.hasCondition("helpless") || combatant.hasCondition("unconscious") || combatant.isDead()) {
        return false;
    }

    let maxAoOs = 1;
    if (combatant.feats.includes("Combat Reflexes")) {
        const dexMod = combatant.ability_scores.getModifier("dexterity");
        maxAoOs += Math.max(0, dexMod); // Add positive Dex mod for Combat Reflexes
    }
    return combatant.aoo_made_this_round < maxAoOs;
  }

  triggerAttacksOfOpportunity(offender: Combatant, provokingActionDescription: string): void {
    this.log.addEntry(`${offender.name} performing '${provokingActionDescription}' may provoke AoOs.`);
    for (const attacker of this.combatants) {
      if (attacker === offender || !attacker.isAlive() || attacker.hasCondition("unconscious") || attacker.hasCondition("stunned") || attacker.hasCondition("paralyzed")) {
        continue;
      }

      // Simplified threat check: assumes attacker can reach offender.
      // A real system needs grid positions and weapon reach.
      const canThreaten = true; // Placeholder
      if (!canThreaten) continue;

      if (this.canMakeAoO(attacker)) {
        const aooAttack = attacker.attacks.find(att => att.attack_type === AttackType.MELEE || att.attack_type === AttackType.NATURAL);
        if (aooAttack) {
          this.log.addEntry(`  ${attacker.name} gets an Attack of Opportunity against ${offender.name} with ${aooAttack.name}!`);
          this.makeAttack(attacker, offender, aooAttack, false, 0, true); // isAoO = true
          attacker.aoo_made_this_round++;
          if (!offender.isAlive() || offender.hasCondition("unconscious") || offender.hasCondition("stunned") || offender.hasCondition("paralyzed")) {
            this.log.addEntry(`  ${offender.name} is downed or incapacitated by the AoO! Action (${provokingActionDescription}) is interrupted.`);
            // TODO: Signal interruption to the ActionHandler or calling context
            break; // Stop further AoOs for this provoking action if offender is downed.
          }
        } else {
            this.log.addEntry(`  ${attacker.name} could make an AoO but has no suitable melee/natural attack listed.`);
        }
      }
    }
  }

  makeAttack(
    attacker: Combatant, target: Combatant, attack: Attack,
    isFullAttack: boolean = false, attackNumber: number = 0, isAoO: boolean = false,
    additionalAttackBonuses: Array<[number, string]> = [],
    _additionalDamageBonuses: Array<[number, string]> = [] // Placeholder for now
  ): AttackResult | null {
    if (!attacker.isAlive() || attacker.hasCondition("unconscious") || attacker.hasCondition("stunned") || attacker.hasCondition("paralyzed")) {
        this.log.addEntry(`${attacker.name} cannot make an attack due to being incapacitated.`);
        return null;
    }

    const result = new AttackResult(attacker.name, target.name, attack.name);
    const baseAttackBonusVal = attacker.getAttackBonus(
        attack,
        isFullAttack && !isAoO,
        isAoO ? 0 : attackNumber,
        target
    );
    result.total_attack_bonus = baseAttackBonusVal;
    let bonusDescriptionsLog: string[] = [];

    additionalAttackBonuses.forEach(([val, desc]) => {
        result.total_attack_bonus += val;
        bonusDescriptionsLog.push(`${val > 0 ? '+' : ''}${val} (${desc})`);
    });

    result.attack_roll = this.d20();
    const totalAttackValue = result.attack_roll + result.total_attack_bonus;

    // Determine target AC
    let acTypeToUse: "standard" | "touch" | "flat_footed" = "standard";
    if (target.is_flat_footed || target.hasCondition("helpless") || target.hasCondition("stunned") ||
        target.hasCondition("paralyzed") || target.hasCondition("blinded")) {
        acTypeToUse = "flat_footed";
    }
    // TODO: Touch attacks would set acTypeToUse = "touch"
    result.target_ac = target.getAC(acTypeToUse);

    // Contextual AC adjustments (e.g. Prone)
    if (target.hasCondition("prone")) {
        if (attack.attack_type === AttackType.RANGED) {
            this.log.addEntry(`  Target ${target.name} is prone, gains +4 AC vs this ranged attack.`);
            result.target_ac += 4;
        } else if (attack.attack_type === AttackType.MELEE) {
            this.log.addEntry(`  Target ${target.name} is prone, takes -4 AC vs this melee attack.`);
            result.target_ac -= 4;
        }
    }

    this.log.addEntry(`${attacker.name} attacks ${target.name} with ${attack.name}${isAoO ? " (AoO)" : ""}`);
    let bonusLog = `Base: ${baseAttackBonusVal}`;
    if (bonusDescriptionsLog.length > 0) bonusLog += `, Modifiers: ${bonusDescriptionsLog.join(', ')}`;
    this.log.addEntry(`  Attack Roll: ${result.attack_roll} (d20) + ${result.total_attack_bonus} (Total Bonus from ${bonusLog}) = ${totalAttackValue} vs AC ${result.target_ac}`);

    if (result.attack_roll === 1) {
      result.is_hit = false;
      this.log.addEntry("  MISS! (Natural 1)");
      return result;
    }
    result.is_hit = (totalAttackValue >= result.target_ac) || result.attack_roll === 20;

    if (!result.is_hit) {
      this.log.addEntry("  MISS!");
      return result;
    }

    // Hit! Check concealment
    let missChancePercent = 0;
    // Example: if (attacker.hasCondition("blinded")) missChancePercent = 50;
    // TODO: Implement concealment checks properly
    if (missChancePercent > 0 && (rollDiceString(`1d100`) <= missChancePercent)) {
        this.log.addEntry(`  HIT! (but miss due to ${missChancePercent}% concealment)`);
        result.is_hit = false;
        return result;
    }
    this.log.addEntry("  HIT!");

    if (result.attack_roll === 20 || (attack.getThreatRange().includes(result.attack_roll))) {
      result.is_critical_threat = true;
      this.log.addEntry("  Critical threat! Rolling to confirm...");
      const confirmRoll = this.d20();
      // Confirmation roll uses same total attack bonus, against same AC.
      if (confirmRoll === 1) {
          result.is_critical_hit = false;
          this.log.addEntry(`  Confirmation failed (Natural 1): ${confirmRoll} + ${result.total_attack_bonus} vs AC ${result.target_ac}. Normal hit.`);
      } else if ((confirmRoll + result.total_attack_bonus >= result.target_ac) || confirmRoll === 20) {
        result.is_critical_hit = true;
        this.log.addEntry(`  CRITICAL HIT CONFIRMED!: ${confirmRoll} + ${result.total_attack_bonus} vs AC ${result.target_ac}`);
      } else {
        result.is_critical_hit = false;
        this.log.addEntry(`  Confirmation failed: ${confirmRoll} + ${result.total_attack_bonus} vs AC ${result.target_ac}. Normal hit.`);
      }
    }

    const {totalDamage, rolls: damageRolls} = attacker.rollDamage(attack, result.is_critical_hit /*, is_off_hand, is_two_handed */);
    result.damage_rolls = damageRolls;
    result.total_damage = totalDamage; // rollDamage should already apply min 1

    // TODO: Apply additional_damage_bonuses if any

    this.log.addEntry(`  Damage: ${result.total_damage} ${result.is_critical_hit ? `(x${attack.getCritMultiplier()} critical)` : ""} from rolls [${damageRolls.join(', ')}]`);

    result.damage_taken = target.takeDamage(result.total_damage, attack.damage_type);
    if (result.damage_taken < result.total_damage) {
        this.log.addEntry(`  Damage reduced to ${result.damage_taken} by DR/resistances.`);
    }
    this.log.addEntry(`  ${target.name} takes ${result.damage_taken} damage. HP: ${target.current_hp}/${target.max_hp}`);

    if (target.isDead()) this.log.addEntry(`  ${target.name} is DEAD!`);
    else if (target.isDying()) this.log.addEntry(`  ${target.name} is DYING!`);
    else if (target.isDisabled()) this.log.addEntry(`  ${target.name} is DISABLED (0 HP)!`);
    else if (target.hasCondition("unconscious")) this.log.addEntry(`  ${target.name} falls UNCONSCIOUS!`);

    return result;
  }

  getValidTargets(attacker: Combatant): Combatant[] {
    return this.combatants.filter(c =>
        c !== attacker &&
        c.isAlive() &&
        !c.hasCondition("unconscious")
    );
  }

  isCombatOver(): boolean {
    const activeCombatants = this.combatants.filter(c =>
        c.isAlive() &&
        !c.hasCondition("unconscious") &&
        !c.hasCondition("helpless") // Helpless can also mean out of combat
    );

    if (activeCombatants.length === 0) {
      this.log.addEntry("All combatants are defeated or incapacitated.");
      return true;
    }

    // Check factions if implemented, e.g. all PCs vs all NPCs
    const pcs = activeCombatants.filter(c => c.is_pc);
    const npcs = activeCombatants.filter(c => !c.is_pc);

    if (this.combatants.some(c => c.is_pc)) { // If there were PCs in the fight
        if (pcs.length === 0) {
            this.log.addEntry("All PCs are defeated.");
            return true;
        }
        if (npcs.length === 0) {
            this.log.addEntry("All hostile NPCs are defeated.");
            return true;
        }
    } else { // Monster vs Monster
        if (activeCombatants.length <= 1) {
            if (activeCombatants.length === 1) this.log.addEntry(`Only ${activeCombatants[0].name} remains.`);
            else this.log.addEntry("No one remains.");
            return true;
        }
    }
    return false;
  }

  endCombat(): void {
    if (!this.combatActive) return;
    this.combatActive = false;
    this.log.addEntry("\n=== COMBAT ENDS ===");
    this.log.addEntry("Final Status:");
    this.combatants.forEach(c => {
      let status = "OK";
      if (c.isDead()) status = "DEAD";
      else if (c.hasCondition("unconscious")) status = "UNCONSCIOUS";
      else if (c.isDying()) status = "DYING";
      else if (c.isDisabled()) status = "DISABLED (0 HP)";
      this.log.addEntry(`  ${c.name}: ${c.current_hp}/${c.max_hp} HP (${status})`);
    });
    const roundsLasted = this.isSurpriseRound ? this.currentRound : Math.max(0, this.currentRound -1);
    this.log.addEntry(`Combat lasted ${roundsLasted} full round(s).`);
  }
}
