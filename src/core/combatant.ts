import { AbilityScores, Ability, AbilityShort } from "./abilityScores.ts";
import { ArmorClass } from "./armorClass.ts";
import { Attack } from "./attack.ts";
import { SavingThrows, SaveType } from "./savingThrows.ts";
import { AttackType, DamageType } from "./enums.ts";

// Helper for dice rolling
function rollDice(numDice: number, dieSize: number): number {
  let total = 0;
  for (let i = 0; i < numDice; i++) {
    total += Math.floor(Math.random() * dieSize) + 1;
  }
  return total;
}

export interface CombatantData {
  name: string;
  is_pc?: boolean;
  max_hp?: number;
  ability_scores?: {
    strength?: number;
    dexterity?: number;
    constitution?: number;
    intelligence?: number;
    wisdom?: number;
    charisma?: number;
  };
  base_attack_bonus?: number;
  armor_class?: {
    armor_bonus?: number;
    shield_bonus?: number;
    natural_armor_bonus?: number;
    deflection_bonus?: number;
    dodge_bonus?: number;
    size_modifier?: number; // Was missing in Python from_dict, but present in AC definition
    max_dex_bonus_from_armor?: number | null;
  };
  saving_throws?: {
    fortitude_base?: number;
    reflex_base?: number;
    will_base?: number;
  };
  base_speed?: number;
  size?: string;
  creature_type?: string;
  subtypes?: string[];
  alignment?: string;
  skills?: Record<string, number>;
  feats?: string[];
  attacks?: Array<{
    name: string;
    damage_dice: string;
    critical_threat_range: string;
    critical_multiplier: string;
    damage_type: DamageType;
    attack_type?: AttackType;
    reach?: number;
    associated_ability_for_attack?: Ability | AbilityShort | string;
    associated_ability_for_damage?: Ability | AbilityShort | string;
    is_primary_natural_attack?: boolean;
    special_qualities?: string[];
    enhancement_bonus?: number;
  }>;
  damage_reduction?: Record<string, any>; // e.g., {"amount": 5, "type": "magic"}
  spell_resistance?: number;
  energy_resistances?: Record<string, number>; // e.g., {"fire": 10, "cold": 5}
  energy_immunities?: string[];
  energy_vulnerabilities?: string[];
  // Fields not typically in JSON but part of class
  player_controller?: string;
  unique_id?: string;
  fly_speed?: number;
  swim_speed?: number;
  climb_speed?: number;
  burrow_speed?: number;
  fly_maneuverability?: string;
  caster_level?: number;
  spellcasting_ability?: Ability | AbilityShort | string;
  spells_per_day?: Record<number, number>;
  known_spells?: Record<number, string[]>;
  prepared_spells?: Record<number, string[]>;
  spell_dc_base?: number;
  metamagic_feats?: string[];
  mythic_tier?: number;
  mythic_path?: string;
  mythic_power_points?: number;
  mythic_abilities?: string[];
  mythic_feats?: string[];
  equipment_slots?: Record<string, string | null | undefined>;
}


export class Combatant {
  // Identification
  name: string;
  is_pc: boolean;
  player_controller: string;
  unique_id: string;

  // Core Stats
  max_hp: number;
  current_hp: number;
  temporary_hp: number;

  // Ability Scores
  ability_scores: AbilityScores;

  // Combat Stats - Offense
  base_attack_bonus: number;
  attacks: Attack[];

  // Combat Stats - Defense
  armor_class: ArmorClass;
  damage_reduction: Record<string, any>; // e.g., {"amount": 5, "type": "magic"}
  spell_resistance: number;
  energy_resistances: Record<string, number>; // e.g., {"fire": 10, "cold": 5}
  energy_immunities: string[];
  energy_vulnerabilities: string[];

  // Movement
  base_speed: number;
  fly_speed: number;
  swim_speed: number;
  climb_speed: number;
  burrow_speed: number;
  fly_maneuverability: string;

  // Saving Throws
  saving_throws: SavingThrows;

  // Skills (dictionary of skill_name: total_modifier)
  skills: Record<string, number>;

