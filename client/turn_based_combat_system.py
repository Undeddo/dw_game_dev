""" Turn-based combat system for Dragon Warriors game.
Purpose: Manage turn-based combat logic where player and enemy take turns attacking each other.
Dependencies: client/game_state.py, client/enemy.py, core/pathfinding/a_star.py, core/hex/utils.py.
"""

import time
from client.game_state import GameState
from core.pathfinding.a_star import a_star
from core.hex.utils import hex_distance
from utils.dice import roll_d6
from core.config import ENEMY_RANGED_ATTACK_ENABLED

class TurnBasedCombatSystem:
    """
    Manages turn-based combat where player and enemies take turns moving and attacking.
    
    This system implements a lockstep combat model where all actions are planned first, then
    executed simultaneously. It handles path planning for the player, AI decision-making for
    enemies, movement execution, and attack resolution in a turn-based fashion.
    """

    def __init__(self, state: GameState, grid_tiles, grid):
        """
        Initialize the turn-based combat system with game state and grid references.
        
        Args:
            state (GameState): Central game state object
            grid_tiles (dict): Grid tiles for pathfinding and blocking checks
            grid (HexGrid): Hex grid object for visual highlighting
        """
        self.state = state
        self.grid_tiles = grid_tiles
        self.grid = grid  # Reference to HexGrid for set_path_highlight
        self.enemy_planned_paths = []  # List of (enem, path) for prepared but not executed enemy moves
        self.last_enemy_plan_time = 0.0  # Throttle enemy re-planning to reduce spam

    def plan_player_path(self, goal_hex):
        """
        Plan a player movement path during combat turn.
        
        Args:
            goal_hex (tuple): Target hex coordinates (q, r)
            
        Returns:
            bool: True if path was successfully planned, False otherwise
        """
        if self.state.is_moving:
            print("Player still moving, can't plan new path")
            return False

        start_hex = tuple(self.state.player_pos)
        mv_limit = self.state.get_mv_limit()

        # Block occupied hexes (DW: no occupation)
        self._block_occupied_hexes()
        path = a_star(start_hex, goal_hex, self.grid_tiles, max_distance=mv_limit)
        # Reset blocks
        self._unblock_occupied_hexes()

        if path:
            self._store_player_path(path, start_hex)
            return True
        else:
            print("No valid player path found")
            return False

    def _block_occupied_hexes(self):
        """Block hexes occupied by alive enemies for pathfinding purposes."""
        alive_enemies = [enem for enem in self.state.enemies if enem.hp > 0]
        for enem in alive_enemies:
            occupied = tuple(enem.pos)
            self.grid_tiles[occupied].blocked = True

    def _unblock_occupied_hexes(self):
        """Unblock hexes occupied by alive enemies after pathfinding."""
        alive_enemies = [enem for enem in self.state.enemies if enem.hp > 0]
        for enem in alive_enemies:
            occupied = tuple(enem.pos)
            self.grid_tiles[occupied].blocked = False

    def _store_player_path(self, path, start_hex):
        """Store the planned path for player's turn execution."""
        self.state.commanded_path = path
        self.grid.set_path_highlight([start_hex] + path)
        print(f"Player planned path: {[start_hex] + path}")
        self._plan_enemy_actions()

    def _plan_enemy_actions(self):
        """
        Plan enemy actions after player plans their path. Store paths for later execution on enemy's turn.
        
        This method determines behaviors and calculates paths for all enemies, but doesn't execute them yet
        to maintain the lockstep execution model where all movements happen simultaneously.
        """
        current_time = time.time()
        if current_time - self.last_enemy_plan_time < 0.1:  # Slight delay to reduce spam
            return
        self.last_enemy_plan_time = current_time

        self.enemy_planned_paths = []  # Reset old plans
        for enem in self.state.enemies:
            if enem.hp > 0:
                dist = hex_distance(enem.pos[0], enem.pos[1], self.state.player_pos[0], self.state.player_pos[1])
                behavior = 'chase' if dist <= enem.chase_distance else 'patrol'  # Decide behavior

                # Decide behavior state (chase if chasing, retreat if low HP)
                if enem.hp <= enem.max_hp * enem.retreat_threshold:
                    behavior = 'retreat'

                path = enem.calculate_ai_path(self.state.player_pos, self.grid_tiles, self.state.enemies, behavior)
                if path:
                    self.enemy_planned_paths.append((enem, path))  # Store path only; start_movement called on tick for lockstep
                    print(f"Enemy {enem.pos} planned {behavior} with path length: {len(path)}")
                else:
                    # No move: Prepare attack if in range
                    enem.attack_this_turn = (dist <= 3)  # Check ranges later on exec
                    print(f"Enemy {enem.pos} plans no move, attack? {enem.attack_this_turn}")

    def execute_turn(self):
        """
        Execute actions for the current turn in combat mode.
        
        This method handles both player and enemy turns according to the turn order:
        - Player's turn: Execute player's planned path
        - Enemy's turn: Execute all enemy paths simultaneously, then resolve attacks
        """
        # Player's turn - execute planned path
        if self.state.is_player_turn() and self.state.commanded_path and not self.state.is_moving:
            self.state.queued_path = self.state.commanded_path
            self.state.current_path_index = 0
            self.state.is_moving = True
            self.state.commanded_path = None
            print(f"Player executing path: {self.state.queued_path}")

        # Enemy's turn - execute planned actions
        elif self.state.is_enemy_turn():
            # Execute enemy paths
            for enem, path in self.enemy_planned_paths:
                enem.queued_path = path
                enem.current_path_index = 0
                enem.is_moving = True
                print(f"Enemy {enem.pos} path executed on tick")

            # After all executions, resolve attacks (post-movement positions)
            self._resolve_combat_attacks()

            # Clear enemy plans after tick
            self.enemy_planned_paths = []

            # Switch turns after execution
            self.state.switch_turn()

    def _resolve_combat_attacks(self):
        """
        Resolve combat attacks based on final positions after movement is complete.
        
        This method handles all attack resolution in combat, including player auto-attacks
        and enemy attacks. It ensures that attacks happen only after all movement is done
        to maintain the lockstep execution model.
        """
        # Player auto-attack if adjacent to enemy and not moving
        if self.state.player_hp > 0 and not self.state.is_moving:
            closest = self.state.get_closest_enemy()
            if closest:
                dist = hex_distance(self.state.player_pos[0], self.state.player_pos[1], closest.pos[0], closest.pos[1])
                if dist == 1:  # Melee only for now
                    damage = roll_d6()
                    closest.hp -= damage
                    # Attack visualization (implement later)
                    print(f"Player auto-attacked enemy for {damage}! Enemy HP: {closest.hp}")
                    if closest.hp <= 0:
                        closest.pos = [-999, -999]
                        print("Enemy defeated!")
                        self.state.last_auto_attack = time.time()

        # Enemy attacks on player or each other (but focus player-centric)
        for enem in self.state.enemies:
            if enem.hp > 0 and enem.attack_this_turn:
                enem.attack_this_turn = False  # Reset
                dist = hex_distance(enem.pos[0], enem.pos[1], self.state.player_pos[0], self.state.player_pos[1])
                if dist == 1:
                    damage = roll_d6()
                    msg = f"Enemy melee for {damage}!"
                elif dist <= 3 and ENEMY_RANGED_ATTACK_ENABLED:
                    damage = max(0, roll_d6() - (dist - 1))
                    msg = f"Enemy ranged for {damage} at dist {dist}!"
                else:
                    damage = 0

                if damage:
                    self.state.update_hp(-damage)  # Use GameState method for HP and win check
                    print(f"{msg} Player HP: {self.state.player_hp}")
                    if self.state.player_hp <= 0:
                        print("Player defeated!")

    def update_positions(self, dt, grid_hex_size, screen, move_speed):
        """
        Update movement positions during combat execution phase using LERP interpolation.
        
        Args:
            dt (float): Delta time for smooth animation
            grid_hex_size (int): Size of hex tiles in pixels
            screen (pygame.Surface): Game screen surface
            move_speed (float): Movement speed in pixels per second
        """
        # Player movement
        if self.state.is_moving and self.state.queued_path and self.state.current_path_index < len(self.state.queued_path):
            target_hex = self.state.queued_path[self.state.current_path_index]
            target_screen = self._hex_to_screen(target_hex[0], target_hex[1], grid_hex_size, screen)
            dx = target_screen[0] - self.state.char_screen_pos[0]
            dy = target_screen[1] - self.state.char_screen_pos[1]
            dist = (dx**2 + dy**2)**0.5

            if dist < 5:  # Arrived
                self.state.char_screen_pos = [target_screen[0], target_screen[1]]
                self.state.player_pos = [target_hex[0], target_hex[1]]
                self.state.current_path_index += 1
                print(f"Player reached hex: {target_hex}")
            else:
                # LERP
                t = min(1.0, (move_speed * dt) / dist)
                self.state.char_screen_pos[0] += dx * t
                self.state.char_screen_pos[1] += dy * t

            if self.state.queued_path and self.state.current_path_index >= len(self.state.queued_path):
                self.state.queued_path = []
                self.state.current_path_index = 0
                self.state.is_moving = False

        # Enemy movements (each completes independently but simultaneously)
        for enem in self.state.enemies:
            if enem.hp > 0:
                enem.update_movement(grid_hex_size, screen, move_speed, dt)

    def _hex_to_screen(self, q, r, size, screen):
        """Convert hex coordinates to screen coordinates for rendering."""
        x = size * 3/2 * q
        y = size * (1.5 * r + 0.5 * q)
        return (int(x + screen.get_width() // 2), int(y + screen.get_height() // 2))
