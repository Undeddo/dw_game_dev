"""
DW Reference: NPCs with MV, initiatives in combat (Book 1, p.84-85). Enemy acts like player but AI-driven.
Purpose: Manage enemy position, movement path, AI (chase player), and integration with combat rounds.
Dependencies: utils/pathfinding.py, utils/hex_utils.py, client/render/enemy_renderer.py; references game.py for player pos.
Ext Hooks: Add HP, attacks/defenses later; support multiple enemies.
Client Only: AI logic; position syncs with PvP/multiplayer via server (offline now).
Grand Scheme: Granular enemy logic class, keeping game.py lean. Manages path calculation (reuse a_star), smooth movement mirroring player (LERP from game.py), and simple AI (direct chase) for lightweight gameplay.
"""

import math
from client.render.enemy_renderer import EnemyRenderer
from client.map.tile import Tile
from core.pathfinding.a_star import a_star
from core.hex.utils import hex_distance

class Enemy:
    def __init__(self, start_pos=(5, 5), mv_limit=6, behavior='chase', grid_hex_size=50, screen=None):
        """
        Initializes enemy at start hex with MV limit (references player in game.py).
        Added behavior parameter for AI variants: 'chase', 'patrol', 'retreat'.
        - References: Player setup in game.py (char_pos, mv_limit), hex_grid.py for tiling.
        - Purpose: Spawn enemy for combat encounters, with flexible AI path-planning.
        """
        self.pos = list(start_pos)  # Hex position (references char_pos)
        # Initialize screen position based on hex position
        if screen:
            self.screen_pos = list(self.hex_to_screen(start_pos[0], start_pos[1], grid_hex_size, screen))
        else:
            self.screen_pos = [400, 300]  # Fallback center position
        self.renderer = EnemyRenderer()  # Renders enemy sprite (references character_renderer usage)
        self.mv_limit = 99  # Unlimited for enemies to chase, adjustable
        self.hp = 10  # Basic HP (for later hit mechanics)
        self.max_hp = 10  # For retreat logic
        self.queued_path = []  # Path to follow (references queued_path in game.py)
        self.current_path_index = 0
        self.is_moving = False  # True when animating move (references is_moving)
        self.behavior = behavior  # AI behavior: 'patrol', 'chase', 'retreat'
        self.chase_distance = 10  # Switch to chase if within this hexes
        self.retreat_threshold = 3  # Retreat if HP below this percentage
        self.targeting_player = False  # True if this enemy is targeting the player

    def set_screen_pos(self, screen_pos):
        """
        Updates enemy screen position (called from game.py after hex_to_screen).
        - References: Player screen_pos management in game.py hex_to_screen.
        - Purpose: Sync visual position for smooth drawing.
        """
        self.screen_pos = list(screen_pos)

    def find_free_hex_adjacent_to_target(self, target_pos, grid_tiles, occupied=None):
        """Find closest free hex within mv_limit range from target, closest to self."""
        if occupied is None: occupied = set()
        closest = None
        min_dist = float('inf')
        mv_limit = self.mv_limit  # to reach within that
        for q in range(-mv_limit, mv_limit + 1):
            for r in range(-mv_limit, mv_limit + 1):
                if abs(q + r) > mv_limit: continue
                hx = target_pos[0] + q
                hy = target_pos[1] + r
                # limit to reasonable grid size
                if abs(hx) > 50 or abs(hy) > 50: continue
                if (hx,hy) in grid_tiles and not grid_tiles[(hx,hy)].blocked and (hx,hy) not in occupied:
                    dist = hex_distance(hx, hy, target_pos[0], target_pos[1])
                    if dist < min_dist:
                        min_dist = dist
                        closest = (hx, hy)
        return closest

    def calculate_ai_path(self, player_pos, grid_tiles, enemies, behavior='chase', occupied=None):
        """
        Enhanced AI: Plan path based on behavior ('chase', 'patrol', 'retreat').
        - Chase: Towards closest free hex adjacent to player.
        - Patrol: Random nearby free hex.
        - Retreat: Free hex furthest from player.
        - References: a_star from utils/pathfinding.py.
        - Returns: Planned path or [] if none.
        - Blocked: Hexes occupied by entities are unpassable except start.
        """
        start_hex = tuple(self.pos)
        # Calculate occupied positions first
        if occupied is None:
            occupied = {tuple(enem.pos) for enem in enemies if enem.hp > 0}
            occupied.add(tuple(player_pos))
        if behavior == 'retreat':
            goal_hex = self.find_retreat_position(player_pos, grid_tiles, occupied)
        elif behavior == 'patrol':
            goal_hex = self.find_patrol_position(grid_tiles, occupied)
        else:  # chase
                # Find free hex adjacent to player
                goal_hex = self.find_free_hex_adjacent_to_target(player_pos, grid_tiles, occupied)

        if goal_hex and goal_hex != start_hex:
            # Modify grid to block occupied hexes except start
            modified_tiles = {}
            for k, v in grid_tiles.items():
                blocked = v.blocked or ((k != start_hex) and (k == tuple(player_pos)))
                new_tile = Tile(v.type)
                new_tile.cost = v.cost
                new_tile.blocked = blocked
                new_tile.color = v.color
                modified_tiles[k] = new_tile
            path = a_star(start_hex, goal_hex, modified_tiles, self.mv_limit)
            return path or []
        return []

    def find_retreat_position(self, player_pos, grid_tiles, occupied=None):
        """Find a hex away from player."""
        if occupied is None: occupied = set()
        px, py = player_pos
        max_dist = 0
        best_hex = None
        for q in range(-self.mv_limit, self.mv_limit + 1):
            for r in range(-self.mv_limit, self.mv_limit + 1):
                if abs(q + r) > self.mv_limit:
                    continue
                hx, hy = self.pos[0] + q, self.pos[1] + r
                if (hx, hy) in grid_tiles and not grid_tiles[(hx, hy)].blocked and abs(hx) <= 10 and abs(hy) <= 10 and (hx, hy) not in occupied:
                    dist = hex_distance(hx, hy, px, py)
                    if dist > max_dist:
                        max_dist = dist
                        best_hex = (hx, hy)
        return best_hex

    def find_patrol_position(self, grid_tiles, occupied=None):
        """Find a random nearby unblocked hex."""
        if occupied is None: occupied = set()
        from random import choice
        candidates = []
        for q in range(-self.mv_limit, self.mv_limit + 1):
            for r in range(-self.mv_limit, self.mv_limit + 1):
                if abs(q + r) > self.mv_limit:
                    continue
                hx, hy = self.pos[0] + q, self.pos[1] + r
                if (hx, hy) in grid_tiles and not grid_tiles[(hx, hy)].blocked and abs(hx) <= 10 and abs(hy) <= 10 and (hx, hy) not in occupied:
                    candidates.append((hx, hy))
        if candidates:
            return choice(candidates)
        return None

    def start_movement(self, path):
        """
        Queues enemy movement path and starts it (references game.py path setting).
        - References: queued_path, current_path_index, is_moving in game.py combat.
        - Purpose: Initiate smooth enemy move after AI path calculation.
        """
        self.queued_path = path
        self.current_path_index = 0
        if path:
            self.is_moving = True
            print(f"Enemy starting movement from {self.pos} along path: {path}")

    def update_movement(self, grid_hex_size, screen, move_speed, dt):
        """
        Updates enemy position during movement, mirroring the player's path-following logic exactly.
        """
        if self.is_moving and self.queued_path and self.current_path_index < len(self.queued_path):
            target_hex = self.queued_path[self.current_path_index]
            target_screen = self.hex_to_screen(target_hex[0], target_hex[1], grid_hex_size, screen)
            dx = target_screen[0] - self.screen_pos[0]
            dy = target_screen[1] - self.screen_pos[1]
            dist = math.hypot(dx, dy)
            if dist < 10:
                self.screen_pos = list(target_screen)
                self.pos = list(target_hex)
                self.current_path_index += 1
                print(f"Enemy reached hex: {target_hex}")
            else:
                t = min(1.0, (move_speed * dt) / dist)
                self.screen_pos[0] += dx * t
                self.screen_pos[1] += dy * t

        if self.queued_path and self.current_path_index >= len(self.queued_path):
            self.queued_path = []
            self.current_path_index = 0
            self.is_moving = False
            print(f"Enemy completed path, now at hex {self.pos}")
            return True  # Path complete
        return False  # Still moving or completed

    def hex_to_screen(self, q, r, size, screen):
        """Convert hex coordinates to screen coordinates."""
        x = size * 3/2 * q
        y = size * math.sqrt(3) * (r + q/2)
        return (int(x + screen.get_width() // 2), int(y + screen.get_height() // 2))

    def take_turn(self, enemies, player_pos, grid_tiles, attack_enabled=False):
        """
        Enemy turn: Decide behavior and calculate AI path (references game.py combat tick).
        - Behavior logic: Retreat if low HP, chase if close, patrol if far.
        - References: game.py combat round advance ('start planned movement').
        - Purpose: Dynamic AI for more engaging gameplay.
        """
        # Reset attack flag
        self.attack_this_turn = False

        # Decide behavior
        dist = hex_distance(self.pos[0], self.pos[1], player_pos[0], player_pos[1])
        if self.hp <= self.retreat_threshold:
            behavior = 'retreat'
        elif dist <= self.chase_distance:
            behavior = 'chase'
        else:
            behavior = 'patrol'

        self.targeting_player = (behavior == 'chase')  # Target if chasing player

        print(f"Enemy at {self.pos} taking turn - dist to player: {dist}, behavior: {behavior}")

        # If adjacent and attacks enabled, attack instead of moving
        if attack_enabled and dist <= 3:
            self.attack_this_turn = True

        if self.attack_this_turn:
            path = []
        else:
            path = self.calculate_ai_path(player_pos, grid_tiles, enemies, behavior)
        if path and not self.is_moving:
            self.start_movement(path)
            print(f"Enemy {behavior}ing with path length: {len(path)}")
        elif path:
            print(f"Enemy wants to {behavior} but already moving")
        else:
            print(f"Enemy failed to find path for {behavior}")

        # Return next active state if needed

    def draw(self, screen, dt):
        """
        Renders enemy and updates animation (references game.py draw and char_renderer.update/draw).
        - References: game.py char_renderer usage, dt from clock.tick.
        - Purpose: Visuals: Animated red-tinted sprite during move for captivating effect.
        """
        self.renderer.update(dt, self.is_moving)
        self.renderer.draw_enemy(screen, int(self.screen_pos[0]), int(self.screen_pos[1]))