  // Feats
  feats: string[];

  // Special Abilities
  special_abilities: Array<Record<string, any>>;

  // Spellcasting
  caster_level: number;
  spellcasting_ability: Ability | AbilityShort | string;
  spells_per_day: Record<number, number>;
  known_spells: Record<number, string[]>;
  prepared_spells: Record<number, string[]>;
  spell_dc_base: number;
  metamagic_feats: string[];

  // Size and Type
  size: string; // e.g. "Medium", "Large"
  creature_type: string;
  subtypes: string[];
  alignment: string;

  // Initiative
  initiative_modifier: number;
  current_initiative_roll: number;
  final_initiative_score: number;

  // Mythic (placeholders)
  mythic_tier: number;
  mythic_path: string;
  mythic_power_points: number;
  mythic_abilities: string[];
  mythic_feats: string[];

  // Combat State
  conditions: Set<string>;
  is_flat_footed: boolean;
  has_acted_this_combat: boolean;
  aoo_made_this_round: number;
  has_moved_this_turn: boolean; // For 5-foot step tracking

  // Equipment
  equipment_slots: Record<string, string | null | undefined>;

  constructor(name: string, is_pc: boolean = false) {
    this.name = name;
    this.is_pc = is_pc;
    this.player_controller = "";
    this.unique_id = ""; // Should be generated later

    this.max_hp = 1;
    this.current_hp = 1;
    this.temporary_hp = 0;

    this.ability_scores = new AbilityScores();
    this.base_attack_bonus = 0;
    this.attacks = [];

    this.armor_class = new ArmorClass();
    this.damage_reduction = {};
    this.spell_resistance = 0;
    this.energy_resistances = {};
    this.energy_immunities = [];
    this.energy_vulnerabilities = [];

    this.base_speed = 30;
    this.fly_speed = 0;
    this.swim_speed = 0;
    this.climb_speed = 0;
    this.burrow_speed = 0;
    this.fly_maneuverability = "average";

    this.saving_throws = new SavingThrows();
    this.skills = {};
    this.feats = [];
    this.special_abilities = [];

    this.caster_level = 0;
    this.spellcasting_ability = "intelligence";
    this.spells_per_day = {};
    this.known_spells = {};
    this.prepared_spells = {};
    this.spell_dc_base = 10;
    this.metamagic_feats = [];

    this.size = "Medium";
    this.creature_type = "Humanoid";
    this.subtypes = [];
    this.alignment = "True Neutral";

    this.initiative_modifier = 0; // Will be calculated
    this.current_initiative_roll = 0;
    this.final_initiative_score = 0;

    this.mythic_tier = 0;
    this.mythic_path = "";
    this.mythic_power_points = 0;
    this.mythic_abilities = [];
    this.mythic_feats = [];

    this.conditions = new Set<string>();
    this.is_flat_footed = true;
    this.has_acted_this_combat = false;
    this.aoo_made_this_round = 0;
    this.has_moved_this_turn = false;

    this.equipment_slots = {
      main_hand: null,
      off_hand: null,
      armor: null,
      belt: null,
      eyes: null,
      feet: null,
      hands: null,
      head: null,
      neck: null,
      ring1: null,
      ring2: null,
      shoulders: null,
      wrists: null,
    };
    this.recalculateInitiativeModifier();
  }

  recalculateInitiativeModifier(): void {
    this.initiative_modifier = this.ability_scores.getModifier("dexterity");
    // TODO: Add other initiative bonuses (feats like Improved Initiative, traits, etc.)
  }

  getSizeModifier(): number {
    const sizeModifiers: Record<string, number> = {
      "Fine": 8, "Diminutive": 4, "Tiny": 2, "Small": 1,
      "Medium": 0, "Large": -1, "Huge": -2,
      "Gargantuan": -4, "Colossal": -8,
    };
    return sizeModifiers[this.size] ?? 0;
  }

