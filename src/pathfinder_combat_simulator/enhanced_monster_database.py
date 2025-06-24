#!/usr/bin/env python3
"""
Enhanced Monster Database with PMD Integration

This module extends the base MonsterDatabase to automatically download and parse
monsters from the PMD (Pathfinder Monster Database) when they're not available locally.

Following SOLID principles:
- Single Responsibility: Manages monster data with automatic downloading
- Open/Closed: Extends MonsterDatabase without modifying it
- Liskov Substitution: Can replace MonsterDatabase in any context
- Interface Segregation: Clear, focused interface
- Dependency Inversion: Depends on PMDIntegrator abstraction
"""

import os
from typing import Optional, List, Dict
# Corrected import: Combatant and MonsterDatabase are in .core
from .core import Combatant, MonsterDatabase
# Assuming pmd_integration is at the same level as this file or correctly in PYTHONPATH
from .pmd_integration import PMDIntegrator


class EnhancedMonsterDatabase(MonsterDatabase):
    """
    Enhanced version of MonsterDatabase that can automatically download monsters
    from the PMD when they're not available locally.
    
    Extends MonsterDatabase following the Open/Closed principle.
    """
    
    def __init__(self, database_path: str = "monster_data", enable_auto_download: bool = True):
        """
        Initialize the enhanced monster database.
        
        Args:
            database_path: Path to store monster data
            enable_auto_download: Whether to enable automatic downloading of missing monsters
        """
        super().__init__(database_path)
        self.enable_auto_download = enable_auto_download
        
        # Initialize PMD integrator if auto-download is enabled
        self.pmd_integrator = None
        if self.enable_auto_download:
            try:
                self.pmd_integrator = PMDIntegrator(database_path)
                print("PMD integration enabled - missing monsters will be downloaded automatically")
            except Exception as e:
                print(f"Warning: PMD integration failed to initialize: {e}")
                print("Auto-download disabled - only local monsters will be available")
                self.enable_auto_download = False
    
    def load_monster(self, monster_name: str) -> Optional[Combatant]:
        """
        Load a monster template from local database or download if not available.
        
        This method first tries to load from the local database. If the monster
        is not found locally and auto-download is enabled, it will attempt to
        download and parse the monster from the PMD.
        
        Args:
            monster_name: Name of the monster to load
            
        Returns:
            Combatant instance if successful, None otherwise
        """
        # First, try the base implementation (load from local database)
        local_monster = super().load_monster(monster_name)
        if local_monster:
            return local_monster
        
        # If not found locally and auto-download is enabled, try downloading
        if self.enable_auto_download and self.pmd_integrator:
            print(f"Monster '{monster_name}' not found in local database.")
            
            try:
                downloaded_monster = self.pmd_integrator.get_or_download_monster(monster_name)
                if downloaded_monster:
                    # The PMD integrator already saves to the database, so we just return it
                    return downloaded_monster
                else:
                    print(f"Failed to download '{monster_name}' from PMD")
            except Exception as e:
                print(f"Error downloading '{monster_name}': {e}")
        
        # If we get here, the monster couldn't be found or downloaded
        print(f"Monster '{monster_name}' is not available")
        return None
    
    def list_monsters(self, include_downloadable: bool = False) -> List[str]:
        """
        List available monster templates.
        
        Args:
            include_downloadable: If True, includes note about downloadable monsters
            
        Returns:
            List of monster names available locally
        """
        local_monsters = super().list_monsters()
        
        if include_downloadable and self.enable_auto_download:
            local_monsters.append("--- Additional monsters can be downloaded automatically ---")
        
        return local_monsters
    
    def is_auto_download_enabled(self) -> bool:
        """Check if automatic downloading is enabled"""
        return self.enable_auto_download and self.pmd_integrator is not None
    
    def disable_auto_download(self):
        """Disable automatic downloading of monsters"""
        self.enable_auto_download = False
        print("Auto-download disabled")
    
    def enable_auto_download_if_possible(self):
        """Enable automatic downloading if PMD integration is available"""
        if self.pmd_integrator:
            self.enable_auto_download = True
            print("Auto-download enabled")
        else:
            print("Cannot enable auto-download: PMD integration not available")
    
    def get_monster_source(self, monster_name: str) -> str:
        """
        Get the source of a monster (local or downloadable).
        
        Args:
            monster_name: Name of the monster
            
        Returns:
            "local" if monster exists locally, "downloadable" if it can be downloaded,
            "unavailable" if it cannot be obtained
        """
        # Check if it exists locally
        filename = f"{monster_name.lower().replace(' ', '_')}.json"
        filepath = os.path.join(self.database_path, filename)
        
        if os.path.exists(filepath):
            return "local"
        elif self.enable_auto_download:
            return "downloadable"
        else:
            return "unavailable"
    
    def preload_monster_list(self, monster_names: List[str]) -> Dict[str, bool]:
        """
        Preload a list of monsters, downloading any that aren't available locally.
        
        Args:
            monster_names: List of monster names to preload
            
        Returns:
            Dictionary mapping monster names to success status
        """
        results = {}
        
        for monster_name in monster_names:
            print(f"Preloading {monster_name}...")
            monster = self.load_monster(monster_name)
            results[monster_name] = monster is not None
            
            if monster:
                print(f"  ✓ {monster_name} ready")
            else:
                print(f"  ✗ {monster_name} failed")
        
        successful = sum(1 for success in results.values() if success)
        total = len(monster_names)
        print(f"\nPreloading complete: {successful}/{total} monsters ready")
        
        return results


def create_enhanced_monster_database(database_path: str = "monster_data", 
                                   enable_auto_download: bool = True) -> EnhancedMonsterDatabase:
    """
    Factory function to create an enhanced monster database.
    
    Args:
        database_path: Path to store monster data
        enable_auto_download: Whether to enable automatic downloading
        
    Returns:
        EnhancedMonsterDatabase instance
    """
    return EnhancedMonsterDatabase(database_path, enable_auto_download)


if __name__ == "__main__":
    # Demo of enhanced monster database
    print("=== Enhanced Monster Database Demo ===")
    
    # Create enhanced database
    db = create_enhanced_monster_database()
    
    # Test loading a monster that should exist locally (if skeleton.json exists)
    print("\n1. Testing local monster loading:")
    skeleton = db.load_monster("Skeleton")
    if skeleton:
        print(f"  Loaded {skeleton.name} from local database")
        print(f"  Source: {db.get_monster_source('Skeleton')}")
    
    # Test loading a monster that might need to be downloaded
    print("\n2. Testing auto-download (if enabled):")
    if db.is_auto_download_enabled():
        # Try a monster that probably doesn't exist locally
        test_monster = "Orc"  # Common monster that should be downloadable
        print(f"  Source of '{test_monster}': {db.get_monster_source(test_monster)}")
        
        orc = db.load_monster(test_monster)
        if orc:
            print(f"  Successfully loaded {orc.name}")
            print(f"  HP: {orc.max_hp}, AC: {orc.get_ac()}")
        else:
            print(f"  Failed to load {test_monster}")
    else:
        print("  Auto-download not available")
    
    # Show available monsters
    print("\n3. Available monsters:")
    monsters = db.list_monsters(include_downloadable=True)
    for i, monster in enumerate(monsters[:10]):  # Show first 10
        print(f"  {monster}")
    
    if len(monsters) > 10:
        print(f"  ... and {len(monsters) - 10} more")
    
    print("\n=== Demo Complete ===")
