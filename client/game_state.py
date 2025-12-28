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

@dataclass
class GameState:
    """
    Encapsulates all mutable game state information for the Dragon Warriors game.
    
    This class centralizes all game state variables to avoid global variables and
    provide a clean interface for game logic components. It handles player position,
    enemy states, game modes, combat mechanics, and win/loss conditions.
    
    The design follows the principle of keeping game.py thin by moving all state
    management to this centralized location.
    """
    
    # Required fields (use None and init in __post_init__ for clarity)
    player_pos: List[int] = field(default_factory=lambda: [0, 0])  # (q, r) as list for mutability
    enemies: List[Enemy] = field(default_factory=list)   # List of Enemy instances; depends on client/enemy.py
    goal_pos: Tuple[int, int] = (9, 9)  # Quest target; maps goal check in game.py
    game_mode: str = 'exploration'  # 'exploration' or 'combat'; references mode switches in GD
    player_hp: int = 10         # Current HP; hooks to future DamageSystem
    max_player_hp: int = 10  # For balancing; config.yaml binding later
    mv_limit: int = 6       # Default MV; exploration mode overrides to 99 per GD
    exploration_mv: int = 99  # Per GD relaxation; set via config
    win_message: str = ""   # Victory/defeat; depends on player_hp and goal_pos
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
    last_auto_attack: float = 0.0 # Timestamp for combat attacks; depends on dist
    current_turn: str = 'player' # 'player' or 'enemy' for turn-based combat

    def __post_init__(self):
        """Initialize mutable defaults if needed."""
        if self.char_screen_pos is None:
            self.char_screen_pos = [512, 384]  # Default center for 1024x768
        if self.queued_path is None:
            self.queued_path = []
        if self.commanded_path is None:
            self.commanded_path = None

    def update_hp(self, damage: int):
        """
        Update player's HP and check win/loss conditions.
        
        Args:
            damage (int): Damage to apply to player HP (negative values heal)
        """
        self.player_hp = max(0, self.player_hp - damage)
        if self.player_hp <= 0:
            self.win_message = "Defeated... Game Over!"
            self.win_message_time = 0.0  # Will be set externally

    def switch_turn(self):
        """Switch between player and enemy turns in combat mode."""
        self.current_turn = 'enemy' if self.current_turn == 'player' else 'player'
        print(f"Turn switched to: {self.current_turn}")

    def is_player_turn(self) -> bool:
        """
        Check if it's currently the player's turn in combat mode.
        
        Returns:
            bool: True if it's the player's turn, False otherwise
        """
        return self.current_turn == 'player'

    def is_enemy_turn(self) -> bool:
        """
        Check if it's currently the enemy's turn in combat mode.
        
        Returns:
            bool: True if it's the enemy's turn, False otherwise
        """
        return self.current_turn == 'enemy'

    def switch_mode(self, new_mode: str):
        """
        Switch between exploration and combat game modes.
        
        This method handles mode-specific state resets and configurations to ensure
        proper behavior in each game mode.
        
        Args:
            new_mode (str): Target game mode ('exploration' or 'combat')
            
        Raises:
            ValueError: If an invalid mode is specified
        """
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
        """
        Get the effective movement limit based on current game mode.
        
        Returns:
            int: Movement limit for current mode (exploration or combat)
        """
        return self.exploration_mv if self.game_mode == 'exploration' else self.mv_limit

    def get_closest_enemy(self) -> Enemy:
        """
        Find the closest living enemy to the player.
        
        Returns:
            Enemy: Closest living enemy, or None if no enemies are alive
        """
        from core.hex.utils import hex_distance
        closest = None
        min_dist = float('inf')
        player_q, player_r = self.player_pos[0], self.player_pos[1]
        
        for enem in self.enemies:
            if enem.hp > 0:
                dist = hex_distance(player_q, player_r, enem.pos[0], enem.pos[1])
                if dist < min_dist:
                    min_dist = dist
                    closest = enem
        return closest

    def check_win_condition(self, current_time: float):
        """
        Check if the player has reached the goal position and set win message if so.
        
        Args:
            current_time (float): Current timestamp for win message timing
        """
        if tuple(self.player_pos) == self.goal_pos and not self.win_message:
            self.win_message = "Victory! You reached the goal hex!"
            self.win_message_time = current_time

    @property
    def defeated(self):
        """
        Check if the player has been defeated (HP <= 0).
        
        Returns:
            bool: True if player is defeated, False otherwise
        """
        return self.player_hp <= 0