  getSpecialSizeModifierForCMB_CMD(): number {
    const sizeMap: Record<string, number> = {
      "Fine": -8, "Diminutive": -4, "Tiny": -2, "Small": -1,
      "Medium": 0, "Large": 1, "Huge": 2, "Gargantuan": 4, "Colossal": 8,
    };
    return sizeMap[this.size] ?? 0;
  }

  calculateCMB(): number {
    const bab = this.base_attack_bonus;
    let ability_mod: number;

    if (["Fine", "Diminutive", "Tiny"].includes(this.size)) {
      ability_mod = this.ability_scores.getModifier("dexterity");
    } else {
      ability_mod = this.ability_scores.getModifier("strength");
    }
    const special_size_mod = this.getSpecialSizeModifierForCMB_CMD();
    // TODO: Add other modifiers from feats, spells, etc.
    return bab + ability_mod + special_size_mod;
  }

  calculateCMD(): number {
    const bab = this.base_attack_bonus;
    let str_mod = this.ability_scores.getModifier("strength");
    let dex_mod = this.ability_scores.getModifier("dexterity");
    const special_size_mod = this.getSpecialSizeModifierForCMB_CMD();

    let cmd = 10 + bab + str_mod + dex_mod + special_size_mod;
    cmd += this.armor_class.deflection_bonus;
    // Dodge bonus is lost if flat-footed or denied Dex.
    // If is_flat_footed, dex_mod effectively becomes 0 for CMD.
    // The Python code had a complex handling for flat-footed CMD.
    // Rule: "A flat-footed creature ... does not add its Dexterity bonus to its CMD."
    // "It also denies its Dexterity bonus to AC."
    // "A flat-footed creature also loses its dodge bonus to AC (if any)." (Core Rulebook p.179)
    // So, if flat-footed, no Dex bonus (if positive) and no dodge bonus.

    const isDeniedDex = this.is_flat_footed || this.hasCondition("helpless") || this.hasCondition("stunned") || this.hasCondition("paralyzed") || this.hasCondition("pinned");

    if (isDeniedDex) {
        if (dex_mod > 0) { // Only remove positive dexterity bonus
            cmd -= dex_mod;
        }
        // Dodge bonus is also lost
    } else {
        cmd += this.armor_class.dodge_bonus; // Add dodge bonus if not denied Dex
    }

    // TODO: Add other applicable AC bonuses (insight, luck, morale, profane, sacred)
    // TODO: Apply penalties to AC to CMD as well.
    return cmd;
  }


  getAC(ac_type: "standard" | "touch" | "flat_footed" = "standard"): number {
    const dex_mod = this.ability_scores.getModifier("dexterity");
    const general_size_mod = this.getSizeModifier(); // This is the attack/AC size modifier

    const isEffectivelyFlatFooted = this.is_flat_footed ||
                                   this.hasCondition("helpless") ||
                                   this.hasCondition("stunned") ||
                                   this.hasCondition("paralyzed") ||
                                   this.hasCondition("cowering") || // Cowering means you lose Dex to AC
                                   this.hasCondition("blinded");   // Blinded creatures are effectively flat-footed

    let ac: number;

    if (ac_type === "touch") {
      ac = this.armor_class.calculate_touch_ac(dex_mod, isEffectivelyFlatFooted);
    } else if (ac_type === "flat_footed" || isEffectivelyFlatFooted) {
      // Pass current dex_mod, calculate_flat_footed_ac will ignore it if it's positive
      ac = this.armor_class.calculate_flat_footed_ac(dex_mod);
    } else { // standard AC
      ac = this.armor_class.calculate_ac(dex_mod, isEffectivelyFlatFooted);
    }

    ac += general_size_mod; // Apply general size modifier to AC

    // Condition-based AC penalties / modifications
    if (this.hasCondition("blinded")) { // Already handled by isEffectivelyFlatFooted for Dex/Dodge loss
      ac -= 2; // Specific penalty for being blinded
    }
    if (this.hasCondition("cowering")) { // Loses Dex bonus (handled by isEffectivelyFlatFooted)
      ac -= 2; // Specific penalty for cowering
    }
    if (this.hasCondition("helpless")) { // Loses Dex bonus (handled)
        // The -4 AC vs melee for helpless is tricky. It's not a general AC penalty.
        // It should be applied by the attacker if they are melee.
        // For now, we won't apply it directly to the general AC value here.
    }
    if (this.hasCondition("pinned")) { // Loses Dex bonus (handled by isEffectivelyFlatFooted if we add pinned to that list)
         ac -= 4; // Specific -4 AC for pinned.
    }
    // Prone is handled by attacker: +4 AC vs ranged, -4 AC vs melee for target. Not here.
    if (this.hasCondition("stunned")) { // Loses Dex bonus (handled)
      ac -= 2; // Specific penalty for stunned
    }

    return ac;
  }

