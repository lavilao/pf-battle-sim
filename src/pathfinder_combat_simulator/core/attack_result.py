from typing import List

class AttackResult:
    """Represents the result of an attack roll"""
    def __init__(self, attacker: str, target: str, attack_name: str):
        self.attacker = attacker
        self.target = target
        self.attack_name = attack_name
        self.attack_roll = 0
        self.total_attack_bonus = 0
        self.target_ac = 0
        self.is_hit = False
        self.is_critical_threat = False
        self.is_critical_hit = False
        self.damage_rolls: List[int] = [] # Changed from list to List[int] for clarity
        self.total_damage = 0
        self.damage_taken = 0
        self.special_effects: List[str] = [] # Changed from list to List[str] for clarity
