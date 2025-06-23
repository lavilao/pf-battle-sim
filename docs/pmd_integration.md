# PMD Integration with Pathfinder Simulator

This document explains the integration between the PMD (Pathfinder Monster Database) project and the Pathfinder simulator, enabling automatic downloading and parsing of monsters from aonprd.com.

## Overview

The integration allows the simulator to automatically download monster statblocks when they're not available locally. When a user requests a monster that doesn't exist in the local database, the system will:

1. **Download** the monster page from aonprd.com using PMD's download logic
2. **Parse** the HTML using PMD's sophisticated parser
3. **Convert** the PMD format to the simulator's format
4. **Store** the result persistently for future use
5. **Return** a ready-to-use Combatant object

## Architecture

The integration follows SOLID principles with clear separation of concerns:

### Key Components

#### 1. `MonsterDownloader` (Single Responsibility)
- Handles HTTP requests to aonprd.com
- Implements rate limiting to be respectful to the server
- Generates proper URLs with encoding

#### 2. `PMDDataConverter` (Single Responsibility)
- Converts PMD data format to simulator format
- Maps damage types, ability scores, and other stats
- Handles edge cases like undead with null Constitution

#### 3. `PMDIntegrator` (Orchestrator)
- Coordinates the download, parse, and conversion process
- Manages PMD environment setup
- Main entry point for integration

#### 4. `EnhancedMonsterDatabase` (Open/Closed Principle)
- Extends the base MonsterDatabase without modifying it
- Adds auto-download capability while maintaining compatibility
- Can be used as a drop-in replacement

## Features

### ✅ Automatic Downloads
- Monsters are downloaded automatically when not found locally
- Rate limiting prevents overwhelming the source server
- Persistent caching avoids re-downloading

### ✅ Complete Integration
- Downloaded monsters work seamlessly with the combat simulator
- All simulator features (AC, attacks, saves, etc.) are supported
- Proper error handling and fallbacks

### ✅ SOLID Design
- **S**ingle Responsibility: Each class has one clear purpose
- **O**pen/Closed: Extensible without modifying existing code
- **L**iskov Substitution: Enhanced database can replace the base one
- **I**nterface Segregation: Clean, focused interfaces
- **D**ependency Inversion: Depends on abstractions, not concretions

### ✅ Test-Driven Development
- Comprehensive test suite covers all integration points
- Unit tests for data conversion
- Integration tests for the full pipeline
- Mocked external dependencies for reliable testing

## Dependencies

The integration uses `uv` for dependency management as specified in the user rules:

```toml
[project]
dependencies = [
    "beautifulsoup4==4.10.0",
    "requests==2.26.0", 
    "tqdm==4.62.3",
    "regex==2021.11.10"
]
```

## Usage

### Basic Usage

```python
from enhanced_monster_database import create_enhanced_monster_database

# Create enhanced database with auto-download
db = create_enhanced_monster_database()

# Load a monster (downloads if not available locally)
skeleton = db.load_monster("Skeleton")

# Use in combat
combat.add_combatant(skeleton)
```

### Advanced Usage

```python
# Check monster availability before loading
source = db.get_monster_source("Ancient Red Dragon")
print(f"Monster source: {source}")  # "local", "downloadable", or "unavailable"

# Preload multiple monsters
monsters_to_load = ["Orc", "Goblin", "Dire Wolf"]
results = db.preload_monster_list(monsters_to_load)

# Disable auto-download if needed
db.disable_auto_download()
```

## Data Conversion

The integration handles complex data conversion between PMD and simulator formats:

### Ability Scores
- PMD: `{"STR": 15, "DEX": 14, "CON": null}`
- Simulator: `{"strength": 15, "dexterity": 14, "constitution": 10}`
- Handles null values (common for undead)

### Attacks
- PMD: Complex nested structure with damage strings
- Simulator: Simplified Attack objects with parsed damage dice
- Extracts damage type, dice, and bonuses

### Armor Class
- PMD: Components breakdown with touch/flat-footed
- Simulator: Component-based AC system
- Maps natural armor, deflection, etc.

### Damage Reduction
- PMD: Array of DR entries with amounts and weaknesses
- Simulator: Single DR object with amount and type
- Takes the first (primary) DR entry

## Error Handling

The integration includes robust error handling:

- **Network errors**: Graceful failure when downloads fail
- **Parse errors**: Fallback when PMD parsing fails
- **Conversion errors**: Safe defaults for missing data
- **File errors**: Proper cleanup of temporary files

## Performance Considerations

- **Rate limiting**: Respects server resources (0.1s delay between requests)
- **Caching**: Downloaded monsters are stored permanently
- **Lazy loading**: Downloads only happen when monsters are requested
- **Memory efficient**: Large files are streamed, not loaded entirely

## Testing

Run the test suite to verify the integration:

```bash
# Using uv (recommended)
cd /home/lavilao570/pf
uv run python tests/test_pmd_integration.py

# Run demo
uv run python demo_pmd_integration.py
```

### Test Coverage

- ✅ URL generation for different monster names
- ✅ HTTP download with mocked responses
- ✅ PMD to simulator data conversion
- ✅ Full integration pipeline
- ✅ Local cache behavior
- ✅ Error handling for edge cases

## Future Enhancements

### Planned Features
- [ ] **Critical hit extraction**: Parse critical hit ranges from PMD data
- [ ] **Reach extraction**: Extract weapon reach from attack descriptions
- [ ] **Special abilities**: Convert PMD special abilities to simulator format
- [ ] **Spells**: Handle spellcasting monsters
- [ ] **Multiple sources**: Support other monster databases

### Optimization Opportunities
- [ ] **Parallel downloads**: Download multiple monsters concurrently
- [ ] **Incremental updates**: Check for updated monster data
- [ ] **Compression**: Store cached monsters in compressed format
- [ ] **Background sync**: Pre-download popular monsters

## Contributing

When extending the integration:

1. **Follow TDD**: Write tests first, then implement features
2. **Maintain SOLID**: Keep classes focused and extensible
3. **Use uv**: Manage dependencies with uv as per user rules
4. **Document changes**: Update this file and code comments
5. **Test thoroughly**: Ensure new features don't break existing functionality

## Troubleshooting

### Common Issues

**Auto-download not working:**
- Check internet connection
- Verify PMD dependencies are installed
- Check if rate limiting is too aggressive

**Parse errors:**
- Check if monster exists on aonprd.com
- Verify monster name spelling
- Check PMD parser for recent changes

**Conversion errors:**
- Check simulator format requirements
- Verify all required fields are present
- Look for data type mismatches

**Performance issues:**
- Check disk space for cached monsters
- Verify network speed
- Consider disabling auto-download for large batches

## Integration Success

The PMD integration successfully bridges the gap between the comprehensive Pathfinder monster database and the combat simulator. Users can now:

- ✅ **Request any monster** from the vast aonprd.com database
- ✅ **Get automatic downloads** without manual intervention  
- ✅ **Use immediately** in combat simulations
- ✅ **Benefit from caching** for improved performance
- ✅ **Trust the data** thanks to PMD's robust parsing

This integration transforms the simulator from a tool with limited monster data to one with access to the entire Pathfinder monster ecosystem, while maintaining clean architecture and following all specified development principles.