  getAttackBonus(attack: Attack, is_full_attack: boolean = false, attack_number: number = 0, _target?: Combatant): number {
    const ability_to_use = attack.associated_ability_for_attack;

    let effective_str_mod = this.ability_scores.getModifier("strength");
    let effective_dex_mod = this.ability_scores.getModifier("dexterity");

    if (this.hasCondition("exhausted")) {
      effective_str_mod -= 3;
      effective_dex_mod -= 3;
    } else if (this.hasCondition("fatigued")) {
      effective_str_mod -= 1;
      effective_dex_mod -= 1;
    }
    if (this.hasCondition("entangled")) { // -4 dex
         effective_dex_mod -= 2; // -4 to score is -2 to mod
    }

    let ability_mod: number;
    if (ability_to_use === "str" || ability_to_use === "strength") {
      ability_mod = effective_str_mod;
    } else if (ability_to_use === "dex" || ability_to_use === "dexterity") {
      ability_mod = effective_dex_mod;
    } else {
      ability_mod = this.ability_scores.getModifier(ability_to_use);
    }

    const size_mod = this.getSizeModifier();
    let bab = this.base_attack_bonus;
    if (is_full_attack && attack_number > 0) {
      bab -= attack_number * 5;
    }

    let total_bonus = bab + ability_mod + size_mod + attack.enhancement_bonus;

    if (this.hasCondition("dazzled")) total_bonus -= 1;
    if (this.hasCondition("entangled")) total_bonus -= 2; // Stacks with Dex penalty for attack rolls
    if (this.hasCondition("frightened") || this.hasCondition("shaken")) total_bonus -= 2;
    if (this.hasCondition("grappled")) total_bonus -= 2;

    if (this.hasCondition("prone")) {
        if (attack.attack_type === AttackType.MELEE) {
            total_bonus -= 4;
        } else if (attack.attack_type === AttackType.RANGED) {
            // Most ranged attacks cannot be used while prone. Crossbows/shuriken are exceptions.
            // For simplicity, we assume an attack made here IS possible (e.g. crossbow).
            // Pathfinder Core Rulebook p.193: "If you are prone, you can usually only make melee attacks or fire a crossbow or shuriken."
            // No explicit penalty listed for these allowed ranged attacks, but being prone is generally bad.
            // The Python code had a heavy penalty. Let's omit a direct penalty here, assuming the attack is valid.
            // The target being prone gives them +4 AC vs ranged, handled on their side.
        }
    }
    if (this.hasCondition("sickened")) total_bonus -= 2;
    // Conditions like Stunned, Helpless, Nauseated, Paralyzed prevent attacks.

    return total_bonus;
  }

  getDamageBonus(attack: Attack, is_off_hand: boolean = false, is_two_handed: boolean = false): number {
    const ability_to_use = attack.associated_ability_for_damage;
    let ability_mod = this.ability_scores.getModifier(ability_to_use);

    if (ability_to_use === "strength" || ability_to_use === "str") {
      if (this.hasCondition("exhausted")) ability_mod -= 3;
      else if (this.hasCondition("fatigued")) ability_mod -= 1;
    }

    if (ability_to_use === "strength" || ability_to_use === "str") {
      if (is_off_hand) {
        ability_mod = Math.floor(ability_mod * 0.5); // Pathfinder: 1/2 Str for off-hand
      } else if (is_two_handed && !["Small", "Tiny", "Diminutive", "Fine"].includes(this.size)) {
        ability_mod = Math.floor(ability_mod * 1.5); // 1.5 Str for two-handed
      }
      // Primary natural attacks get full Str. Secondary natural attacks get 1/2 Str.
      // This needs more specific handling if we differentiate primary/secondary natural attacks.
      // For now, assuming generic weapon or primary natural.
    }

    let damage_bonus = ability_mod + attack.enhancement_bonus;
    if (this.hasCondition("sickened")) damage_bonus -= 2;
    return damage_bonus;
  }

