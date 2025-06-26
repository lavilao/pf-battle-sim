export type Ability = "strength" | "dexterity" | "constitution" | "intelligence" | "wisdom" | "charisma";
export type AbilityShort = "str" | "dex" | "con" | "int" | "wis" | "cha";

export class AbilityScores {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;

  temp_str: number;
  temp_dex: number;
  temp_con: number;
  temp_int: number;
  temp_wis: number;
  temp_cha: number;

  constructor(
    strength: number = 10,
    dexterity: number = 10,
    constitution: number = 10,
    intelligence: number = 10,
    wisdom: number = 10,
    charisma: number = 10,
    temp_str: number = 0,
    temp_dex: number = 0,
    temp_con: number = 0,
    temp_int: number = 0,
    temp_wis: number = 0,
    temp_cha: number = 0,
  ) {
    this.strength = strength;
    this.dexterity = dexterity;
    this.constitution = constitution;
    this.intelligence = intelligence;
    this.wisdom = wisdom;
    this.charisma = charisma;
    this.temp_str = temp_str;
    this.temp_dex = temp_dex;
    this.temp_con = temp_con;
    this.temp_int = temp_int;
    this.temp_wis = temp_wis;
    this.temp_cha = temp_cha;
  }

  private mapAbilityKey(ability: Ability | AbilityShort | string): { baseKey: Ability, tempKey: keyof this } {
    const lowerAbility = ability.toLowerCase();
    switch (lowerAbility) {
      case "str":
      case "strength":
        return { baseKey: "strength", tempKey: "temp_str" };
      case "dex":
      case "dexterity":
        return { baseKey: "dexterity", tempKey: "temp_dex" };
      case "con":
      case "constitution":
        return { baseKey: "constitution", tempKey: "temp_con" };
      case "int":
      case "intelligence":
        return { baseKey: "intelligence", tempKey: "temp_int" };
      case "wis":
      case "wisdom":
        return { baseKey: "wisdom", tempKey: "temp_wis" };
      case "cha":
      case "charisma":
        return { baseKey: "charisma", tempKey: "temp_cha" };
      default:
        throw new Error(`Invalid ability score: ${ability}`);
    }
  }

  getModifier(ability: Ability | AbilityShort | string): number {
    const totalScore = this.getTotalScore(ability);
    return Math.floor((totalScore - 10) / 2);
  }

  getTotalScore(ability: Ability | AbilityShort | string): number {
    const { baseKey, tempKey } = this.mapAbilityKey(ability);
    const baseValue = this[baseKey] as number; // Type assertion
    const tempValue = this[tempKey] as number; // Type assertion
    return baseValue + tempValue;
  }
}
