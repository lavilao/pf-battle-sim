/**
 * Rolls dice based on a dice string notation.
 * e.g., "1d8", "2d6+1", "1d20-2".
 * Returns the total result of the roll.
 * Returns 0 if the dice string is invalid.
 */
export function rollDiceString(diceString: string): number {
  if (!diceString || typeof diceString !== 'string') {
    console.error("Invalid diceString input: must be a non-empty string.");
    return 0;
  }

  const mainParts = diceString.toLowerCase().split(/([+-])/);
  let total = 0;

  // Process the first part, which should be the dice roll (e.g., "2d6")
  const dicePart = mainParts[0];
  if (dicePart.includes('d')) {
    const [numDiceStr, dieSizeStr] = dicePart.split('d');
    const numDice = parseInt(numDiceStr, 10);
    const dieSize = parseInt(dieSizeStr, 10);

    if (isNaN(numDice) || isNaN(dieSize) || numDice <= 0 || dieSize <= 0) {
      console.error(`Invalid dice format in rollDiceString: ${dicePart}`);
      return 0;
    }

    for (let i = 0; i < numDice; i++) {
      total += Math.floor(Math.random() * dieSize) + 1;
    }
  } else {
    // If no 'd', it might be a flat number, e.g. "5" as part of "5+1d6" (though our split handles it differently)
    // Or the initial part is just a number like in "10"
    const flatNumber = parseInt(dicePart, 10);
    if (isNaN(flatNumber)) {
      console.error(`Invalid initial part (not a dice roll or number) in rollDiceString: ${dicePart}`);
      return 0;
    }
    total += flatNumber;
  }

  // Process bonuses/penalties
  for (let i = 1; i < mainParts.length; i += 2) {
    const operator = mainParts[i];
    const valueStr = mainParts[i + 1];
    if (!valueStr) {
        console.error(`Missing value after operator ${operator} in rollDiceString: ${diceString}`);
        return 0; // Or handle as error appropriately
    }
    const value = parseInt(valueStr, 10);

    if (isNaN(value)) {
      console.error(`Invalid bonus/penalty value in rollDiceString: ${valueStr}`);
      return 0; // Or handle as error
    }

    if (operator === '+') {
      total += value;
    } else if (operator === '-') {
      total -= value;
    }
  }
  // Pathfinder rule: "If penalties reduce the damage result to less than 1, a hit still deals 1 point of nonlethal damage."
  // This function is generic for dice rolling, not just damage.
  // The original Python code had max(1, total) for damage. For general dice rolls, 0 or negative might be valid.
  // However, for damage dice specifically, it's often minimum 1.
  // The python code applies max(1, total) which suggests it's primarily for damage.
  // Let's keep it that way for now. If a roll can be less than 1, this should be revisited.
  return Math.max(1, total);
}

/**
 * Generates a simple unique ID.
 * Not cryptographically secure, but good enough for runtime object identification.
 */
export function generateUniqueID(): string {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

/**
 * Parses a critical threat range string (e.g., "20", "19-20") into a list of numbers.
 * @param rangeStr The critical threat range string.
 * @returns An array of numbers representing the threat range. Defaults to [20] if invalid.
 */
export function parseCriticalThreatRange(rangeStr: string): number[] {
    if (!rangeStr) return [20];
    if (rangeStr.includes('-')) {
        const parts = rangeStr.split('-');
        const start = parseInt(parts[0], 10);
        const end = parseInt(parts[1], 10);
        if (!isNaN(start) && !isNaN(end) && start <= end && start >=1 && end <= 20) {
            const range: number[] = [];
            for (let i = start; i <= end; i++) {
                range.push(i);
            }
            return range;
        }
    } else {
        const val = parseInt(rangeStr, 10);
        if (!isNaN(val) && val >=1 && val <= 20) {
            return [val];
        }
    }
    console.warn(`Invalid critical threat range string: "${rangeStr}", defaulting to [20].`);
    return [20]; // Default if parsing fails
}

/**
 * Parses a critical multiplier string (e.g., "x2", "x3") into a number.
 * @param multiplierStr The critical multiplier string.
 * @returns The multiplier as a number. Defaults to 2 if invalid.
 */
export function parseCriticalMultiplier(multiplierStr: string): number {
    if (!multiplierStr) return 2;
    const match = multiplierStr.toLowerCase().match(/x(\d+)/);
    if (match && match[1]) {
        const val = parseInt(match[1], 10);
        if (!isNaN(val) && val >= 2) {
            return val;
        }
    }
    console.warn(`Invalid critical multiplier string: "${multiplierStr}", defaulting to 2.`);
    return 2; // Default if parsing fails
}

// The Attack class already has getThreatRange and getCritMultiplier.
// These parsers can be used if needed before an Attack object is instantiated,
// or for validating input for Attack constructor.
// We can update the Attack class to use these utility functions.
// For now, these are standalone helpers.

/**
 * A simple sleep function.
 * @param ms Milliseconds to sleep.
 */
export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