  rollDamage(attack: Attack, is_critical: boolean = false, is_off_hand: boolean = false, is_two_handed: boolean = false): {totalDamage: number, rolls: number[]} {
    const dice_parts = attack.damage_dice.match(/(\d+)d(\d+)/);
    if (!dice_parts || dice_parts.length !== 3) return {totalDamage: 1, rolls: [1]};

    const num_dice = parseInt(dice_parts[1], 10);
    const die_size = parseInt(dice_parts[2], 10);

    let base_damage_rolls: number[] = [];
    let base_damage_sum = 0;
    for (let i = 0; i < num_dice; i++) {
        const roll = rollDice(1, die_size);
        base_damage_rolls.push(roll);
        base_damage_sum += roll;
    }

    const damage_bonus = this.getDamageBonus(attack, is_off_hand, is_two_handed);
    let final_damage: number;

    if (is_critical) {
      const multiplier = attack.getCritMultiplier();
      let crit_damage_sum = base_damage_sum;
      // Roll additional dice for critical hit (Pathfinder: multiply weapon dice rolls, not just sum)
      for (let m = 1; m < multiplier; m++) {
          for (let i = 0; i < num_dice; i++) {
              const roll = rollDice(1, die_size);
              base_damage_rolls.push(roll); // Log all rolls
              crit_damage_sum += roll;
          }
      }
      // Add bonus damage, multiplied by number of damage dice sets for some interpretations,
      // or simply added once and then the total (dice+bonus) multiplied.
      // Pathfinder: "Multiply the damage dealt by the weapon’s critical multiplier."
      // "Exception: Precision damage (such as from a rogue’s sneak attack class feature) and
      //  damage dice from special weapon abilities (such as flaming) are not multiplied when you score a critical hit."
      // Assuming damage_bonus here is standard (e.g. Str, enhancement) and *is* multiplied.
      final_damage = crit_damage_sum + (damage_bonus * multiplier);

    } else {
      final_damage = base_damage_sum + damage_bonus;
    }

    return {totalDamage: Math.max(1, final_damage), rolls: base_damage_rolls};
  }

  getThreatenedSquares(_current_position: [number, number]): [number, number][] {
    // Placeholder - needs grid system
    // For now, assume 5ft reach threatens adjacent squares
    const threatened: [number, number][] = [];
    // const [x,y] = current_position;
    // if (this.attacks.some(att => att.reach >=5 && (att.attack_type === AttackType.MELEE || att.attack_type === AttackType.NATURAL))) {
    //     for (let dx of [-1,0,1]) {
    //         for (let dy of [-1,0,1]) {
    //             if (dx === 0 && dy === 0) continue;
    //             threatened.push([x+dx, y+dy]);
    //         }
    //     }
    // }
    return threatened;
  }

