#!/usr/bin/env python3
"""
Tests for PMD (Pathfinder Monster Database) integration with the simulator.
Tests the download, parsing, and conversion pipeline.
"""

import unittest
import json
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Import the modules we'll be testing
# Assuming tests are run from the root directory where `src` is visible,
# or pytest handles path resolution for the src layout.
import sys # Added for path modification
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Added

from src.pathfinder_combat_simulator import Combatant, MonsterDatabase
from src.pathfinder_combat_simulator.pmd_integration import PMDIntegrator, PMDDataConverter # PMDDataConverter might be needed for some tests if they were using it directly from pmd_integration
from src.pathfinder_combat_simulator.enhanced_monster_database import EnhancedMonsterDatabase


class TestPMDIntegration(unittest.TestCase):
    """Test cases for PMD integration functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        # Use MonsterDatabase from the package for consistency in tests
        self.monster_db = MonsterDatabase(database_path=self.test_dir)
        
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def test_download_monster_url_list_generation(self):
        """Test that we can generate proper URLs for monster downloads"""
        # PMDIntegrator is now imported at the module level
        integrator = PMDIntegrator(self.test_dir)
        
        # Test various monster name formats
        test_cases = [
            ("Skeleton", "https://aonprd.com/MonsterDisplay.aspx?ItemName=Skeleton"),
            ("Ancient Red Dragon", "https://aonprd.com/MonsterDisplay.aspx?ItemName=Ancient%20Red%20Dragon"),
            ("Orc Warrior", "https://aonprd.com/MonsterDisplay.aspx?ItemName=Orc%20Warrior")
        ]
        
        for monster_name, expected_url in test_cases:
            with self.subTest(monster_name=monster_name):
                url = integrator.generate_monster_url(monster_name)
                self.assertEqual(url, expected_url)
    
    @patch('requests.get')
    def test_download_monster_page(self, mock_get):
        """Test downloading a monster page from the web"""
        # PMDIntegrator is now imported at the module level
        integrator = PMDIntegrator(self.test_dir)
        
        # Mock HTML response
        mock_html = """
        <html>
            <div id="main">
                <table>
                    <tr>
                        <td>
                            <span>
                                <h1 class="title">Skeleton</h1>
                                <h2 class="title">Skeleton CR 1/3</h2>
                                <!-- Monster data would be here -->
                            </span>
                        </td>
                    </tr>
                </table>
            </div>
        </html>
        """
        
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        html = integrator.download_monster_page("Skeleton")
        
        self.assertIsNotNone(html)
        self.assertIn("Skeleton", html)
        mock_get.assert_called_once()
    
    def test_parse_pmd_to_simulator_format(self):
        """Test conversion from PMD format to simulator format"""
        # PMDIntegrator is now imported at the module level
        integrator = PMDIntegrator(self.test_dir)
        
        # Sample PMD data (simplified)
        pmd_data = {
            "title2": "Skeleton",
            "CR": 0.33,
            "HP": {
                "total": 4,
                "HD": {"num": 1}
            },
            "ability_scores": {
                "STR": 15,
                "DEX": 14,
                "CON": None,  # Undead have no Con
                "INT": None,
                "WIS": 10,
                "CHA": 10
            },
            "AC": {
                "AC": 16,
                "touch": 12,
                "flat_footed": 14,
                "components": {
                    "natural": 2
                }
            },
            "saves": {
                "fort": 0,
                "ref": 2,
                "will": 2
            },
            "BAB": 0,
            "attacks": {
                "melee": [[{
                    "attack": "claw",
                    "bonus": [1],
                    "entries": [[{
                        "damage": "1d4+2",
                        "type": "slashing"
                    }]]
                }]]
            },
            "speeds": {
                "base": 30
            },
            "size": "Medium",
            "type": "undead",
            "alignment": {
                "cleaned": "Neutral Evil"
            },
            "DR": [{
                "amount": 5,
                "weakness": "bludgeoning"
            }]
        }
        
        simulator_data = integrator.convert_pmd_to_simulator(pmd_data)
        
        # Verify the conversion
        self.assertEqual(simulator_data["name"], "Skeleton")
        self.assertEqual(simulator_data["max_hp"], 4)
        self.assertEqual(simulator_data["ability_scores"]["strength"], 15)
        self.assertEqual(simulator_data["ability_scores"]["dexterity"], 14)
        self.assertEqual(simulator_data["ability_scores"]["constitution"], 10)  # Default for undead
        self.assertEqual(simulator_data["base_attack_bonus"], 0)
        self.assertEqual(simulator_data["size"], "Medium")
        self.assertEqual(simulator_data["creature_type"], "Undead")
        self.assertEqual(simulator_data["alignment"], "Neutral Evil")
        
        # Check AC components
        self.assertEqual(simulator_data["armor_class"]["natural_armor_bonus"], 2)
        
        # Check attacks
        self.assertEqual(len(simulator_data["attacks"]), 1)
        self.assertEqual(simulator_data["attacks"][0]["name"], "Claw")
        self.assertEqual(simulator_data["attacks"][0]["damage_dice"], "1d4")
        
        # Check DR
        self.assertEqual(simulator_data["damage_reduction"]["amount"], 5)
        self.assertEqual(simulator_data["damage_reduction"]["type"], "bludgeoning")
    
    @patch('pathfinder_combat_simulator.pmd_integration.PMDIntegrator.download_monster_page')
    @patch('pathfinder_combat_simulator.pmd_integration.PMDIntegrator.parse_monster_html')
    def test_full_integration_pipeline(self, mock_parse, mock_download):
        """Test the full pipeline from download to storage"""
        # PMDIntegrator is now imported at the module level
        integrator = PMDIntegrator(self.test_dir)
        
        # Mock the download and parse steps
        mock_download.return_value = "<html>Monster HTML</html>"
        mock_parse.return_value = {
            "title2": "Test Monster",
            "HP": {"total": 10},
            "ability_scores": {"STR": 14, "DEX": 12, "CON": 13, "INT": 10, "WIS": 11, "CHA": 9},
            "AC": {"AC": 15},
            "saves": {"fort": 2, "ref": 1, "will": 0},
            "BAB": 1,
            "speeds": {"base": 30},
            "size": "Medium",
            "type": "humanoid",
            "alignment": {"cleaned": "Neutral"}
        }
        
        # Test the full pipeline
        combatant = integrator.get_or_download_monster("Test Monster")
        
        self.assertIsNotNone(combatant)
        self.assertEqual(combatant.name, "Test Monster")
        self.assertEqual(combatant.max_hp, 10)
        
        # Verify the monster was saved to the database
        saved_monster = self.monster_db.load_monster("Test Monster")
        self.assertIsNotNone(saved_monster)
        self.assertEqual(saved_monster.name, "Test Monster")
    
    def test_monster_already_exists_locally(self):
        """Test that existing monsters are loaded from local cache"""
        # PMDIntegrator is now imported at the module level
        integrator = PMDIntegrator(self.test_dir)
        
        # Create a test monster and save it
        test_monster = Combatant("Existing Monster")
        test_monster.max_hp = 20
        self.monster_db.save_monster(test_monster)
        
        # Try to get the monster - should load from cache
        with patch('pathfinder_combat_simulator.pmd_integration.PMDIntegrator.download_monster_page') as mock_download:
            monster = integrator.get_or_download_monster("Existing Monster")
            
            # Should not have tried to download
            mock_download.assert_not_called()
            
            # Should have loaded the existing monster
            self.assertIsNotNone(monster)
            self.assertEqual(monster.name, "Existing Monster")
            self.assertEqual(monster.max_hp, 20)
    
    def test_ability_score_conversion_with_none_values(self):
        """Test that None ability scores are handled correctly"""
        # PMDIntegrator is now imported at the module level
        integrator = PMDIntegrator(self.test_dir)
        
        # Test undead with no Con/Int
        pmd_data = {
            "title2": "Undead Test",
            "ability_scores": {
                "STR": 16,
                "DEX": 12,
                "CON": None,
                "INT": None,
                "WIS": 10,
                "CHA": 8
            },
            "HP": {"total": 5},
            "AC": {"AC": 14},
            "saves": {"fort": 0, "ref": 1, "will": 2},
            "BAB": 1,
            "speeds": {"base": 30},
            "size": "Medium",
            "type": "undead",
            "alignment": {"cleaned": "Neutral Evil"}
        }
        
        simulator_data = integrator.convert_pmd_to_simulator(pmd_data)
        
        # None values should be converted to 10 (no modifier)
        self.assertEqual(simulator_data["ability_scores"]["constitution"], 10)
        self.assertEqual(simulator_data["ability_scores"]["intelligence"], 10)
    
    def test_attack_parsing_complex_cases(self):
        """Test parsing of complex attack patterns"""
        # PMDIntegrator is now imported at the module level
        integrator = PMDIntegrator(self.test_dir)
        
        # Test multiple attacks with different patterns
        pmd_data = {
            "title2": "Multi-Attack Monster",
            "HP": {"total": 15},
            "ability_scores": {"STR": 18, "DEX": 14, "CON": 16, "INT": 10, "WIS": 12, "CHA": 8},
            "AC": {"AC": 17},
            "saves": {"fort": 3, "ref": 2, "will": 1},
            "BAB": 3,
            "attacks": {
                "melee": [[{
                    "attack": "bite",
                    "bonus": [5],
                    "entries": [[{
                        "damage": "1d6+4",
                        "type": "piercing"
                    }]]
                }, {
                    "attack": "2 claws",
                    "bonus": [3, 3],
                    "entries": [[{
                        "damage": "1d4+2",
                        "type": "slashing"
                    }]]
                }]]
            },
            "speeds": {"base": 40},
            "size": "Large",
            "type": "magical beast",
            "alignment": {"cleaned": "Chaotic Evil"}
        }
        
        simulator_data = integrator.convert_pmd_to_simulator(pmd_data)
        
        # Should have multiple attacks
        self.assertGreaterEqual(len(simulator_data["attacks"]), 2)
        
        # Check that we have attacks
        attack_names = [a["name"] for a in simulator_data["attacks"]]
        print(f"Attack names found: {attack_names}")  # Debug output
        
        # Check first attack (bite)
        bite_attack = next((a for a in simulator_data["attacks"] if "bite" in a["name"].lower()), None)
        self.assertIsNotNone(bite_attack, f"Bite attack not found in {attack_names}")
        self.assertEqual(bite_attack["damage_dice"], "1d6")
        self.assertEqual(bite_attack["damage_type"], "piercing")
        
        # Check second attack (claws) - might be named "2 claws" or just "Claws"
        claw_attack = next((a for a in simulator_data["attacks"] if "claw" in a["name"].lower()), None)
        self.assertIsNotNone(claw_attack, f"Claw attack not found in {attack_names}")
        self.assertEqual(claw_attack["damage_dice"], "1d4")
        self.assertEqual(claw_attack["damage_type"], "slashing")


class TestEnhancedMonsterDatabase(unittest.TestCase):
    """Test enhanced monster database with PMD integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    @patch('pathfinder_combat_simulator.pmd_integration.PMDIntegrator.get_or_download_monster')
    def test_enhanced_load_monster_with_download(self, mock_get_monster):
        """Test that the enhanced database can download missing monsters"""
        # EnhancedMonsterDatabase is now imported at the module level
        
        # Set up mock to return a monster
        mock_monster = Combatant("Solar")
        mock_monster.max_hp = 25
        mock_get_monster.return_value = mock_monster
        
        db = EnhancedMonsterDatabase(self.test_dir)
        
        # Try to load a monster that doesn't exist locally
        monster = db.load_monster("Solar")
        
        self.assertIsNotNone(monster)
        self.assertEqual(monster.name, "Solar")
        self.assertEqual(monster.max_hp, 25)
        
        # Verify the download was attempted
        mock_get_monster.assert_called_once_with("Solar")
    
    def test_enhanced_load_monster_local_cache(self):
        """Test that local monsters are loaded without downloading"""
        # EnhancedMonsterDatabase is now imported at the module level
        db = EnhancedMonsterDatabase(self.test_dir)
        
        # Create and save a local monster
        local_monster = Combatant("Local Monster")
        local_monster.max_hp = 30
        db.save_monster(local_monster)
        
        # Load the monster - should not attempt download
        with patch('pathfinder_combat_simulator.pmd_integration.PMDIntegrator.get_or_download_monster') as mock_download:
            monster = db.load_monster("Local Monster")
            
            self.assertIsNotNone(monster)
            self.assertEqual(monster.name, "Local Monster")
            self.assertEqual(monster.max_hp, 30)
            
            # Should not have attempted download
            mock_download.assert_not_called()


if __name__ == '__main__':
    unittest.main()
