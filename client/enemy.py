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

    def calculate_ai_path(self, player_pos, grid_tiles, behavior='chase'):
        """
        Enhanced AI: Plan path based on behavior ('chase', 'patrol', 'retreat').
        - Chase: Towards player.
        - Patrol: Random nearby hex.
        - Retreat: Away from player.
        - References: a_star from utils/pathfinding.py.
        - Returns: Planned path or [] if none.
        """
        start_hex = tuple(self.pos)
        if behavior == 'retreat':
            # Find hex furthest from player within MV
            goal_hex = self.find_retreat_position(player_pos, grid_tiles)
        elif behavior == 'patrol':
            goal_hex = self.find_patrol_position(grid_tiles)
        else:  # chase
            goal_hex = tuple(player_pos)
        if goal_hex and goal_hex != start_hex:
            path = a_star(start_hex, goal_hex, grid_tiles, self.mv_limit)
            return path or []
        return []

    def find_retreat_position(self, player_pos, grid_tiles):
        """Find a hex away from player."""
        px, py = player_pos
        max_dist = 0
        best_hex = None
        for q in range(-self.mv_limit, self.mv_limit + 1):
            for r in range(-self.mv_limit, self.mv_limit + 1):
                if abs(q + r) > self.mv_limit:
                    continue
                hx, hy = self.pos[0] + q, self.pos[1] + r
                if (hx, hy) in grid_tiles and not grid_tiles[(hx, hy)].blocked:
                    dist = hex_distance(hx, hy, px, py)
                    if dist > max_dist:
                        max_dist = dist
                        best_hex = (hx, hy)
        return best_hex

    def find_patrol_position(self, grid_tiles):
        """Find a random nearby unblocked hex."""
        from random import choice
        candidates = []
        for q in range(-self.mv_limit, self.mv_limit + 1):
            for r in range(-self.mv_limit, self.mv_limit + 1):
                if abs(q + r) > self.mv_limit:
                    continue
                hx, hy = self.pos[0] + q, self.pos[1] + r
                if (hx, hy) in grid_tiles and not grid_tiles[(hx, hy)].blocked and (hx, hy) != tuple(self.pos):
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
        Updates enemy position during movement (LERP towards next hex, mirrors game.py player movement).
        - References: game.py movement loop (LERP), MOVE_SPEED.
        - Purpose: Smooth animation towards target hex, then advance path.
        """
        if not self.is_moving or not self.queued_path or self.current_path_index >= len(self.queued_path):
            return False  # Completed

        target_hex = self.queued_path[self.current_path_index]
        target_screen = self.hex_to_screen(target_hex[0], target_hex[1], grid_hex_size, screen)

        # Calculate distance to target
        dx = target_screen[0] - self.screen_pos[0]
        dy = target_screen[1] - self.screen_pos[1]
        dist = math.hypot(dx, dy)

        if dist < 5:  # Reached target hex
            # Update both screen and hex positions
            self.screen_pos = list(target_screen)
            self.pos = list(target_hex)
            self.current_path_index += 1

            # Check if path is complete
            if self.current_path_index >= len(self.queued_path):
                self.is_moving = False
                self.queued_path = []
                self.current_path_index = 0
                print(f"Enemy completed path, now at hex {self.pos}")
                return True  # Path complete
            return False  # Continue to next hex in path
        else:
            # LERP towards target (smooth movement)
            # Normalize the movement speed by distance to ensure consistent speed
            if dist > 0:
                move_factor = (move_speed * dt) / dist
                t = min(1.0, move_factor)
                self.screen_pos[0] += dx * t
                self.screen_pos[1] += dy * t
            return False  # Still moving

    def hex_to_screen(self, q, r, size, screen):
        """Convert hex coordinates to screen coordinates."""
        x = size * 3/2 * q
        y = size * math.sqrt(3) * (r + q/2)
        return (int(x + screen.get_width() // 2), int(y + screen.get_height() // 2))

    def take_turn(self, player_pos, grid_tiles, attack_enabled=False):
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

        if behavior == 'chase':
            # Simple direct movement towards player for testing
            print(f"Enemy attempting to move towards player at {player_pos}")
            # Try to find a simple path to an adjacent hex closer to player
            best_hex = None
            best_dist = dist

            # Check all 6 adjacent hexes
            for dq in [-1, 0, 1]:
                for dr in [-1, 0, 1]:
                    if dq == 0 and dr == 0:
                        continue
                    if abs(dq + dr) > 1:  # Skip diagonal moves for hex grid
                        continue

                    new_q = self.pos[0] + dq
                    new_r = self.pos[1] + dr
                    new_hex = (new_q, new_r)

                    if new_hex in grid_tiles and not grid_tiles[new_hex].blocked:
                        new_dist = hex_distance(new_q, new_r, player_pos[0], player_pos[1])
                        if new_dist < best_dist:
                            best_dist = new_dist
                            best_hex = new_hex

            if best_hex:
                simple_path = [tuple(self.pos), best_hex]
                print(f"Enemy found simple path: {simple_path}")
                self.start_movement(simple_path)
            else:
                print(f"Enemy found no adjacent hexes to move to")

        # Return next active state if needed

    def draw(self, screen, dt):
        """
        Renders enemy and updates animation (references game.py draw and char_renderer.update/draw).
        - References: game.py char_renderer usage, dt from clock.tick.
        - Purpose: Visuals: Animated red-tinted sprite during move for captivating effect.
        """
        self.renderer.update(dt, self.is_moving)
        self.renderer.draw_enemy(screen, int(self.screen_pos[0]), int(self.screen_pos[1]))
