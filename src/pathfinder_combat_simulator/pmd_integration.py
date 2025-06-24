#!/usr/bin/env python3
"""
PMD (Pathfinder Monster Database) Integration Module

This module integrates the PMD project's download and parsing logic with the simulator.
It handles downloading monster pages from aonprd.com, parsing them using PMD's parser,
and converting the data to the simulator's format.

Following SOLID principles:
- Single Responsibility: Each class has one clear purpose
- Open/Closed: Extensible for new monster sources
- Liskov Substitution: PMDIntegrator can be substituted with other integrators
- Interface Segregation: Clear, focused interfaces
- Dependency Inversion: Depends on abstractions, not concretions
"""

import os
import sys
import json
import re
import requests
import time
from typing import Dict, List, Optional, Any
from urllib.parse import quote

# Import PMD modules
# Corrected imports: these are now in .core
from .core import Combatant, MonsterDatabase, DamageType
# PMD is now a submodule, direct/relative imports should work if src is in PYTHONPATH
# from .pmd.main import parsePage # This will be used later in the code


class MonsterDownloader:
    """
    Handles downloading monster pages from the web.
    Single responsibility: Download operations only.
    """
    
    def __init__(self, rate_limit_delay: float = 0.1):
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
    
    def generate_monster_url(self, monster_name: str) -> str:
        """Generate the URL for a monster on aonprd.com"""
        # URL encode the monster name
        encoded_name = quote(monster_name, safe='/')
        return f"https://aonprd.com/MonsterDisplay.aspx?ItemName={encoded_name}"
    
    def download_page(self, url: str) -> Optional[str]:
        """Download a page from the web with rate limiting"""
        # Respect rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            self.last_request_time = time.time()
            return response.text
        except requests.RequestException as e:
            print(f"Error downloading {url}: {e}")
            return None