  takeDamage(damage: number, damage_type: DamageType | string = "untyped"): number {
    let effective_damage = damage;

    if (this.damage_reduction && this.damage_reduction.amount) {
      const dr_amount = this.damage_reduction.amount;
      // TODO: DR type checking (e.g. /magic, /cold_iron)
      effective_damage = Math.max(0, effective_damage - dr_amount);
    }

    if (this.energy_resistances[damage_type as string]) {
      effective_damage = Math.max(0, effective_damage - this.energy_resistances[damage_type as string]);
    }
    if (this.energy_immunities.includes(damage_type as string)) {
      effective_damage = 0;
    }
    if (this.energy_vulnerabilities.includes(damage_type as string)) {
      effective_damage *= 2;
    }

    if (this.temporary_hp > 0) {
      const temp_damage = Math.min(effective_damage, this.temporary_hp);
      this.temporary_hp -= temp_damage;
      effective_damage -= temp_damage;
    }

    this.current_hp -= effective_damage;
    const con_score = this.ability_scores.getTotalScore("constitution");

    if (this.current_hp <= 0 && this.current_hp > -con_score) {
        this.removeCondition("stable"); // If they were stable and took damage
        if (this.current_hp === 0) {
            this.addCondition("disabled");
            this.removeCondition("dying");
        } else { // current_hp < 0
            this.addCondition("dying");
            this.removeCondition("disabled");
        }
    } else if (this.current_hp <= -con_score) {
        this.addCondition("dead");
        this.removeCondition("dying");
        this.removeCondition("disabled");
        this.removeCondition("stable");
        this.current_hp = -con_score; // HP doesn't go below this threshold by rule
    }

    return effective_damage; // Return damage actually dealt to HP (after temp HP)
  }

  isAlive(): boolean {
    return !this.hasCondition("dead");
  }

  isDisabled(): boolean {
    return this.hasCondition("disabled") && this.isAlive();
  }

  isDying(): boolean {
    return this.hasCondition("dying") && this.isAlive();
  }

  isDead(): boolean {
    return this.hasCondition("dead");
  }

  stabilize(): boolean {
    if (!this.isDying()) return false;

    const penalty = Math.abs(this.current_hp);
    const roll = rollDice(1, 20);
    const con_mod = this.ability_scores.getModifier("constitution"); // DC is 10 + penalty OR 10 + Con mod + penalty for some interpretations. PF Core says DC 10 + negative HP as penalty.
                                                                    // Let's use DC 15 for a different flavor, or DC based on Con.
                                                                    // PF Core: "Each round on his turn, a dying character must make a DC 10 Constitution check to become stable."
                                                                    // "He takes a penalty on this roll equal to his negative hit point total."
    // So, it's a Con check (d20 + Con_mod) vs DC 10, with penalty of negative HP.
    // Or, d20 vs DC (10 + penalty), where character rolls d20 + Con_mod.
    // The Python code did: roll - penalty >= 10. This implies d20 vs DC (10+penalty). This is correct.
    // Let's re-implement that specific logic.

    if (roll === 20) { // Nat 20 on stabilize check
        this.addCondition("stable");
        this.removeCondition("dying");
        return true;
    }
    if (roll === 1) { // Nat 1 on stabilize check
        this.current_hp -=1; // Lose 1 HP
        // Check for death
        if (this.current_hp <= -this.ability_scores.getTotalScore("constitution")) {
            this.addCondition("dead");
            this.removeCondition("dying");
            this.removeCondition("stable");
        }
        return false;
    }

    // Check is d20 + Con_mod vs DC (10 + penalty from negative HP)
    // No, the rule is: "Constitution check to become stable. ... takes a penalty on this roll equal to his negative hit point total."
    // So, (d20 + Con_mod - penalty) vs DC 10.
    const conCheckValue = roll + con_mod - penalty;

    if (conCheckValue >= 10) {
      this.addCondition("stable");
      this.removeCondition("dying");
      return true;
    } else {
      this.current_hp -= 1; // Failed stabilization, lose 1 HP
      if (this.current_hp <= -this.ability_scores.getTotalScore("constitution")) {
        this.addCondition("dead");
        this.removeCondition("dying");
        this.removeCondition("stable");
      }
      return false;
    }
  }

  heal(amount: number): number {
    const old_hp = this.current_hp;
    this.current_hp = Math.min(this.max_hp, this.current_hp + amount);
    if (this.current_hp > 0) {
      this.removeCondition("disabled");
      this.removeCondition("dying");
      this.removeCondition("stable");
    } else if (this.current_hp === 0 && this.isAlive()) { // Healed to exactly 0 HP
      this.addCondition("disabled");
      this.removeCondition("dying");
      this.removeCondition("stable");
    }
    return this.current_hp - old_hp;
  }

