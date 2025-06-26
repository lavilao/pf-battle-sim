// Forward declaration for Combatant if needed, or use a simpler type like string/object for now
// import { Combatant } from "./combatant";

export class AttackResult {
  attacker_name: string; // Changed from attacker to attacker_name to avoid conflict if using Combatant type
  target_name: string;   // Changed from target to target_name
  attack_name: string;
  attack_roll: number;
  total_attack_bonus: number;
  target_ac: number;
  is_hit: boolean;
  is_critical_threat: boolean;
  is_critical_hit: boolean;
  damage_rolls: number[];
  total_damage: number;
  damage_taken: number; // Damage actually dealt after DR, resistances etc.
  special_effects: string[];

  constructor(attacker_name: string, target_name: string, attack_name: string) {
    this.attacker_name = attacker_name;
    this.target_name = target_name;
    this.attack_name = attack_name;
    this.attack_roll = 0;
    this.total_attack_bonus = 0;
    this.target_ac = 0;
    this.is_hit = false;
    this.is_critical_threat = false;
    this.is_critical_hit = false;
    this.damage_rolls = [];
    this.total_damage = 0;
    this.damage_taken = 0;
    this.special_effects = [];
  }
}
