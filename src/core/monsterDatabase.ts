import { Combatant, CombatantData } from "./combatant.ts";

function sanitizeNameForFilename(name: string): string {
  if (!name) return "unnamed_monster";
  let safe_name = name.toLowerCase().replace(/\s+/g, '_');
  safe_name = safe_name.replace(/[^a-z0-9_-]/g, ''); // Allow letters, numbers, underscore, hyphen
  return safe_name || "unnamed_monster";
}

export class MonsterDatabase {
  private databasePath: string;

  constructor(databasePath: string = "data") {
    this.databasePath = databasePath;
    // Deno.mkdir is async, ensure directory exists (can be done at first operation or constructor)
    // For simplicity, we'll assume the directory exists or operations will handle it.
    // Or, we can add an async init method if needed.
    // Let's try to ensure it in constructor, making constructor potentially async or using top-level await if main module.
    // For a class constructor, direct async operations are tricky. Better to ensure path exists before operations.
  }

  private async ensureDbPathExists(): Promise<void> {
    try {
      await Deno.mkdir(this.databasePath, { recursive: true });
    } catch (error) {
      if (error instanceof Deno.errors.AlreadyExists) {
        return; // Directory already exists, which is fine
      }
      console.error(`Error creating database directory at ${this.databasePath}:`, error);
      throw error; // Re-throw if it's another error
    }
  }

  async saveMonster(combatant: Combatant): Promise<boolean> {
    await this.ensureDbPathExists();
    const safeName = sanitizeNameForFilename(combatant.name);
    const filename = `${safeName}.json`;
    // Deno.cwd() might not be what we want if the script is run from elsewhere.
    // For Deno, relative paths are usually relative to the current working directory.
    // If this class is imported, `this.databasePath` should be an absolute path or relative to a known root.
    // Assuming `this.databasePath` is correctly resolved (e.g. "data" in project root).
    const filepath = `${this.databasePath}/${filename}`;

    try {
      const data = combatant.toData(); // Use the new method name
      await Deno.writeTextFile(filepath, JSON.stringify(data, null, 2));
      return true;
    } catch (e) {
      console.error(`Error saving monster ${combatant.name} to ${filepath}:`, e);
      return false;
    }
  }

  async loadMonster(monsterName: string): Promise<Combatant | null> {
    // No need to ensureDbPathExists for loading, if it doesn't exist, file won't be found.
    let filenameToTry: string;
    if (monsterName.endsWith('.json')) {
      filenameToTry = monsterName;
    } else {
      const safeName = sanitizeNameForFilename(monsterName);
      filenameToTry = `${safeName}.json`;
    }

    const filepath = `${this.databasePath}/${filenameToTry}`;

    try {
      const fileContent = await Deno.readTextFile(filepath);
      const data = JSON.parse(fileContent) as CombatantData;
      const combatant = Combatant.fromData(data); // Use the new method name
      combatant.resetForCombat(); // Good practice
      return combatant;
    } catch (e) {
      // Try original name if sanitized one failed (Python version had this logic)
      if (!monsterName.endsWith('.json')) {
          const originalSafeName = monsterName.toLowerCase().replace(/\s+/g, '_');
          // A simpler original sanitization for lookup if the first one failed
          const originalFilename = `${originalSafeName}.json`;
          const originalFilepath = `${this.databasePath}/${originalFilename}`;
          if (originalFilename !== filenameToTry) { // Avoid re-trying the same file
            try {
                const fileContent = await Deno.readTextFile(originalFilepath);
                const data = JSON.parse(fileContent) as CombatantData;
                const combatant = Combatant.fromData(data);
                combatant.resetForCombat();
                return combatant;
            } catch (e2) {
                // console.warn(`Monster file not found: ${filepath} (and also not at ${originalFilepath})`, e, e2);
            }
          }
      }
      // If any error (NotFound, JSONParse, etc.)
      if (!(e instanceof Deno.errors.NotFound)) {
        console.error(`Error loading monster ${monsterName} from ${filepath}:`, e);
      }
      return null;
    }
  }

  async listMonsters(): Promise<string[]> {
    await this.ensureDbPathExists(); // Ensure path exists before trying to read from it
    const monsterNames: string[] = [];
    try {
      for await (const dirEntry of Deno.readDir(this.databasePath)) {
        if (dirEntry.isFile && dirEntry.name.endsWith('.json')) {
          const namePart = dirEntry.name.slice(0, -5); // Remove .json
          // Attempt to make it more readable: replace underscores, title case
          const readableName = namePart.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
          monsterNames.push(readableName);
        }
      }
      return monsterNames;
    } catch (e) {
      if (e instanceof Deno.errors.NotFound) {
        // If the directory itself doesn't exist, return empty list.
        return [];
      }
      console.error(`Error listing monsters from ${this.databasePath}:`, e);
      return [];
    }
  }

  async deleteMonster(monsterName: string): Promise<boolean> {
    // No need to ensureDbPathExists for deletion, if it doesn't exist, file won't be found for deletion.
    let filenameToDelete: string;
     if (monsterName.endsWith('.json')) { // Should ideally be called with readable name
      filenameToDelete = monsterName;
    } else {
      const safeName = sanitizeNameForFilename(monsterName);
      filenameToDelete = `${safeName}.json`;
    }
    const filepath = `${this.databasePath}/${filenameToDelete}`;

    try {
      await Deno.remove(filepath);
      return true;
    } catch (e) {
      if (e instanceof Deno.errors.NotFound) {
        // Try original name if sanitized one failed
        if (!monsterName.endsWith('.json')) {
            const originalSafeName = monsterName.toLowerCase().replace(/\s+/g, '_');
            const originalFilename = `${originalSafeName}.json`;
            const originalFilepath = `${this.databasePath}/${originalFilename}`;
            if (originalFilename !== filenameToDelete) {
                 try {
                    await Deno.remove(originalFilepath);
                    return true;
                 } catch (e2) {
                    // console.warn(`Monster file not found for deletion: ${filepath} (and also not at ${originalFilepath})`);
                    return false;
                 }
            }
        }
        // console.warn(`Monster file not found for deletion: ${filepath}`);
        return false;
      }
      console.error(`Error deleting monster ${monsterName} (${filepath}):`, e);
      return false;
    }
  }
}