  makeSavingThrow(save_type: SaveType, dc: number, _source_effect_name: string = "Unknown Effect"): boolean {
    const save_bonus = this.saving_throws.calculateSave(save_type, this.ability_scores);
    const roll = rollDice(1, 20);
    // const total_roll = roll + save_bonus; // Logged in Python, not directly used for success check

    if (roll === 1) return false; // Natural 1 always fails
    if (roll === 20) return true;  // Natural 20 always succeeds (unless vs. irresistible effect)

    return (roll + save_bonus) >= dc;
  }

  addCondition(condition: string): void {
    this.conditions.add(condition.toLowerCase());
    // TODO: Apply immediate effects of condition if any (e.g. prone makes you fall)
    // More complex conditions might require an event system or callbacks.
  }

  removeCondition(condition: string): void {
    this.conditions.delete(condition.toLowerCase());
    // TODO: Remove effects of condition
  }

  hasCondition(condition: string): boolean {
    return this.conditions.has(condition.toLowerCase());
  }

  resetForCombat(): void {
    this.current_hp = this.max_hp;
    this.temporary_hp = 0;
    this.conditions.clear();
    this.is_flat_footed = true;
    this.has_acted_this_combat = false;
    this.current_initiative_roll = 0;
    this.final_initiative_score = 0;
    this.aoo_made_this_round = 0;
    this.has_moved_this_turn = false;
    // Temp ability score damage/drain should also be reset if not persistent.
  }

  toData(): CombatantData {
    return {
      name: this.name,
      is_pc: this.is_pc,
      max_hp: this.max_hp,
      ability_scores: {
        strength: this.ability_scores.strength,
        dexterity: this.ability_scores.dexterity,
        constitution: this.ability_scores.constitution,
        intelligence: this.ability_scores.intelligence,
        wisdom: this.ability_scores.wisdom,
        charisma: this.ability_scores.charisma,
      },
      base_attack_bonus: this.base_attack_bonus,
      armor_class: {
        armor_bonus: this.armor_class.armor_bonus,
        shield_bonus: this.armor_class.shield_bonus,
        natural_armor_bonus: this.armor_class.natural_armor_bonus,
        deflection_bonus: this.armor_class.deflection_bonus,
        dodge_bonus: this.armor_class.dodge_bonus,
        size_modifier: this.armor_class.size_modifier,
        max_dex_bonus_from_armor: this.armor_class.max_dex_bonus_from_armor,
      },
      saving_throws: {
        fortitude_base: this.saving_throws.fortitude_base,
        reflex_base: this.saving_throws.reflex_base,
        will_base: this.saving_throws.will_base,
      },
      base_speed: this.base_speed,
      size: this.size,
      creature_type: this.creature_type,
      subtypes: [...this.subtypes],
      alignment: this.alignment,
      skills: { ...this.skills },
      feats: [...this.feats],
      attacks: this.attacks.map(attack => ({
        name: attack.name,
        damage_dice: attack.damage_dice,
        critical_threat_range: attack.critical_threat_range,
        critical_multiplier: attack.critical_multiplier,
        damage_type: attack.damage_type,
        attack_type: attack.attack_type,
        reach: attack.reach,
        associated_ability_for_attack: attack.associated_ability_for_attack,
        associated_ability_for_damage: attack.associated_ability_for_damage,
        is_primary_natural_attack: attack.is_primary_natural_attack,
        special_qualities: [...attack.special_qualities],
        enhancement_bonus: attack.enhancement_bonus,
      })),
      damage_reduction: { ...this.damage_reduction },
      spell_resistance: this.spell_resistance,
      energy_resistances: { ...this.energy_resistances },
      energy_immunities: [...this.energy_immunities],
      energy_vulnerabilities: [...this.energy_vulnerabilities],
      // Non-serialized operational fields (can be added if needed for specific save/load scenarios)
      player_controller: this.player_controller,
      unique_id: this.unique_id,
      fly_speed: this.fly_speed,
      // ... other operational fields
    };
  }

