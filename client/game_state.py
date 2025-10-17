"""
DW Reference: State management per GAMEDESIGN.md exploration/combat modes.
Purpose: Centralize mutable game state for modularity - avoids globals in game.py.
Dependencies: client/enemy.py for Enemy list; core/config.py for settings.
Ext Hooks: Integrate Actor dataclass (client/actors/base.py) for stats in Step 4.
Game Loop: Accessed in client/game.py for updates; no rendering/effects here.
"""

from dataclasses import dataclass, field
from typing import List, Tuple
from core.config import TICK_TIME, ENEMY_RANGED_ATTACK_ENABLED
from client.enemy import Enemy
from client.actors.base import ActorStats

@dataclass
class GameState:
    """
    Encapsulates player, enemies, and global state per GAMEDESIGN.md.
    - References: Player MV/HP from config for combat; enemy pos for AI dependency.
    - Grand Scheme: Turn game.py into thin manager; all state changes via methods here.
    - Actor Integration: Player stats via ActorStats (STR/AGI/HP/MR); enemies will migrate to ActorStats in future.
    """
    defeated: bool = False  # Set to True when HP <= 0; blocks all player actions
    # Required fields (use None and init in __post_init__ for clarity)
    player_pos: List[int] = field(default_factory=lambda: [0, 0])  # (q, r) as list for mutability
    enemies: List[Enemy] = field(default_factory=list)   # List of Enemy instances; depends on client/enemy.py
    goal_pos: Tuple[int, int] = (9, 9)  # Quest target; maps goal check in game.py
    game_mode: str = 'exploration'  # 'exploration' or 'combat'; references mode switches in GD
    player_stats: ActorStats = field(default_factory=lambda: ActorStats(name="Player", str=12, agi=10))  # Player stats; HP derived from roll
    mv_limit: int = 6       # Default MV; exploration mode overrides to 99 per GD
    exploration_mv: int = 99  # Per GD relaxation; set via config
    win_message: str = ""   # Victory/defeat; depends on player_stats.hp and goal_pos
    win_message_time: float = 0.0  # Timestamp for UI fade; links to drawing logic
    WIN_DURATION: float = 10.0  # Display time; configurable

    # Movement/rendering states (not full globals, but core to state)
    char_screen_pos: List[float] = field(default_factory=lambda: [512, 384])  # Screen pos (x,y); updates via hex conversions
    queued_path: List[List[int]] = field(default_factory=list)  # Path of hexes [(q,r),...]; deps on a_star
    is_moving: bool = False      # True during lerp; prevents new plans
    current_path_index: int = 0  # Current index in queued_path for LERP movement
    path_validated: bool = False  # Server approval flag; hooks to client/network
    initial_char_pos: List[int] = None  # For validation; set on path start
    goal_target: List[int] = None  # Path target; used in rejection feedback
    server_offline: bool = False  # Fallback flag; links to network robustness
    combat_round: int = 0        # Tick counter; increments in combat
    commanded_path: List[List[int]] = None  # Planned combat path; clears on CR tick

    # AI and event timing (centralized to avoid game.py clutter)
    last_auto_attack: float = 0.0  # Timestamp for combat attacks; depends on dist

    def __post_init__(self):
        """Initialize mutable defaults if needed."""
        if self.char_screen_pos is None:
            self.char_screen_pos = [512, 384]  # Default center for 1024x768
        if self.queued_path is None:
            self.queued_path = []
        if self.commanded_path is None:
            self.commanded_path = None

    def update_hp(self, damage: int):
        """Adjust player HP via ActorStats; clamp to 0, set win/loss."""
        self.player_stats.update_hp(damage)
        if self.player_stats.hp <= 0:
            self.defeated = True
            self.win_message = "Defeated... Game Over!"
            self.win_message_time = 0.0  # Will be set externally

    @property
    def player_hp(self) -> int:
        """Getter: HP from player_stats for backward compat."""
        return self.player_stats.hp

    @property
    def max_player_hp(self) -> int:
        """Getter: Max HP from player_stats."""
        return self.player_stats.max_hp

    def switch_mode(self, new_mode: str):
        """Switch game_mode; reset mode-specific vars per GD."""
        if new_mode == 'combat':
            self.game_mode = 'combat'
            self.mv_limit = self.mv_limit  # Default 6; configurable
        elif new_mode == 'exploration':
            self.game_mode = 'exploration'
            self.mv_limit = self.exploration_mv
            # Clear combat states
            self.combat_round = 0
            self.commanded_path = None
        else:
            raise ValueError(f"Invalid mode: {new_mode}")

    def get_mv_limit(self) -> int:
        """Return effective MV based on mode; depends on switch_mode."""
        return self.exploration_mv if self.game_mode == 'exploration' else self.mv_limit

    def get_closest_enemy(self) -> Enemy:
        """Return closest living enemy with HP > 0; dist deps on hex_distance."""
        from core.hex.utils import hex_distance
        closest = None
        min_dist = float('inf')
        for enem in self.enemies:
            if enem.hp > 0:
                dist = hex_distance(self.player_pos[0], self.player_pos[1], enem.pos[0], enem.pos[1])
                if dist < min_dist:
                    min_dist = dist
                    closest = enem
        return closest

    def check_win_condition(self, current_time: float):
        """Check if player at goal; set win if so."""
        if tuple(self.player_pos) == self.goal_pos and not self.win_message:
            self.win_message = "Victory! You reached the goal hex!"
            self.win_message_time = current_time
