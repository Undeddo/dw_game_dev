"""
DW Reference: Input handling for game events.
Purpose: Handle all user input events and translate them to game actions.
Dependencies: client/game_state.py, client/map/hex_grid.py, core/pathfinding/a_star.py, core/hex/utils.py
Ext Hooks: Future input mapping, keybinds.
Client Only: Input handling only; no game logic.
"""

import time
import threading
import requests
from core.pathfinding.a_star import a_star
from core.hex.utils import hex_distance
from utils.dice import roll_d6
from client.enemy import Enemy

class InputHandler:
    """
    Handles all user input events and translates them to game actions.
    Separates input logic from game logic for better modularity.
    """
    
    def __init__(self, state, grid):
        """
        Initialize the input handler with references to game state and grid.
        
        Args:
            state: GameState instance for accessing game state
            grid: HexGrid instance for grid operations
        """
        self.state = state
        self.grid = grid
        self.server_offline = False  # Fallback flag; links to network robustness
    
    def handle_mouse_click(self, mouse_pos, state, grid, enemies, screen):
        """Handle mouse click events."""
        if state.defeated:
            return  # Dead, no movement or planning
            
        goal = grid.get_hex_at_mouse(mouse_pos, screen)
        if goal:
            # Handle based on mode
            if state.game_mode == 'exploration':
                self._handle_exploration_mode_click(goal, state, grid, screen)
            else:  # Combat mode
                self._handle_combat_mode_click(goal, state, grid, enemies)
    
    def _handle_exploration_mode_click(self, goal, state, grid, screen):
        """Handle mouse click in exploration mode."""
        # DEBUG: Print current movement state
        print(f"DEBUG INPUT: Current is_moving={state.is_moving}, path_validated={state.path_validated}")

        # Prevent path switching during movement until validation is complete
        if state.is_moving and not state.path_validated:
            print("Movement in progress, please wait for validation")
            return

        # Exploration: switch path without interruption
        # Use player_pos (hex coordinates) instead of char_screen_pos (screen coordinates)
        current_hex = tuple(state.player_pos)
        local_mv_limit = 99
        path = a_star(current_hex, goal, grid.tiles, local_mv_limit)

        print(f"DEBUG INPUT: Path found from {current_hex} to {goal}: {path}")

        if path:
            # Store initial position for rollback on rejection
            state.initial_char_pos = list(state.char_screen_pos)

            state.queued_path = path
            state.current_path_index = 0
            grid.set_path_highlight(path)
            state.is_moving = True
            state.path_validated = False

            print(f"DEBUG INPUT: Set is_moving=True, path_validated=False")
            print(f"DEBUG INPUT: Queued path length: {len(path)}")

            data = {"action": "move_path", "start": current_hex, "goal": tuple(goal), "grid": grid.get_grid_state(), "game_mode": state.game_mode}
            if not self.server_offline:
                validation_thread = threading.Thread(target=self._validate_path_async, args=(data,))
                validation_thread.daemon = True
                validation_thread.start()
                print("DEBUG INPUT: Started async validation thread")
            else:
                state.path_validated = True
                print("DEBUG INPUT: Server offline, auto-validating path")

            print(f"Exploration: switched to new path from {current_hex} to {goal}")
        else:
            print("No path found!")
    
    def _handle_combat_mode_click(self, goal, state, grid, enemies):
        """Handle mouse click in combat mode."""
        if state.is_moving:
            return  # Can't plan new move during movement
            
        # Calculate path from current position
        start_hex = tuple(state.player_pos)
        local_mv_limit = state.get_mv_limit()  # Use state method for mode-aware MV
        
        # Block living enemy hexes to prevent occupation (DW: hexes occupied by one entity)
        for enem in enemies:
            if enem.hp > 0:
                enemy_hex = tuple(enem.pos)
                grid.tiles[enemy_hex].blocked = True
                
        path = a_star(start_hex, goal, grid.tiles, local_mv_limit)
        
        for enem in enemies:  # Reset
            if enem.hp > 0:
                enemy_hex = tuple(enem.pos)
                grid.tiles[enemy_hex].blocked = False
                
        if path:
            grid.set_path_highlight(path)
            state.commanded_path = path  # Store planned path for combat system
            # Have enemies start their turn simultaneously in combat
            for enem in enemies:
                if enem.hp > 0:
                    enem.take_turn(list(enemies), state.player_pos, grid.tiles)
                    
            data = {"action": "move_path", "start": start_hex, "goal": tuple(goal), "grid": grid.get_grid_state(), "game_mode": state.game_mode}
            validation_thread = threading.Thread(target=self._validate_combat_path_async, args=(path, data))
            validation_thread.daemon = True
            validation_thread.start()
            print("Combat: planned path set, validating async")
        else:
            print("No path found!")
    
    def handle_keydown(self, key, state, grid):
        """Handle keyboard input."""
        if key == ord('c'):
            state.switch_mode('combat')
            if state.is_moving:
                state.is_moving = False
            print("Switched to combat mode")
        elif key == ord('e'):
            state.switch_mode('exploration')
            print("Switched to exploration mode")
    
    def _validate_path_async(self, data):
        """Async validation for exploration mode."""
        from core.config import SERVER_URL

        print("DEBUG VALIDATION: Starting async validation")

        try:
            resp = requests.post(f"{SERVER_URL}/api/move_path", json=data, timeout=5.0)
            if resp.status_code == 200:
                result = resp.json()
                approved_path = [tuple(p) for p in result.get("approved_path", [])]

                print(f"DEBUG VALIDATION: Server response - approved_path={approved_path}")

                if approved_path:
                    self.state.path_validated = True
                    print("Exploration path validated by server!")
                else:
                    # CRITICAL FIX: Reset player position to start of failed path
                    print("Server rejected exploration path, stopping movement")
                    self.state.is_moving = False
                    self.state.queued_path = []
                    self.state.current_path_index = 0

                    # Reset player to their original position before this movement attempt
                    if hasattr(self.state, 'initial_char_pos') and self.state.initial_char_pos:
                        self.state.char_screen_pos = list(self.state.initial_char_pos)
                    if 'start' in data:
                        self.state.player_pos = list(data['start'])

                    # Visual feedback
                    self.state.rejected_path = list(self.state.queued_path)  # Flash current path
                    self.state.rejected_flash_time = time.time()
                    self.state.rejected_message = "Path Rejected: Invalid route!"
                    self.state.rejected_message_time = time.time()
            else:
                print("Async validation failed, continuing with local path")
                self.state.path_validated = True
        except requests.exceptions.RequestException as e:
            print(f"Async server error: {e}, continuing with local path")
            self.state.path_validated = True
    
    def _validate_combat_path_async(self, path, data):
        """Async validation for combat mode."""
        from core.config import SERVER_URL
        try:
            resp = requests.post(f"{SERVER_URL}/api/move_path", json=data, timeout=5.0)
            if resp.status_code == 200:
                result = resp.json()
                approved_path = [tuple(p) for p in result.get("approved_path", [])]
                if approved_path:
                    if self.state.commanded_path is not None and approved_path != self.state.commanded_path:
                        self.grid.set_path_highlight(approved_path)
                        self.state.commanded_path = approved_path
                        print("Combat path approved, updated.")
                else:
                    print("Combat path rejected by server")
                    # Visual feedback: clear highlight, flash red
                    self.state.rejected_path = path
                    self.state.rejected_flash_time = time.time()
                    self.state.rejected_message = "Path Rejected!"
                    self.state.rejected_message_time = time.time()
                    self.grid.set_path_highlight([])
                    self.state.commanded_path = None
            else:
                print("Combat validation failed")
                # Treat as rejected
                self.state.rejected_path = path
                self.state.rejected_flash_time = time.time()
                self.state.rejected_message = "Validation Failed!"
                self.state.rejected_message_time = time.time()
                self.grid.set_path_highlight([])
                self.state.commanded_path = None
        except requests.exceptions.RequestException as e:
            print(f"Combat server error: {e}, keeping local path")
            # Keep local planned_path and highlight
            pass
