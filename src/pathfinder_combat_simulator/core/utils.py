import random
import re

def roll_dice(dice_string: str) -> int:
    """
    Roll dice from a string like "1d8", "2d6+1", etc.
    Helper function for damage rolling
    """
    # Handle simple dice notation like "1d8", "2d6", etc.
    if 'd' not in dice_string:
        try: # Added try-except for robustness
            return int(dice_string)
        except ValueError:
            print(f"Error: Invalid non-dice string for roll_dice: {dice_string}")
            return 0 # Or raise error

    # Split on '+' or '-' for bonuses
    # Ensure re is imported if this file is standalone
    parts = re.split(r'([+-])', dice_string)
    dice_part = parts[0]

    try:
        # Parse the dice part
        num_dice_str, die_size_str = dice_part.split('d')
        num_dice = int(num_dice_str)
        die_size = int(die_size_str)
    except ValueError:
        print(f"Error: Invalid dice format in roll_dice: {dice_part}")
        return 0 # Or raise error

    if num_dice <= 0 or die_size <= 0:
        print(f"Error: Number of dice and die size must be positive: {dice_string}")
        return 0 # Or raise error

    # Roll the dice
    total = sum(random.randint(1, die_size) for _ in range(num_dice))

    # Add any bonuses
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            operator = parts[i]
            try:
                value = int(parts[i + 1])
                if operator == '+':
                    total += value
                elif operator == '-':
                    total -= value
            except ValueError:
                print(f"Error: Invalid bonus value in roll_dice: {parts[i+1]}")
                # Decide whether to continue or return/raise error
                # For now, continue with previously calculated total

    return max(1, total)  # Minimum 1, unless error occurred and returned 0
