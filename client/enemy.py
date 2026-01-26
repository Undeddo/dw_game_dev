"""
DW Reference: NPCs with MV, initiatives in combat (Book 1, p.84-85). Enemy acts like player but AI-driven.
Purpose: Manage enemy position, movement path, AI (chase player), and integration with combat rounds.
Dependencies: client/render/enemy_renderer.py, client/movement_controller.py, core.pathfinding.a_star, core.hex.utils
Ext Hooks: Add HP, attacks/defenses later; support multiple enemies.
Client Only: AI logic; position syncs with PvP/multiplayer via server (offline now).
Grand Scheme: Granular enemy logic class, keeping game.py lean. Manages path calculation (reuse a_star), smooth movement mirroring player (LERP from game.py), and simple AI (direct chase) for lightweight gameplay.
"""

import math
from client.render.enemy_renderer import EnemyRenderer
from client.movement_controller import MovementController
from client.map.tile import Tile
from core.hex.utils import hex_distance
from typing import List, Tuple, Optional, Set


class Enemy:
    """
    Enemy entity with AI-driven movement and combat capabilities.
    
    Features:
    - AI behavior management (chase, patrol, retreat)
    - Movement via unified MovementController
    - Combat integration
    - Rendering
    """
    
    def __init__(
        self,
        start_pos: Tuple[int, int],
        mv_limit: int = 6,
        behavior: str = 'chase',
        grid_hex_size: int = 50,
        screen_width: int = 1024,
        screen_height: int = 768
    ):
        """
        Initialize enemy at start hex with MV limit.
        
        Args:
            start_pos: Starting hex coordinates (q, r)
            mv_limit: Movement points limit
            behavior: AI behavior ('chase', 'patrol', 'retreat')
            grid_hex_size: Size of each hex in pixels
            screen_width: Screen width for coordinate conversion
            screen_height: Screen height for coordinate conversion
        """
        self.pos = list(start_pos)  # Keep as list for compatibility
        self.mv_limit = mv_limit
        self.behavior = behavior
        
        # Initialize screen position
        self.screen_pos = list(self._hex_to_screen(start_pos[0], start_pos[1], grid_hex_size, screen_width, screen_height))
        
        # Renderer
        self.renderer = EnemyRenderer()
        
        # Combat stats
        self.hp = 10
        self.max_hp = 10
        self.retreat_threshold = 3  # Retreat if HP below this percentage
        
        # Movement state
        self.queued_path: List[Tuple[int, int]] = []
        self.current_path_index = 0
        self.is_moving = False
        
        # AI state
        self.targeting_player = False
        self.chase_distance = 10
        self.attack_this_turn = False
        
        # Movement controller (will be set externally)
        self.movement_controller: Optional[MovementController] = None
        self.entity_id: str = f"enemy_{id(self)}"
    
    def set_movement_controller(self, controller: MovementController):
        """Set the movement controller for this enemy."""
        self.movement_controller = controller
    
    def _hex_to_screen(
        self,
        q: int,
        r: int,
        hex_size: int,
        screen_width: int,
        screen_height: int
    ) -> Tuple[float, float]:
        """Convert hex coordinates to screen coordinates."""
        x = hex_size * 1.5 * q
        y = hex_size * math.sqrt(3) * (r + q / 2)
        return (x + screen_width // 2, y + screen_height // 2)
    
    def set_screen_pos(self, screen_pos: Tuple[float, float]):
        """Update enemy screen position."""
        self.screen_pos = list(screen_pos)
    
    def find_free_hex_adjacent_to_target(
        self,
        target_pos: Tuple[int, int],
        grid_tiles: dict,
        occupied: Optional[Set[Tuple[int, int]]] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Find closest free hex within mv_limit range from target.
        
        Args:
            target_pos: Target hex coordinates
            grid_tiles: Dictionary of grid tiles
            occupied: Set of occupied hex coordinates
        
        Returns:
            Closest free hex, or None if none found
        """
        if occupied is None:
            occupied = set()
        
        closest = None
        min_dist = float('inf')
        
        for q in range(-self.mv_limit, self.mv_limit + 1):
            for r in range(-self.mv_limit, self.mv_limit + 1):
                if abs(q + r) > self.mv_limit:
                    continue
                
                hx = target_pos[0] + q
                hy = target_pos[1] + r
                
                # Limit to reasonable grid size
                if abs(hx) > 50 or abs(hy) > 50:
                    continue
                
                if (hx, hy) in grid_tiles and not grid_tiles[(hx, hy)].blocked and (hx, hy) not in occupied:
                    dist = hex_distance(hx, hy, target_pos[0], target_pos[1])
                    if dist < min_dist:
                        min_dist = dist
                        closest = (hx, hy)
        
        return closest
    
    def find_retreat_position(
        self,
        player_pos: Tuple[int, int],
        grid_tiles: dict,
        occupied: Optional[Set[Tuple[int, int]]] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Find hex furthest from player within mv_limit.
        
        Args:
            player_pos: Player hex coordinates
            grid_tiles: Dictionary of grid tiles
            occupied: Set of occupied hex coordinates
        
        Returns:
            Furthest free hex, or None if none found
        """
        if occupied is None:
            occupied = set()
        
        px, py = player_pos
        max_dist = 0
        best_hex = None
        
        for q in range(-self.mv_limit, self.mv_limit + 1):
            for r in range(-self.mv_limit, self.mv_limit + 1):
                if abs(q + r) > self.mv_limit:
                    continue
                
                hx = self.pos[0] + q
                hy = self.pos[1] + r
                
                if (hx, hy) in grid_tiles and not grid_tiles[(hx, hy)].blocked and abs(hx) <= 10 and abs(hy) <= 10 and (hx, hy) not in occupied:
                    dist = hex_distance(hx, hy, px, py)
                    if dist > max_dist:
                        max_dist = dist
                        best_hex = (hx, hy)
        
        return best_hex
    
    def find_patrol_position(
        self,
        grid_tiles: dict,
        occupied: Optional[Set[Tuple[int, int]]] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Find random nearby unblocked hex.
        
        Args:
            grid_tiles: Dictionary of grid tiles
            occupied: Set of occupied hex coordinates
        
        Returns:
            Random nearby free hex, or None if none found
        """
        if occupied is None:
            occupied = set()
        
        from random import choice
        candidates = []
        
        for q in range(-self.mv_limit, self.mv_limit + 1):
            for r in range(-self.mv_limit, self.mv_limit + 1):
                if abs(q + r) > self.mv_limit:
                    continue
                
                hx = self.pos[0] + q
                hy = self.pos[1] + r
                
                if (hx, hy) in grid_tiles and not grid_tiles[(hx, hy)].blocked and abs(hx) <= 10 and abs(hy) <= 10 and (hx, hy) not in occupied:
                    candidates.append((hx, hy))
        
        if candidates:
            return choice(candidates)
        return None
    
    def calculate_ai_path(
        self,
        player_pos: Tuple[int, int],
        grid_tiles: dict,
        enemies: List['Enemy'],
        behavior: str = 'chase',
        occupied: Optional[Set[Tuple[int, int]]] = None
    ) -> List[Tuple[int, int]]:
        """
        Calculate AI path based on behavior.
        
        Args:
            player_pos: Player hex coordinates
            grid_tiles: Dictionary of grid tiles
            enemies: List of all enemies
            behavior: AI behavior ('chase', 'patrol', 'retreat')
            occupied: Set of occupied hex coordinates
        
        Returns:
            Planned path, or empty list if none found
        """
        start_hex = tuple(self.pos)
        
        # Calculate occupied positions
        if occupied is None:
            occupied = {tuple(enem.pos) for enem in enemies if enem.hp > 0}
            occupied.add(tuple(player_pos))
        
        # Determine goal based on behavior
        if behavior == 'retreat':
            goal_hex = self.find_retreat_position(player_pos, grid_tiles, occupied)
        elif behavior == 'patrol':
            goal_hex = self.find_patrol_position(grid_tiles, occupied)
        else:  # chase
            goal_hex = self.find_free_hex_adjacent_to_target(player_pos, grid_tiles, occupied)
        
        if goal_hex and goal_hex != start_hex:
            # Use movement controller to calculate path
            if self.movement_controller:
                return self.movement_controller.calculate_path(start_hex, goal_hex, occupied, self.mv_limit)
            else:
                # Fallback to direct A* call
                return self._calculate_path_direct(start_hex, goal_hex, occupied, self.mv_limit)
        
        return []
    
    def _calculate_path_direct(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        occupied: Optional[Set[Tuple[int, int]]],
        max_distance: Optional[int]
    ) -> List[Tuple[int, int]]:
        """Direct path calculation without movement controller."""
        if occupied is None:
            occupied = set()
        
        # Create modified grid
        modified_grid = {}
        for tile_pos, tile in self.movement_controller.grid.items() if self.movement_controller else {}:
            new_tile = Tile(tile.type)
            new_tile.cost = tile.cost
            new_tile.blocked = tile.blocked or (tile_pos in occupied)
            new_tile.color = tile.color
            modified_grid[tile_pos] = new_tile
        
        from core.pathfinding.a_star import a_star
        return a_star(start, goal, modified_grid, max_distance)
    
    def start_movement(self, path: List[Tuple[int, int]]):
        """
        Start movement along a path using movement controller.
        
        Args:
            path: List of hex coordinates to follow
        """
        if not path:
            return
        
        if self.movement_controller:
            self.movement_controller.start_movement(
                self.entity_id,
                path,
                tuple(self.pos),
                tuple(self.screen_pos)
            )
            self.queued_path = path
            self.current_path_index = 0
            self.is_moving = True
            print(f"Enemy {self.entity_id} starting movement from {self.pos} along path: {path}")
        else:
            # Fallback
            self.queued_path = path
            self.current_path_index = 0
            self.is_moving = True
    
    def update_movement(self, dt: float) -> bool:
        """
        Update movement using movement controller.
        
        Args:
            dt: Delta time in seconds
        
        Returns:
            True if movement is complete
        """
        if not self.is_moving or not self.movement_controller:
            return True
        
        is_complete, current_hex, current_screen_pos = self.movement_controller.update_movement(self.entity_id, dt)
        
        if is_complete:
            self.pos = list(current_hex)
            self.screen_pos = list(current_screen_pos)
            self.is_moving = False
            self.queued_path = []
            self.current_path_index = 0
            print(f"Enemy {self.entity_id} completed movement, now at hex {self.pos}")
        
        return is_complete
    
    def take_turn(
        self,
        enemies: List['Enemy'],
        player_pos: Tuple[int, int],
        grid_tiles: dict,
        attack_enabled: bool = False
    ):
        """
        Enemy turn: Decide behavior and calculate AI path.
        
        Args:
            enemies: List of all enemies
            player_pos: Player hex coordinates
            grid_tiles: Dictionary of grid tiles
            attack_enabled: Whether attacks are enabled
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
        
        self.targeting_player = (behavior == 'chase')
        
        print(f"Enemy {self.entity_id} at {self.pos} taking turn - dist to player: {dist}, behavior: {behavior}")
        
        # Attack if adjacent and attacks enabled
        if attack_enabled and dist <= 3:
            self.attack_this_turn = True
        
        if self.attack_this_turn:
            path = []
        else:
            path = self.calculate_ai_path(player_pos, grid_tiles, enemies, behavior)
        
        if path and not self.is_moving:
            self.start_movement(path)
            print(f"Enemy {self.entity_id} {behavior}ing with path length: {len(path)}")
        elif path:
            print(f"Enemy {self.entity_id} wants to {behavior} but already moving")
        else:
            print(f"Enemy {self.entity_id} failed to find path for {behavior}")
    
    def draw(self, screen, dt: float):
        """
        Render enemy and update animation.
        
        Args:
            screen: Pygame screen
            dt: Delta time in seconds
        """
        self.renderer.update(dt, self.is_moving)
        self.renderer.draw_enemy(screen, int(self.screen_pos[0]), int(self.screen_pos[1]))
    
    def update_hp(self, damage: int):
        """Apply damage to enemy."""
        self.hp = max(0, self.hp - damage)
    
    def is_alive(self) -> bool:
        """Check if enemy is alive."""
        return self.hp > 0