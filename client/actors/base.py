"""
DW Reference: Actor stats design (Book 1, pp. 84-85: MR = STR + AGI, HP roll, etc.).
Purpose: Modular actor dataclasses for stats - centralize STR/AGI/HP/MV for players/enemies.
Dependencies: None (standalone dataclass; will integrate into Enemy class in client/enemy.py).
Ext Hooks: Future Items/Equipment (modifiers to stats); merges with client/actors/ai.py for behaviors.
Game Loop: Instantiated in client/game_state.py and client/enemy.py; no direct rendering.
"""

from dataclasses import dataclass, field
from typing import Optional
from utils.dice import roll_d6

@dataclass
class ActorStats:
    """
    Core actor stats dataclass - human-readable and serializable.
    - MR (Magical Resistance) = STR + AGI; used for future magic/flee checks.
    - HP rolls: roll_d6() per MR for variety (GD-inspired randomness).
    - MV: Exploration default (but can be race/class modded).
    """
    name: str = "Actor"  # For debugging/log names
    str: int = 10        # Strength; also affects melee damage roll
    agi: int = 10        # Agility; affects ranged evasion/Hit rolls
    hp: int = field(init=False)  # Calculated on init: roll_d6() * (str // 2 + 1) for scaling
    max_hp: int = field(init=False)  # Set to hp on init
    mv: int = 6          # Movement points; exploration overrides to 99
    mr: int = field(init=False)  # Magical Resistance = str + agi

    def __post_init__(self):
        """Calculate derived stats on init."""
        self.mr = self.str + self.agi
        self.hp = roll_d6() * (self.str // 2 + 1)  # Random HP based on STR (min 6, max var)
        self.max_hp = self.hp  # For HP bar rendering

    def update_hp(self, damage: int):
        """Apply damage; clamp to 0."""
        self.hp = max(0, self.hp - damage)

    def get_damage_bonus(self, melee: bool = True) -> int:
        """Return damage modifier; melee uses STR, ranged uses AGI."""
        if melee:
            return self.str // 4  # +STR damage (scales with strong chars)
        else:
            return self.agi // 5  # Slight AGI bonus for ranged

    def is_alive(self) -> bool:
        """Convenience: HP > 0 check."""
        return self.hp > 0
