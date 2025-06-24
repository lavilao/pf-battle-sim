from typing import List

class CombatLog:
    """Handles logging of combat events"""
    def __init__(self):
        self.log_entries: List[str] = [] # Added type hint

    def add_entry(self, message: str):
        """Add an entry to the combat log"""
        self.log_entries.append(message)
        print(message)  # Also print for immediate feedback

    def get_full_log(self) -> str:
        """Get the complete combat log"""
        return "\n".join(self.log_entries)

    def clear(self):
        """Clear the combat log"""
        self.log_entries.clear()
