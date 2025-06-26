import { DamageType, AttackType } from "./enums.ts";
import { Ability, AbilityShort } from "./abilityScores.ts"; // Assuming this will be created

export class Attack {
  name: string;
  damage_dice: string; // e.g., "1d8", "2d6"
  critical_threat_range: string; // e.g., "20", "19-20"
  critical_multiplier: string; // e.g., "x2", "x3"
  damage_type: DamageType;
  attack_type: AttackType;
  reach: number; // in feet
  associated_ability_for_attack: Ability | AbilityShort | string; // str or dex
  associated_ability_for_damage: Ability | AbilityShort | string;
  is_primary_natural_attack: boolean;
  special_qualities: string[];
  enhancement_bonus: number;

  constructor(
    name: string,
    damage_dice: string,
    critical_threat_range: string,
    critical_multiplier: string,
    damage_type: DamageType,
    attack_type: AttackType = AttackType.MELEE,
    reach: number = 5,
    associated_ability_for_attack: Ability | AbilityShort | string = "str",
    associated_ability_for_damage: Ability | AbilityShort | string = "str",
    is_primary_natural_attack: boolean = true,
    special_qualities: string[] = [],
    enhancement_bonus: number = 0,
  ) {
    this.name = name;
    this.damage_dice = damage_dice;
    this.critical_threat_range = critical_threat_range;
    this.critical_multiplier = critical_multiplier;
    this.damage_type = damage_type;
    this.attack_type = attack_type;
    this.reach = reach;
    this.associated_ability_for_attack = associated_ability_for_attack;
    this.associated_ability_for_damage = associated_ability_for_damage;
    this.is_primary_natural_attack = is_primary_natural_attack;
    this.special_qualities = special_qualities;
    this.enhancement_bonus = enhancement_bonus;
  }

  getThreatRange(): number[] {
    switch (this.critical_threat_range) {
      case "20":
        return [20];
      case "19-20":
        return [19, 20];
      case "18-20":
        return [18, 19, 20];
      default:
        // Potentially log a warning for an unrecognized range
        console.warn(`Unrecognized critical_threat_range: ${this.critical_threat_range}, defaulting to [20]`);
        return [20];
    }
  }

  getCritMultiplier(): number {
    switch (this.critical_multiplier) {
      case "x2":
        return 2;
      case "x3":
        return 3;
      case "x4":
        return 4;
      default:
        // Potentially log a warning for an unrecognized multiplier
        console.warn(`Unrecognized critical_multiplier: ${this.critical_multiplier}, defaulting to 2`);
        return 2;
    }
  }
}