class PMDDataConverter:
    """
    Converts PMD format data to simulator format.
    Single responsibility: Data format conversion.
    """
    
    def __init__(self):
        # Mapping from PMD damage types to simulator damage types
        self.damage_type_mapping = {
            'slashing': DamageType.SLASHING,
            'piercing': DamageType.PIERCING,
            'bludgeoning': DamageType.BLUDGEONING,
            'fire': DamageType.FIRE,
            'cold': DamageType.COLD,
            'acid': DamageType.ACID,
            'electricity': DamageType.ELECTRICITY,
            'sonic': DamageType.SONIC,
            'force': DamageType.FORCE
        }
    
    def convert_to_simulator_format(self, pmd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert PMD format data to simulator format"""
        simulator_data = {
            "name": pmd_data.get("title2", "Unknown Monster"),
            "is_pc": False,
            "max_hp": self._extract_hp(pmd_data),
            "ability_scores": self._extract_ability_scores(pmd_data),
            "base_attack_bonus": pmd_data.get("BAB", 0),
            "armor_class": self._extract_armor_class(pmd_data),
            "saving_throws": self._extract_saving_throws(pmd_data),
            "base_speed": self._extract_speed(pmd_data),
            "size": self._extract_size(pmd_data),
            "creature_type": self._extract_creature_type(pmd_data),
            "subtypes": self._extract_subtypes(pmd_data),
            "alignment": self._extract_alignment(pmd_data),
            "skills": self._extract_skills(pmd_data),
            "feats": self._extract_feats(pmd_data),
            "attacks": self._extract_attacks(pmd_data),
            "damage_reduction": self._extract_damage_reduction(pmd_data),
            "spell_resistance": pmd_data.get("SR", 0),
            "energy_resistances": self._extract_resistances(pmd_data),
            "energy_immunities": self._extract_immunities(pmd_data),
            "energy_vulnerabilities": self._extract_vulnerabilities(pmd_data)
        }
        
        return simulator_data
    
    def _extract_hp(self, pmd_data: Dict[str, Any]) -> int:
        """Extract HP from PMD data"""
        hp_data = pmd_data.get("HP", {})
        return hp_data.get("total", 1)
    
    def _extract_ability_scores(self, pmd_data: Dict[str, Any]) -> Dict[str, int]:
        """Extract ability scores from PMD data"""
        pmd_abilities = pmd_data.get("ability_scores", {})
        
        # Convert PMD ability score format to simulator format
        # PMD uses uppercase short names, simulator uses lowercase full names
        # Handle None values (for things like undead with no Con)
        return {
            "strength": pmd_abilities.get("STR") or 10,
            "dexterity": pmd_abilities.get("DEX") or 10,
            "constitution": pmd_abilities.get("CON") or 10,
            "intelligence": pmd_abilities.get("INT") or 10,
            "wisdom": pmd_abilities.get("WIS") or 10,
            "charisma": pmd_abilities.get("CHA") or 10
        }
    
    def _extract_armor_class(self, pmd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract armor class components from PMD data"""
        ac_data = pmd_data.get("AC", {})
        components = ac_data.get("components", {})
        
        return {
            "armor_bonus": components.get("armor", 0),
            "shield_bonus": components.get("shield", 0),
            "natural_armor_bonus": components.get("natural", 0),
            "deflection_bonus": components.get("deflection", 0),
            "dodge_bonus": components.get("dodge", 0),
            "size_modifier": components.get("size", 0),
            "max_dex_bonus_from_armor": None  # TODO: Extract from PMD if available
        }
    
    def _extract_saving_throws(self, pmd_data: Dict[str, Any]) -> Dict[str, int]:
        """Extract saving throws from PMD data"""
        saves = pmd_data.get("saves", {})
        return {
            "fortitude_base": saves.get("fort", 0),
            "reflex_base": saves.get("ref", 0),
            "will_base": saves.get("will", 0)
        }
    
    def _extract_speed(self, pmd_data: Dict[str, Any]) -> int:
        """Extract base speed from PMD data"""
        speeds = pmd_data.get("speeds", {})
        return speeds.get("base", 30)
    
    def _extract_size(self, pmd_data: Dict[str, Any]) -> str:
        """Extract size from PMD data"""
        size = pmd_data.get("size", "Medium")
        # Capitalize first letter
        return size.capitalize()
    
    def _extract_creature_type(self, pmd_data: Dict[str, Any]) -> str:
        """Extract creature type from PMD data"""
        creature_type = pmd_data.get("type", "humanoid")
        # Capitalize first letter  
        return creature_type.capitalize()
    
    def _extract_subtypes(self, pmd_data: Dict[str, Any]) -> List[str]:
        """Extract subtypes from PMD data"""
        subtypes = pmd_data.get("subtypes", [])
        if isinstance(subtypes, list):
            return subtypes
        return []
    
    def _extract_alignment(self, pmd_data: Dict[str, Any]) -> str:
        """Extract alignment from PMD data"""
        alignment_data = pmd_data.get("alignment", {})
        if isinstance(alignment_data, dict):
            return alignment_data.get("cleaned", "True Neutral")
        elif isinstance(alignment_data, str):
            return alignment_data
        return "True Neutral"
    
    def _extract_skills(self, pmd_data: Dict[str, Any]) -> Dict[str, int]:
        """Extract skills from PMD data"""
        skills = pmd_data.get("skills", {})
        # Convert PMD skill format to simulator format
        simulator_skills = {}
        
        for skill_name, skill_data in skills.items():
            if isinstance(skill_data, dict) and "_" in skill_data:
                # Extract the base skill value
                simulator_skills[skill_name] = skill_data["_"]
            elif isinstance(skill_data, int):
                simulator_skills[skill_name] = skill_data
        
        return simulator_skills
    
    def _extract_feats(self, pmd_data: Dict[str, Any]) -> List[str]:
        """Extract feats from PMD data"""
        feats = pmd_data.get("feats", [])
        feat_names = []
        
        for feat in feats:
            if isinstance(feat, dict):
                feat_names.append(feat.get("name", "Unknown Feat"))
            elif isinstance(feat, str):
                feat_names.append(feat)
        
        return feat_names
    
    def _extract_attacks(self, pmd_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attacks from PMD data"""
        attacks_data = pmd_data.get("attacks", {})
        simulator_attacks = []
        
        # Process melee attacks
        melee_attacks = attacks_data.get("melee", [])
        for attack_group in melee_attacks:
            for attack in attack_group:
                simulator_attack = self._convert_single_attack(attack, "melee")
                if simulator_attack:
                    simulator_attacks.append(simulator_attack)
        
        # Process ranged attacks
        ranged_attacks = attacks_data.get("ranged", [])
        for attack_group in ranged_attacks:
            for attack in attack_group:
                simulator_attack = self._convert_single_attack(attack, "ranged")
                if simulator_attack:
                    simulator_attacks.append(simulator_attack)
        
        return simulator_attacks
    
    def _convert_single_attack(self, attack_data: Dict[str, Any], attack_type: str) -> Optional[Dict[str, Any]]:
        """Convert a single attack from PMD format to simulator format"""
        if not isinstance(attack_data, dict):
            return None
        
        attack_name = attack_data.get("attack", "Unknown Attack")
        # Clean up attack name (remove numbers, capitalize)
        clean_name = re.sub(r'^\d+\s*', '', attack_name).strip()
        clean_name = clean_name.capitalize()
        
        # Extract damage information from the first entry
        entries = attack_data.get("entries", [])
        if not entries or not entries[0]:
            return None
        
        damage_info = entries[0][0] if entries[0] else {}
        damage_string = damage_info.get("damage", "1d4")
        damage_type = damage_info.get("type", "bludgeoning")
        
        # Parse damage dice and bonus
        damage_dice, bonus = self._parse_damage_string(damage_string)
        
        # Map damage type
        simulator_damage_type = self.damage_type_mapping.get(
            damage_type.lower(), DamageType.BLUDGEONING
        )
        
        return {
            "name": clean_name,
            "damage_dice": damage_dice,
            "critical_threat_range": "20",  # Default, TODO: extract from PMD
            "critical_multiplier": "x2",    # Default, TODO: extract from PMD
            "damage_type": simulator_damage_type.value,
            "reach": 5,  # Default, TODO: extract from PMD
            "associated_ability_for_attack": "str",  # Default for melee
            "associated_ability_for_damage": "str",
            "is_primary_natural_attack": True,
            "special_qualities": [],
            "enhancement_bonus": 0
        }
    
    def _parse_damage_string(self, damage_string: str) -> tuple[str, int]:
        """Parse damage string like '1d4+2' into dice and bonus"""
        # Remove any extra spaces
        damage_string = damage_string.strip()
        
        # Extract the dice part (XdY)
        dice_match = re.search(r'(\d+d\d+)', damage_string)
        if dice_match:
            dice_part = dice_match.group(1)
        else:
            dice_part = "1d4"  # Default
        
        # Extract bonus (+ or - number)
        bonus_match = re.search(r'([+-]\d+)', damage_string)
        bonus = int(bonus_match.group(1)) if bonus_match else 0
        
        return dice_part, bonus
    
    def _extract_damage_reduction(self, pmd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract damage reduction from PMD data"""
        dr_list = pmd_data.get("DR", [])
        if dr_list and len(dr_list) > 0:
            # Take the first DR entry
            dr_entry = dr_list[0]
            return {
                "amount": dr_entry.get("amount", 0),
                "type": dr_entry.get("weakness", "")
            }
        return {}
    
    def _extract_resistances(self, pmd_data: Dict[str, Any]) -> Dict[str, int]:
        """Extract energy resistances from PMD data"""
        resistances = pmd_data.get("resistances", {})
        energy_resistances = {}
        
        for resistance_type, value in resistances.items():
            if isinstance(value, int) and resistance_type in self.damage_type_mapping:
                energy_resistances[resistance_type] = value
        
        return energy_resistances
    
    def _extract_immunities(self, pmd_data: Dict[str, Any]) -> List[str]:
        """Extract energy immunities from PMD data"""
        immunities = pmd_data.get("immunities", [])
        if isinstance(immunities, list):
            return immunities
        return []
    
    def _extract_vulnerabilities(self, pmd_data: Dict[str, Any]) -> List[str]:
        """Extract energy vulnerabilities from PMD data"""
        # PMD doesn't typically have a separate vulnerabilities field
        # This would need to be extracted from special abilities or other sources
        return []


class PMDIntegrator:
    """
    Main integration class that orchestrates the download and conversion process.
    Open/Closed principle: Can be extended for new monster sources.
    """
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.monster_db = MonsterDatabase(database_path)
        self.downloader = MonsterDownloader()
        self.converter = PMDDataConverter()
        
        # Ensure PMD dependencies are available
        self._setup_pmd_environment()
    
    def _setup_pmd_environment(self):
        """Setup PMD environment and dependencies"""
        # Create necessary directories
        os.makedirs(os.path.join(self.database_path, "pmd_cache"), exist_ok=True)
        
        # Load class HD data if available
        try:
            # Construct path to class_hds.json, now that pmd is a subdirectory
            # __file__ is pmd_integration.py
            # pmd/data/class_hds.json is relative to this file's directory's sibling 'pmd'
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            class_hds_path = os.path.join(current_script_dir, "pmd", "data", "class_hds.json")
            if os.path.exists(class_hds_path):
                with open(class_hds_path, 'r') as f:
                    self.class_hds = json.load(f)
            else:
                # Fallback class HD data
                self.class_hds = {
                    "barbarian": 12, "fighter": 10, "paladin": 10, "ranger": 10,
                    "bard": 8, "cleric": 8, "druid": 8, "monk": 8, "rogue": 8,
                    "sorcerer": 6, "wizard": 6
                }
        except Exception as e:
            print(f"Warning: Could not load class HD data: {e}")
            self.class_hds = {}
    
    def generate_monster_url(self, monster_name: str) -> str:
        """Generate URL for monster (delegates to downloader)"""
        return self.downloader.generate_monster_url(monster_name)
    
    def download_monster_page(self, monster_name: str) -> Optional[str]:
        """Download monster page from the web"""
        url = self.generate_monster_url(monster_name)
        return self.downloader.download_page(url)
    
    def parse_monster_html(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse monster HTML using PMD's parser"""
        try:
            # Set up global variables that PMD parser expects
            # Parse the HTML using PMD's parser
            # pmd_integration.py is in pathfinder_combat_simulator/
            # pmd module is in pathfinder_combat_simulator/pmd/
            from .pmd.main import parsePage
            pmd_data = parsePage(html, url)
            return pmd_data
        except Exception as e:
            print(f"Error parsing monster HTML: {e}")
            return None
    
    def convert_pmd_to_simulator(self, pmd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert PMD data to simulator format (delegates to converter)"""
        return self.converter.convert_to_simulator_format(pmd_data)
    
    def get_or_download_monster(self, monster_name: str) -> Optional[Combatant]:
        """
        Get monster from local database or download and parse if not available.
        This is the main entry point for the integration.
        """
        # First, try to load from local database
        local_monster = self.monster_db.load_monster(monster_name)
        if local_monster:
            print(f"Loaded {monster_name} from local database")
            return local_monster
        
        print(f"Monster '{monster_name}' not found locally. Downloading...")
        
        # Download the monster page
        html = self.download_monster_page(monster_name)
        if not html:
            print(f"Failed to download {monster_name}")
            return None
        
        # Parse using PMD
        url = self.generate_monster_url(monster_name)
        pmd_data = self.parse_monster_html(html, url)
        if not pmd_data:
            print(f"Failed to parse {monster_name}")
            return None
        
        # Convert to simulator format
        simulator_data = self.convert_pmd_to_simulator(pmd_data)
        
        # Create combatant and save to database
        combatant = Combatant.from_dict(simulator_data)
        
        # Save for future use
        if self.monster_db.save_monster(combatant):
            print(f"Saved {monster_name} to local database")
        else:
            print(f"Warning: Failed to save {monster_name} to database")
        
        return combatant


def create_pmd_integrator(database_path: str = "monster_data") -> PMDIntegrator:
    """Factory function to create PMD integrator"""
    return PMDIntegrator(database_path)


if __name__ == "__main__":
    # Demo of PMD integration
    print("=== PMD Integration Demo ===")
    
    integrator = create_pmd_integrator()
    
    # Test downloading a monster
    test_monster_name = "Skeleton"
    print(f"Testing with {test_monster_name}...")
    
    monster = integrator.get_or_download_monster(test_monster_name)
    
    if monster:
        print(f"Successfully processed {monster.name}:")
        print(f"  HP: {monster.current_hp}/{monster.max_hp}")
        print(f"  AC: {monster.get_ac()}")
        print(f"  Attacks: {len(monster.attacks)}")
        if monster.attacks:
            attack = monster.attacks[0]
            print(f"    - {attack.name}: {attack.damage_dice} {attack.damage_type.value}")
    else:
        print(f"Failed to process {test_monster_name}")
