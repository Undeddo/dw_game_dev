"""
DW Reference: Lockstep combat rounds (Book 1, p. 39-42), simultaneous resolution.
Purpose: Manage combat mode logic for true lockstep - plan phase then execute on tick.
Dependencies: client/game_state.py, client/enemy.py, core/pathfinding/a_star.py, core/hex/utils.py.
Ext Hooks: Future CombatScheduler for advanced rounds; integrates with Player/Enemy stats.
Combat Only: Called from game.py event/tick handlers; decoupled from rendering.
"""

import time
from client.game_state import GameState
from core.pathfinding.a_star import a_star
from core.hex.utils import hex_distance
from utils.dice import roll_d6
from core.config import ENEMY_RANGED_ATTACK_ENABLED

class CombatSystem:
    """
    Manages lockstep combat rounds: Plan phase (player clicks plan path, enemies decide paths) followed by Execute phase (tick moves all simultaneously, then attacks resolve).
    - Dependencies: GameState for pos/enemies, Enemy.take_turn for AI, but intercepts to store instead of immediate execution.
    - Grand Scheme: Keeps game.py thin; handles planning/execution/stats integration.
    """

    def __init__(self, state: GameState, grid_tiles, grid):
        """
        Init with GameState, grid tiles, and grid object; combat_system hooks here.
        - state: Central state (players, enemies, mode).
        - grid_tiles: Reference to Grid.tiles for blocking/MV checks.
        - grid: Grid object for setting highlights.
        """
        self.state = state
        self.grid_tiles = grid_tiles
        self.grid = grid  # Reference to HexGrid for set_path_highlight
        self.enemy_planned_paths = []  # List of (enem, path) for prepared but not executed enemy moves
        self.last_enemy_plan_time = 0.0  # Throttle enemy re-planning to reduce spam

    def plan_player_path(self, goal_hex):
        """
        Called on mouse click in combat: Plan player's path, store for tick execution, prevent planning during movement.
        - Computes path with MV limits, blocks occupied hexes for fairness.
        - Returns True if path set; False otherwise (e.g., invalid).
        """
        if self.state.is_moving:
            print("Player still moving, can't plan new path")
            return False
        start_hex = tuple(self.state.player_pos)
        mv_limit = self.state.get_mv_limit()

        # Block occupied hexes (DW: no occupation)
        alive_enemies = [enem for enem in self.state.enemies if enem.hp > 0]
        for enem in alive_enemies:
            occupied = tuple(enem.pos)
            self.grid_tiles[occupied].blocked = True

        path = a_star(start_hex, goal_hex, self.grid_tiles, max_distance=mv_limit)

        # Reset blocks
        for enem in alive_enemies:
            occupied = tuple(enem.pos)
            self.grid_tiles[occupied].blocked = False

        if path:
            self.state.commanded_path = path  # Store planned path
            self.grid.set_path_highlight([start_hex] + path)  # Include start hex for highlight to start from player pos
            print(f"Player planned path: {[start_hex] + path}")
            # Trigger enemy planning after player plans
            self._plan_enemy_actions()
            return True
        else:
            print("No valid player path found")
            return False

    def _plan_enemy_actions(self):
        """
        Private: Plan enemy paths after player plans; store for later execution, don't move yet.
        - Enemies take turn if close enough or chasing; store path if decided to move.
        - Throttled to avoid spam; uses Enemy.take_turn but intercepts for delayed execution.
        """
        current_time = time.time()
        if current_time - self.last_enemy_plan_time < 0.1:  # Slight delay to reduce spam
            return
        self.last_enemy_plan_time = current_time

        self.enemy_planned_paths = []  # Reset old plans
        for enem in self.state.enemies:
            if enem.hp > 0:
                dist = hex_distance(enem.pos[0], enem.pos[1], self.state.player_pos[0], self.state.player_pos[1])
                behavior = 'chase' if dist <= enem.chase_distance else 'patrol'
                # Decide behavior state (chase if chasing, retreat if low HP)
                if enem.hp <= enem.max_hp * enem.retreat_threshold:
                    behavior = 'retreat'

                path = enem.calculate_ai_path(self.state.player_pos, self.grid_tiles, self.state.enemies, behavior)
                if path:
                    self.enemy_planned_paths.append((enem, path))
                    # Store path only; start_movement called on tick for lockstep
                    print(f"Enemy {enem.pos} planned {behavior} with path length: {len(path)}")
                else:
                    # No move: Prepare attack if in range
                    enem.attack_this_turn = (dist <= 3)  # Check ranges later on exec
                    print(f"Enemy {enem.pos} plans no move, attack? {enem.attack_this_turn}")

    def execute_round_tick(self):
        """
        Called on round timer tick: Execute all planned paths simultaneously (LERP-style), then resolve attacks based on end positions.
        - Moves player and enemies if paths set; resets after execution.
        - Attacks resolve nearest adjacent after movement.
        """
        # Execute player path if planned
        if self.state.commanded_path and not self.state.is_moving:
            self.state.queued_path = self.state.commanded_path
            self.state.current_path_index = 0
            self.state.is_moving = True
            self.state.commanded_path = None
            print(f"Player executing path: {self.state.queued_path}")

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

    def _resolve_combat_attacks(self):
        """
        Private: After movements, check for attacks based on final positions. Auto-attack player if adjacent.
        - Player attacks adjacent enemy; enemies attack player.
        - Use dice rolls; update HP.
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
        Called every frame: Handle LERP movement for player and enemies during execution.
        - Mirrors game's update path-following but centralized here.
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
            else:  # LERP
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
        """Quick local hex conversion."""
        x = size * 3/2 * q
        y = size * (1.5 * r + 0.5 * q)
        return (int(x + screen.get_width() // 2), int(y + screen.get_height() // 2))
