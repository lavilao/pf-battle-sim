#!/usr/bin/env python3
"""
Pathfinder 1e Battle Simulator - Command Line Interface
Interactive CLI for running combat encounters
"""

import sys # Keep sys for potential exit() calls, though not currently used directly
import os # Keep os for potential path operations if needed later, though not for sys.path

# sys.path.append(os.path.dirname(os.path.abspath(__file__))) # No longer needed if run as module

# Corrected imports to use the .core subpackage
from .core import (
    Combatant, Attack, DamageType, MonsterDatabase,
    CombatEngine, ActionHandler, ActionType
)
# Note: pmd_integration import will be handled separately if it's within this file.
# Looking at the file content, pmd_integration is imported later dynamically.

class PathfinderCLI:
    """Command line interface for the Pathfinder Battle Simulator"""

    def __init__(self):
        self.db = MonsterDatabase()
        self.combat = None
        self.action_handler = None
        self.loaded_combatants = []

        # Initialize with some sample monsters
        self.initialize_sample_monsters()

    def initialize_sample_monsters(self):
        """Create and save some sample monsters to the database"""
        # Only create if they don't already exist
        existing_monsters = [name.lower() for name in self.db.list_monsters()]

        # Orc Warrior
        if 'orc warrior' not in existing_monsters:
            orc = Combatant("Orc Warrior", is_pc=False)
            orc.max_hp = 6
            orc.ability_scores.strength = 17
            orc.ability_scores.dexterity = 11
            orc.ability_scores.constitution = 12
            orc.ability_scores.intelligence = 8
            orc.ability_scores.wisdom = 11
            orc.ability_scores.charisma = 8
            orc.base_attack_bonus = 1
            orc.armor_class.armor_bonus = 4
            orc.armor_class.shield_bonus = 1
            orc.saving_throws.fortitude_base = 3
            orc.saving_throws.reflex_base = 0
            orc.saving_throws.will_base = -1
            orc.size = "Medium"
            orc.creature_type = "Humanoid"
            orc.subtypes = ["Orc"]
            orc.alignment = "Chaotic Evil"

            falchion = Attack(
                name="Falchion",
                damage_dice="2d4",
                critical_threat_range="18-20",
                critical_multiplier="x2",
                damage_type=DamageType.SLASHING
            )
            orc.attacks.append(falchion)
            orc.initiative_modifier = orc.ability_scores.get_modifier("dexterity")
            self.db.save_monster(orc)

        # Goblin
        if 'goblin' not in existing_monsters:
            goblin = Combatant("Goblin", is_pc=False)
            goblin.max_hp = 5
            goblin.ability_scores.strength = 11
            goblin.ability_scores.dexterity = 15
            goblin.ability_scores.constitution = 12
            goblin.ability_scores.intelligence = 10
            goblin.ability_scores.wisdom = 9
            goblin.ability_scores.charisma = 6
            goblin.base_attack_bonus = 1
            goblin.armor_class.armor_bonus = 2  # Leather armor
            goblin.armor_class.shield_bonus = 1  # Light shield
            goblin.armor_class.size_modifier = 1  # Small size
            goblin.saving_throws.fortitude_base = 1
            goblin.saving_throws.reflex_base = 2
            goblin.saving_throws.will_base = -1
            goblin.size = "Small"
            goblin.creature_type = "Humanoid"
            goblin.subtypes = ["Goblinoid"]
            goblin.alignment = "Neutral Evil"

            short_sword = Attack(
                name="Short Sword",
                damage_dice="1d4",
                critical_threat_range="19-20",
                critical_multiplier="x2",
                damage_type=DamageType.PIERCING
            )
            goblin.attacks.append(short_sword)
            goblin.initiative_modifier = goblin.ability_scores.get_modifier("dexterity")
            self.db.save_monster(goblin)

        # Skeleton
        if 'skeleton' not in existing_monsters:
            skeleton = Combatant("Skeleton", is_pc=False)
            skeleton.max_hp = 4
            skeleton.ability_scores.strength = 15
            skeleton.ability_scores.dexterity = 14
            skeleton.ability_scores.constitution = 10  # Undead don't use Con, but keeping for simplicity
            skeleton.ability_scores.intelligence = 10
            skeleton.ability_scores.wisdom = 10
            skeleton.ability_scores.charisma = 10
            skeleton.base_attack_bonus = 1
            skeleton.armor_class.natural_armor_bonus = 2
            skeleton.saving_throws.fortitude_base = 0
            skeleton.saving_throws.reflex_base = 2
            skeleton.saving_throws.will_base = 2
            skeleton.size = "Medium"
            skeleton.creature_type = "Undead"
            skeleton.alignment = "Neutral Evil"
            skeleton.damage_reduction = {"amount": 5, "type": "bludgeoning"}

            claw = Attack(
                name="Claw",
                damage_dice="1d4",
                critical_threat_range="20",
                critical_multiplier="x2",
                damage_type=DamageType.SLASHING
            )
            skeleton.attacks.append(claw)
            skeleton.initiative_modifier = skeleton.ability_scores.get_modifier("dexterity")
            self.db.save_monster(skeleton)

    def show_menu(self):
        """Display the main menu"""
        print("\n" + "="*50)
        print("   PATHFINDER 1E BATTLE SIMULATOR")
        print("="*50)
        print("1. List Available Monsters")
        print("2. Create Player Character")
        print("3. Start Combat Encounter")
        print("4. Show Monster Details")
        print("5. Manage Monster Database")
        print("6. Exit")
        print("="*50)

    def list_monsters(self):
        """List all monsters in the database"""
        monsters = self.db.list_monsters()
        if not monsters:
            print("No monsters in database.")
            return

        print("\nAvailable Monsters:")
        print("-" * 30)
        for i, monster in enumerate(monsters, 1):
            print(f"{i}. {monster}")

    def show_monster_details(self):
        """Show detailed stats for a monster"""
        monsters = self.db.list_monsters()
        if not monsters:
            print("No monsters in database.")
            return

        self.list_monsters()
        try:
            choice = int(input("\nEnter monster number: ")) - 1
            if 0 <= choice < len(monsters):
                monster = self.db.load_monster(monsters[choice])
                if monster:
                    self.print_combatant_details(monster)
            else:
                print("Invalid choice.")
        except (ValueError, IndexError):
            print("Invalid input.")

    def print_combatant_details(self, combatant: Combatant):
        """Print detailed information about a combatant"""
        print(f"\n{combatant.name}")
        print("="*40)
        print(f"HP: {combatant.current_hp}/{combatant.max_hp}")
        print(f"AC: {combatant.get_ac()} (Touch: {combatant.get_ac('touch')}, Flat-footed: {combatant.get_ac('flat_footed')})")
        print(f"BAB: +{combatant.base_attack_bonus}")
        print(f"CMB: +{combatant.calculate_cmb()}, CMD: {combatant.calculate_cmd()}")

        print(f"\nAbility Scores:")
        abilities = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
        for ability in abilities:
            score = combatant.ability_scores.get_total_score(ability)
            modifier = combatant.ability_scores.get_modifier(ability)
            mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)
            print(f"  {ability.capitalize()}: {score} ({mod_str})")

        print(f"\nSaving Throws:")
        for save in ['fortitude', 'reflex', 'will']:
            bonus = combatant.saving_throws.calculate_save(save, combatant.ability_scores)
            bonus_str = f"+{bonus}" if bonus >= 0 else str(bonus)
            print(f"  {save.capitalize()}: {bonus_str}")

        if combatant.attacks:
            print(f"\nAttacks:")
            for attack in combatant.attacks:
                attack_bonus = combatant.get_attack_bonus(attack)
                bonus_str = f"+{attack_bonus}" if attack_bonus >= 0 else str(attack_bonus)
                print(f"  {attack.name}: {bonus_str} ({attack.damage_dice}, {attack.critical_threat_range}/{attack.critical_multiplier})")

        if combatant.damage_reduction:
            print(f"\nDamage Reduction: {combatant.damage_reduction['amount']}/{combatant.damage_reduction.get('type', 'any')}")

        print(f"\nSize: {combatant.size}")
        print(f"Type: {combatant.creature_type}")
        if combatant.subtypes:
            print(f"Subtypes: {', '.join(combatant.subtypes)}")
        print(f"Alignment: {combatant.alignment}")
        print(f"Initiative: +{combatant.initiative_modifier}")

    def create_player_character(self):
        """Simple PC creation"""
        print("\n=== Create Player Character ===")

        name = input("Character name: ").strip()
        if not name:
            print("Invalid name.")
            return None

        pc = Combatant(name, is_pc=True)

        print("\nEnter ability scores (or press Enter for default 10):")
        abilities = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
        for ability in abilities:
            while True:
                try:
                    score_input = input(f"{ability.capitalize()} (10): ").strip()
                    score = int(score_input) if score_input else 10
                    if 3 <= score <= 25:
                        setattr(pc.ability_scores, ability, score)
                        break
                    else:
                        print("Score must be between 3 and 25.")
                except ValueError:
                    print("Please enter a valid number.")

        # Basic combat stats
        while True:
            try:
                hp = int(input("Hit Points (10): ") or "10")
                if hp > 0:
                    pc.max_hp = hp
                    pc.current_hp = hp
                    break
                else:
                    print("HP must be positive.")
            except ValueError:
                print("Please enter a valid number.")

        while True:
            try:
                bab = int(input("Base Attack Bonus (1): ") or "1")
                if bab >= 0:
                    pc.base_attack_bonus = bab
                    break
                else:
                    print("BAB must be non-negative.")
            except ValueError:
                print("Please enter a valid number.")

        while True:
            try:
                ac_bonus = int(input("Armor Bonus (0): ") or "0")
                if ac_bonus >= 0:
                    pc.armor_class.armor_bonus = ac_bonus
                    break
                else:
                    print("Armor bonus must be non-negative.")
            except ValueError:
                print("Please enter a valid number.")

        # Simple weapon
        weapon_name = input("Primary weapon name (Longsword): ").strip() or "Longsword"
        damage_dice = input("Weapon damage dice (1d8): ").strip() or "1d8"

        weapon = Attack(
            name=weapon_name,
            damage_dice=damage_dice,
            critical_threat_range="20",
            critical_multiplier="x2",
            damage_type=DamageType.SLASHING
        )
        pc.attacks.append(weapon)

        pc.initiative_modifier = pc.ability_scores.get_modifier("dexterity")

        print(f"\nCreated {pc.name}!")
        self.print_combatant_details(pc)

        return pc

    def setup_encounter(self):
        """Set up a combat encounter"""
        print("\n=== Setup Combat Encounter ===")

        self.combat = CombatEngine()
        self.action_handler = ActionHandler(self.combat)

        while True:
            print("\n1. Add Monster")
            print("2. Add Player Character")
            print("3. Start Combat")
            print("4. Cancel")

            choice = input("Choice: ").strip()

            if choice == "1":
                self.add_monster_to_encounter()
            elif choice == "2":
                self.add_pc_to_encounter()
            elif choice == "3":
                if len(self.combat.combatants) >= 2:
                    self.run_combat()
                    break
                else:
                    print("Need at least 2 combatants for combat.")
            elif choice == "4":
                break
            else:
                print("Invalid choice.")

    def add_monster_to_encounter(self):
        """Add a monster to the current encounter"""
        monsters = self.db.list_monsters()
        if not monsters:
            print("No monsters available.")
            return

        self.list_monsters()
        try:
            choice = int(input("Enter monster number: ")) - 1
            if 0 <= choice < len(monsters):
                monster = self.db.load_monster(monsters[choice])
                if monster:
                    # Ask about awareness for surprise rounds
                    aware = input(f"Is {monster.name} aware at start of combat? (y/N): ").strip().lower()
                    is_aware = aware in ['y', 'yes']

                    self.combat.add_combatant(monster, is_aware=is_aware)
                    print(f"Added {monster.name} to encounter (aware: {is_aware})")
            else:
                print("Invalid choice.")
        except (ValueError, IndexError):
            print("Invalid input.")

    def add_pc_to_encounter(self):
        """Add a PC to the encounter"""
        pc = self.create_player_character()
        if pc:
            aware = input(f"Is {pc.name} aware at start of combat? (Y/n): ").strip().lower()
            is_aware = aware not in ['n', 'no']

            self.combat.add_combatant(pc, is_aware=is_aware)
            print(f"Added {pc.name} to encounter (aware: {is_aware})")

    def run_combat(self):
        """Run the combat encounter"""
        print("\n" + "="*60)
        print("                    COMBAT!")
        print("="*60)

        self.combat.start_combat()

        while self.combat.combat_active:
            current_combatant = self.combat.get_current_combatant()
            if not current_combatant or current_combatant.current_hp <= 0:
                # Remove unconscious/dead combatants from initiative order
                self.combat.advance_turn()
                continue

            if current_combatant.is_pc:
                self.handle_player_turn(current_combatant)
            else:
                self.handle_npc_turn(current_combatant)

            # Check if combat should end
            alive_combatants = [c for c in self.combat.combatants if c.current_hp > 0]
            has_pcs = any(c.is_pc for c in alive_combatants)
            has_monsters = any(not c.is_pc for c in alive_combatants)

            # Combat ends when either:
            # 1. PCs are all that remain, or
            # 2. Only 0-1 combatants remain (for monster vs monster)
            if (has_pcs and not has_monsters) or (len(alive_combatants) <= 1):
                self.combat.end_combat()
                print("\n=== COMBAT ENDS ===")
                self.print_final_combat_status()
                break

            self.combat.advance_turn()

            # Pause between turns for readability
            input("\nPress Enter to continue...")

    def handle_player_turn(self, combatant: Combatant):
        """Handle a player character's turn"""
        print(f"\n{combatant.name}'s turn:")
        self.print_combat_status(combatant)

        while True:
            print("\nActions:")
            print("1. Attack")
            print("2. Full Attack")
            print("3. Move")
            print("4. Pass Turn")

            choice = input("Choose action: ").strip()

            if choice == "1":
                if self.choose_target_and_attack(combatant, is_full_attack=False):
                    break
            elif choice == "2":
                if self.choose_target_and_attack(combatant, is_full_attack=True):
                    break
            elif choice == "3":
                distance = input("Move distance (feet): ").strip()
                try:
                    distance = int(distance)
                    self.action_handler.take_move_action(combatant, distance)
                    break
                except ValueError:
                    print("Invalid distance.")
            elif choice == "4":
                self.combat.log.add_entry(f"{combatant.name} passes their turn")
                break
            else:
                print("Invalid choice.")

    def handle_npc_turn(self, combatant: Combatant):
        """Handle an NPC's turn with simple AI"""
        targets = self.combat.get_valid_targets(combatant)
        if targets and combatant.attacks:
            target = targets[0]  # Simple AI: attack first available target
            self.action_handler.take_attack_action(combatant, target, 0)
        else:
            self.combat.log.add_entry(f"{combatant.name} has no valid actions")

    def choose_target_and_attack(self, attacker: Combatant, is_full_attack: bool = False) -> bool:
        """Choose a target and make an attack"""
        targets = self.combat.get_valid_targets(attacker)
        if not targets:
            print("No valid targets.")
            return False

        if not attacker.attacks:
            print("No attacks available.")
            return False

        print("\nAvailable targets:")
        for i, target in enumerate(targets, 1):
            print(f"{i}. {target.name} (HP: {target.current_hp}/{target.max_hp})")

        try:
            target_choice = int(input("Choose target: ")) - 1
            if 0 <= target_choice < len(targets):
                target = targets[target_choice]

                if len(attacker.attacks) > 1:
                    print("\nAvailable attacks:")
                    for i, attack in enumerate(attacker.attacks, 1):
                        print(f"{i}. {attack.name}")

                    attack_choice = int(input("Choose attack: ")) - 1
                    if 0 <= attack_choice < len(attacker.attacks):
                        if is_full_attack:
                            self.action_handler.take_full_attack_action(attacker, target, attack_choice)
                        else:
                            self.action_handler.take_attack_action(attacker, target, attack_choice)
                        return True
                else:
                    if is_full_attack:
                        self.action_handler.take_full_attack_action(attacker, target, 0)
                    else:
                        self.action_handler.take_attack_action(attacker, target, 0)
                    return True

            print("Invalid choice.")
            return False
        except (ValueError, IndexError):
            print("Invalid input.")
            return False

    def print_final_combat_status(self):
        """Print final status of all combatants"""
        print("\nFinal Status:")
        for combatant in self.combat.combatants:
            status = "DEAD" if combatant.current_hp <= 0 else f"{combatant.current_hp}/{combatant.max_hp} HP"
            print(f"{combatant.name}: {status}")

    def print_combat_status(self, combatant: Combatant):
        """Print current combat status for a combatant"""
        print(f"HP: {combatant.current_hp}/{combatant.max_hp}")
        print(f"AC: {combatant.get_ac()}")
        if combatant.conditions:
            print(f"Conditions: {', '.join(combatant.conditions)}")

    def manage_database(self):
        """Monster database management menu"""
        while True:
            print("\n=== Monster Database Management ===")
            print("1. List Monsters")
            print("2. Delete Monster")
            print("3. Browse Online Monsters")
            print("4. Download Monster by Name")
            print("5. Back to Main Menu")

            choice = input("Choice: ").strip()

            if choice == "1":
                self.list_monsters()
            elif choice == "2":
                self.delete_monster()
            elif choice == "3":
                self.browse_online_monsters()
            elif choice == "4":
                self.download_monster_via_pmd()
            elif choice == "5":
                break
            else:
                print("Invalid choice.")

    def browse_online_monsters(self):
        """Browse and download monsters from online sources"""
        from .pmd_integration import MonsterListDownloader

        print("\n=== Online Monster Browser ===")
        print("Downloading monster list...")

        downloader = MonsterListDownloader()
        monsters = downloader.get_available_monsters()

        if not monsters:
            print("Failed to download monster list")
            return

        page_size = 10
        current_page = 0
        total_pages = (len(monsters) + page_size - 1) // page_size

        while True:
            print(f"\nPage {current_page + 1}/{total_pages}")
            start_idx = current_page * page_size
            end_idx = start_idx + page_size

            for i, (name, url) in enumerate(monsters[start_idx:end_idx], start_idx + 1):
                print(f"{i}. {name}")

            print("\nn. Next page | p. Previous page | s. Select monster | q. Quit")
            choice = input("Choice: ").strip().lower()

            if choice == 'n':
                if current_page < total_pages - 1:
                    current_page += 1
                else:
                    print("Already on the last page!")
            elif choice == 'p':
                if current_page > 0:
                    current_page -= 1
                else:
                    print("Already on the first page!")
            elif choice == 's':
                try:
                    num = int(input("Enter monster number: ").strip()) - 1
                    if 0 <= num < len(monsters):
                        name = monsters[num][0]
                        self._download_and_save_monster(name)
                    else:
                        print("Invalid number")
                except ValueError:
                    print("Invalid input")
            elif choice == 'q':
                break
            else:
                print("Invalid choice")

    def _download_and_save_monster(self, monster_name: str):
        """Helper to handle monster download and saving"""
        from .pmd_integration import create_pmd_integrator
        integrator = create_pmd_integrator()

        try:
            print(f"\nDownloading {monster_name}...")
            combatant = integrator.get_or_download_monster(monster_name)
            if combatant:
                self.db.save_monster(combatant)
                print(f"Successfully saved {monster_name}!")
                self.print_combatant_details(combatant)
            else:
                print(f"Failed to download {monster_name}")
        except Exception as e:
            print(f"Error downloading monster: {str(e)}")

    def download_monster_via_pmd(self):
        """Download a monster from PMD"""
        monster_name = input("\nEnter monster name to download: ").strip()
        if not monster_name:
            print("Invalid name.")
            return

        from .pmd_integration import create_pmd_integrator # Changed to relative import
        integrator = create_pmd_integrator()

        try:
            combatant = integrator.get_or_download_monster(monster_name)
            if combatant:
                # Save to database
                self.db.save_monster(combatant)
                print(f"\nSuccessfully downloaded and saved {monster_name}!")
            else:
                print(f"\nFailed to download {monster_name}")
        except Exception as e:
            print(f"\nError downloading monster: {str(e)}")

    def delete_monster(self):
        """Delete a monster from the database"""
        monsters = self.db.list_monsters()
        if not monsters:
            print("No monsters in database.")
            return

        self.list_monsters()
        try:
            choice = int(input("Enter monster number to delete: ")) - 1
            if 0 <= choice < len(monsters):
                monster_name = monsters[choice]
                confirm = input(f"Delete {monster_name}? (y/N): ").strip().lower()
                if confirm in ['y', 'yes']:
                    if self.db.delete_monster(monster_name):
                        print(f"Deleted {monster_name}")
                    else:
                        print(f"Failed to delete {monster_name}")
            else:
                print("Invalid choice.")
        except (ValueError, IndexError):
            print("Invalid input.")

    def run(self):
        """Main CLI loop"""
        print("Welcome to the Pathfinder 1e Battle Simulator!")

        while True:
            self.show_menu()
            choice = input("\nEnter your choice: ").strip()

            if choice == "1":
                self.list_monsters()
            elif choice == "2":
                pc = self.create_player_character()
                if pc:
                    input("\nPress Enter to continue...")
            elif choice == "3":
                self.setup_encounter()
            elif choice == "4":
                self.show_monster_details()
            elif choice == "5":
                self.manage_database()
            elif choice == "6":
                print("Thanks for using the Pathfinder Battle Simulator!")
                break
            else:
                print("Invalid choice. Please try again.")


if __name__ == "__main__":
    cli = PathfinderCLI()
    cli.run()
