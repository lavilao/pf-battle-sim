import { AbilityScores } from "./abilityScores.ts";

export type SaveType = "fortitude" | "reflex" | "will";

export class SavingThrows {
  fortitude_base: number;
  reflex_base: number;
  will_base: number;

  constructor(
    fortitude_base: number = 0,
    reflex_base: number = 0,
    will_base: number = 0,
  ) {
    this.fortitude_base = fortitude_base;
    this.reflex_base = reflex_base;
    this.will_base = will_base;
  }

  calculateSave(save_type: SaveType, ability_scores: AbilityScores): number {
    let base: number;
    let ability_modifier: number;

    switch (save_type) {
      case "fortitude":
        base = this.fortitude_base;
        ability_modifier = ability_scores.getModifier("constitution");
        break;
      case "reflex":
        base = this.reflex_base;
        ability_modifier = ability_scores.getModifier("dexterity");
        break;
      case "will":
        base = this.will_base;
        ability_modifier = ability_scores.getModifier("wisdom");
        break;
      default:
        // Should not happen with SaveType, but as a fallback:
        console.warn(`Unknown save type: ${save_type}`);
        return 0;
    }
    return base + ability_modifier;
  }
}