  static fromData(data: CombatantData): Combatant {
    const combatant = new Combatant(data.name, data.is_pc ?? false);

    combatant.max_hp = data.max_hp ?? 1;
    combatant.current_hp = combatant.max_hp; // Start at full HP when loading from data
    combatant.base_attack_bonus = data.base_attack_bonus ?? 0;
    combatant.base_speed = data.base_speed ?? 30;
    combatant.size = data.size ?? "Medium";
    combatant.creature_type = data.creature_type ?? "Humanoid";
    combatant.subtypes = data.subtypes ? [...data.subtypes] : [];
    combatant.alignment = data.alignment ?? "True Neutral";
    combatant.skills = data.skills ? { ...data.skills } : {};
    combatant.feats = data.feats ? [...data.feats] : [];
    combatant.damage_reduction = data.damage_reduction ? { ...data.damage_reduction } : {};
    combatant.spell_resistance = data.spell_resistance ?? 0;
    combatant.energy_resistances = data.energy_resistances ? { ...data.energy_resistances } : {};
    combatant.energy_immunities = data.energy_immunities ? [...data.energy_immunities] : [];
    combatant.energy_vulnerabilities = data.energy_vulnerabilities ? [...data.energy_vulnerabilities] : [];

    // Optional operational fields from CombatantData (if they were included)
    if (data.player_controller) combatant.player_controller = data.player_controller;
    if (data.unique_id) combatant.unique_id = data.unique_id;
    combatant.fly_speed = data.fly_speed ?? 0;
    // ... etc for other operational fields in CombatantData

    if (data.ability_scores) {
      const abs = data.ability_scores;
      combatant.ability_scores = new AbilityScores(
        abs.strength ?? 10, abs.dexterity ?? 10, abs.constitution ?? 10,
        abs.intelligence ?? 10, abs.wisdom ?? 10, abs.charisma ?? 10
      );
    }
    combatant.recalculateInitiativeModifier(); // Recalculate based on loaded Dex

    if (data.armor_class) {
      const ac = data.armor_class;
      combatant.armor_class = new ArmorClass(
        ac.armor_bonus ?? 0, ac.shield_bonus ?? 0, ac.natural_armor_bonus ?? 0,
        ac.deflection_bonus ?? 0, ac.dodge_bonus ?? 0,
        ac.size_modifier ?? combatant.getSizeModifier(), // Use calculated if not provided
        ac.max_dex_bonus_from_armor === undefined ? null : ac.max_dex_bonus_from_armor
      );
      // Note: Python AC had size_modifier field, but from_dict didn't load it.
      // Here, we ensure it's set, either from data or calculated.
      // If the size_modifier in AC is meant to be distinct from the combatant's general size modifier,
      // this needs clarification. For now, assume it's the general one if not specified.
      // However, AC.size_modifier is usually 0 as the general size_modifier is applied on top.
      // Let's default AC's own size_modifier to 0 unless explicitly provided.
      combatant.armor_class.size_modifier = ac.size_modifier ?? 0;

    } else {
        // Ensure AC's size modifier is correctly initialized if no AC data provided
        combatant.armor_class.size_modifier = 0; // Default for AC component itself
    }


    if (data.saving_throws) {
      const saves = data.saving_throws;
      combatant.saving_throws = new SavingThrows(
        saves.fortitude_base ?? 0, saves.reflex_base ?? 0, saves.will_base ?? 0
      );
    }

    if (data.attacks) {
      combatant.attacks = data.attacks.map(att_data => new Attack(
        att_data.name,
        att_data.damage_dice,
        att_data.critical_threat_range,
        att_data.critical_multiplier,
        att_data.damage_type, // Already a DamageType enum from JSON parsing
        att_data.attack_type ?? AttackType.MELEE,
        att_data.reach ?? 5,
        att_data.associated_ability_for_attack ?? "str",
        att_data.associated_ability_for_damage ?? "str",
        att_data.is_primary_natural_attack ?? true,
        att_data.special_qualities ? [...att_data.special_qualities] : [],
        att_data.enhancement_bonus ?? 0
      ));
    }
    return combatant;
  }
}
