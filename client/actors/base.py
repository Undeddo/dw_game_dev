"""
DW Reference: Player/Enemy Stats (Book 1, p.37-38 for players, enemies).
Purpose: Define Actor, Player, Enemy dataclasses for game state.
Dependencies: dataclasses module.
Ext Hooks: Add more stats like armor, weapons.
Client Only: Game state representation.
"""

from dataclasses import dataclass
from typing import Tuple, List

@dataclass
class Actor:
    id: str
    hp: int
    max_hp: int
    position: Tuple[int, int]
    sprite: str  # Path or identifier

    def take_damage(self, damage: int):
        self.hp -= damage
        if self.hp < 0:
            self.hp = 0

@dataclass
class Player(Actor):
    auto_attack_interval: float = 2.0
    mv_limit: int = 6

@dataclass
class Enemy(Actor):
    mv_limit: int = 99
    behavior: str = 'chase'  # 'chase', 'patrol', 'retreat'
    chase_distance: int = 10
    retreat_threshold: float = 0.3  # HP percentage
    attack_this_turn: bool = False

    def should_retreat(self) -> bool:
        return self.hp / self.max_hp <= self.retreat_threshold

    def is_targeting_player(self) -> bool:
        return self.behavior == 'chase'
