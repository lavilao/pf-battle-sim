export class CombatLog {
  private logEntries: string[] = [];

  constructor() {}

  addEntry(message: string): void {
    this.logEntries.push(message);
    console.log(message); // Also print for immediate feedback
  }

  getFullLog(): string {
    return this.logEntries.join("\n");
  }

  getLogEntries(): string[] {
    return [...this.logEntries]; // Return a copy
  }

  clear(): void {
    this.logEntries = [];
  }
}
