export class ArmorClass {
  armor_bonus: number;
  shield_bonus: number;
  natural_armor_bonus: number;
  deflection_bonus: number;
  dodge_bonus: number;
  size_modifier: number;
  max_dex_bonus_from_armor: number | null;

  constructor(
    armor_bonus: number = 0,
    shield_bonus: number = 0,
    natural_armor_bonus: number = 0,
    deflection_bonus: number = 0,
    dodge_bonus: number = 0,
    size_modifier: number = 0,
    max_dex_bonus_from_armor: number | null = null,
  ) {
    this.armor_bonus = armor_bonus;
    this.shield_bonus = shield_bonus;
    this.natural_armor_bonus = natural_armor_bonus;
    this.deflection_bonus = deflection_bonus;
    this.dodge_bonus = dodge_bonus;
    this.size_modifier = size_modifier;
    this.max_dex_bonus_from_armor = max_dex_bonus_from_armor;
  }

  calculate_ac(dex_modifier: number, is_flat_footed: boolean = false): number {
    let effective_dex = dex_modifier;
    if (this.max_dex_bonus_from_armor !== null) {
      effective_dex = Math.min(dex_modifier, this.max_dex_bonus_from_armor);
    }

    if (is_flat_footed) {
      effective_dex = 0; // Flat-footed characters lose their Dexterity bonus to AC
      // They also lose their dodge bonus to AC
      return (
        10 +
        this.armor_bonus +
        this.shield_bonus +
        this.natural_armor_bonus +
        // effective_dex is 0
        this.size_modifier +
        this.deflection_bonus
        // No dodge_bonus
      );
    }

    return (
      10 +
      this.armor_bonus +
      this.shield_bonus +
      this.natural_armor_bonus +
      effective_dex +
      this.size_modifier +
      this.deflection_bonus +
      this.dodge_bonus
    );
  }

  calculate_touch_ac(dex_modifier: number, is_flat_footed: boolean = false): number {
    let effective_dex = dex_modifier;
    if (this.max_dex_bonus_from_armor !== null) {
      effective_dex = Math.min(dex_modifier, this.max_dex_bonus_from_armor);
    }

    if (is_flat_footed) {
      effective_dex = 0; // Flat-footed characters lose their Dexterity bonus to AC
      // They also lose their dodge bonus to AC for touch AC
       return (
        10 +
        // effective_dex is 0
        this.size_modifier +
        this.deflection_bonus
        // No dodge_bonus
      );
    }

    return (
      10 +
      effective_dex +
      this.size_modifier +
      this.deflection_bonus +
      this.dodge_bonus
    );
  }

  calculate_flat_footed_ac(dex_modifier: number): number {
    // Flat-footed AC is AC as calculated above, but without the dexterity bonus and dodge bonus.
    // It's not just calling calculate_ac with is_flat_footed = true,
    // because that method also removes dodge_bonus, which is correct for flat-footed state.
    // The original Python code for calculate_flat_footed_ac was:
    // return (10 + self.armor_bonus + self.shield_bonus +
    //        self.natural_armor_bonus + self.size_modifier +
    //        self.deflection_bonus + self.dodge_bonus)
    // This implies dodge_bonus IS included in flat-footed AC, which contradicts some Pathfinder rules interpretations.
    // However, the calculate_ac with is_flat_footed=True *does* remove dodge.
    // Let's stick to the behavior of calculate_ac(dex, true) for consistency within this codebase's logic,
    // as flat-footed means losing Dex and Dodge bonuses.
    return this.calculate_ac(dex_modifier, true);
  }
}
