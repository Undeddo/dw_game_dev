"""
DW Reference: Book 1, p.18-19 (movement).
Purpose: Unified movement controller for player and enemies.
Dependencies: core.hex.utils, core.pathfinding.a_star, client/map/tile.py
Ext Hooks: Add smooth movement interpolation, path smoothing.
Client Only: Movement execution and state management.
"""

import math
from typing import List, Tuple, Optional, Set
from core.hex.utils import hex_distance
from core.pathfinding.a_star import a_star, is_path_valid, get_path_cost
from client.map.tile import Tile


class MovementController:
    """
    Unified movement controller that manages movement for both player and enemies.
    
    Features:
    - Single source of truth for movement state
    - Consistent coordinate handling (always tuples)
    - Smooth movement interpolation
    - Path validation and cost calculation
    - Movement state machine (idle, moving, path_complete)
    """
    
    def __init__(self, grid: dict, hex_size: int, screen_width: int, screen_height: int):
        """
        Initialize the movement controller.
        
        Args:
            grid: Dictionary mapping hex coordinates to Tile objects
            hex_size: Size of each hex in pixels
            screen_width: Screen width for coordinate conversion
            screen_height: Screen height for coordinate conversion
        """
        self.grid = grid
        self.hex_size = hex_size
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Movement speed in pixels per second
        self.move_speed = 100.0
        
        # Track all moving entities
        self.moving_entities: dict = {}
    
    def hex_to_screen(self, q: int, r: int) -> Tuple[float, float]:
        """
        Convert hex coordinates to screen coordinates.
        
        Args:
            q: Hex column coordinate
            r: Hex row coordinate
        
        Returns:
            Tuple of (x, y) screen coordinates
        """
        # Use the same formula as core/hex/grid.py for consistency
        x = self.hex_size * 1.5 * q
        y = self.hex_size * math.sqrt(3) * (r + q / 2)
        # Add screen center offset
        return (x + self.screen_width // 2, y + self.screen_height // 2)
    
    def screen_to_hex(self, screen_x: float, screen_y: float) -> Optional[Tuple[int, int]]:
        """
        Convert screen coordinates to hex coordinates.
        
        Args:
            screen_x: Screen x coordinate
            screen_y: Screen y coordinate
        
        Returns:
            Tuple of (q, r) hex coordinates, or None if invalid
        """
        # Adjust for screen center
        x = screen_x - self.screen_width // 2
        y = screen_y - self.screen_height // 2
        
        # Convert to hex coordinates using the inverse of hex_to_pixel formula
        # x = hex_size * 1.5 * q
        # y = hex_size * sqrt(3) * (r + q/2)
        q = (2.0 / 3.0 * x) / self.hex_size
        r = (y / (self.hex_size * math.sqrt(3))) - q / 2
        
        return self.axial_round(q, r)
    
    def axial_round(self, q: float, r: float) -> Optional[Tuple[int, int]]:
        """
        Round axial coordinates to nearest valid hex.

        Args:
            q: Float q coordinate
            r: Float r coordinate

        Returns:
            Tuple of (q, r) integer coordinates, or None if invalid
        """
        x = q
        z = r
        y = -x - z

        rx = round(x)
        ry = round(y)
        rz = round(z)

        x_diff = abs(rx - x)
        y_diff = abs(ry - y)
        z_diff = abs(rz - z)

        if x_diff > y_diff and x_diff > z_diff:
            rx = -ry - rz
        elif y_diff > z_diff:
            ry = -rx - rz
        else:
            rz = -rx - ry

        hex_pos = (int(rx), int(rz))

        # Check if hex is in grid
        if hex_pos in self.grid:
            return hex_pos

        # If the rounded position is not in grid, try nearby positions
        # This handles edge cases where rounding lands just outside the grid
        for dq in [-1, 0, 1]:
            for dr in [-1, 0, 1]:
                candidate = (hex_pos[0] + dq, hex_pos[1] + dr)
                if candidate in self.grid:
                    return candidate

        # If no valid position found nearby, try to find the closest valid hex
        min_dist = float('inf')
        best_pos = None
        for pos in self.grid.keys():
            dist = abs(pos[0] - rx) + abs(pos[1] - rz)
            if dist < min_dist:
                min_dist = dist
                best_pos = pos

        return best_pos
    
    def calculate_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        occupied: Optional[Set[Tuple[int, int]]] = None,
        max_distance: Optional[int] = None
    ) -> List[Tuple[int, int]]:
        """
        Calculate path from start to goal using A*.
        
        Args:
            start: Starting hex coordinates
            goal: Target hex coordinates
            occupied: Set of hex coordinates that are occupied (blocked)
            max_distance: Maximum path length in moves
        
        Returns:
            List of hex coordinates from start to goal (inclusive)
        """
        if occupied is None:
            occupied = set()
        
        # Create modified grid with occupied tiles blocked
        modified_grid = {}
        for tile_pos, tile in self.grid.items():
            new_tile = Tile(tile.type)
            new_tile.cost = tile.cost
            new_tile.blocked = tile.blocked or (tile_pos in occupied)
            new_tile.color = tile.color
            modified_grid[tile_pos] = new_tile
        
        # Calculate path
        try:
            path = a_star(start, goal, modified_grid, max_distance)
            
            # Validate path
            if path and is_path_valid(path, modified_grid):
                return path
            
            return []
        
        except Exception as e:
            print(f"Path calculation error: {e}")
            return []
    
    def get_path_cost(self, path: List[Tuple[int, int]]) -> int:
        """
        Calculate total cost of a path.
        
        Args:
            path: List of hex coordinates
        
        Returns:
            Total cost of the path
        """
        return get_path_cost(path, self.grid)
    
    def start_movement(
        self,
        entity_id: str,
        path: List[Tuple[int, int]],
        current_hex: Tuple[int, int],
        current_screen_pos: Tuple[float, float]
    ) -> bool:
        """
        Start movement for an entity along a path.
        
        Args:
            entity_id: Unique identifier for the entity
            path: List of hex coordinates to follow
            current_hex: Current hex position
            current_screen_pos: Current screen position
        
        Returns:
            True if movement started successfully
        """
        if not path:
            return False
        
        # Validate path starts at current position
        if path[0] != current_hex:
            print(f"Path doesn't start at current position: {path[0]} != {current_hex}")
            return False
        
        # Store movement state
        self.moving_entities[entity_id] = {
            'path': path,
            'path_index': 0,
            'current_hex': current_hex,
            'current_screen_pos': list(current_screen_pos),
            'is_moving': True
        }
        
        return True
    
    def update_movement(self, entity_id: str, dt: float) -> Tuple[bool, Tuple[int, int], Tuple[float, float]]:
        """
        Update movement for an entity.
        
        Args:
            entity_id: Unique identifier for the entity
            dt: Delta time in seconds
        
        Returns:
            Tuple of (is_complete, current_hex, current_screen_pos)
        """
        if entity_id not in self.moving_entities:
            return (True, (0, 0), (0, 0))
        
        entity = self.moving_entities[entity_id]
        
        if not entity['is_moving']:
            return (True, entity['current_hex'], tuple(entity['current_screen_pos']))
        
        # Check if we've reached the end of the path
        if entity['path_index'] >= len(entity['path']):
            entity['is_moving'] = False
            return (True, entity['current_hex'], tuple(entity['current_screen_pos']))
        
        # Get target hex and screen position
        target_hex = entity['path'][entity['path_index']]
        target_screen = self.hex_to_screen(*target_hex)
        
        # Calculate movement
        dx = target_screen[0] - entity['current_screen_pos'][0]
        dy = target_screen[1] - entity['current_screen_pos'][1]
        dist = math.hypot(dx, dy)
        
        if dist < 10:  # Close enough to snap to target
            entity['current_hex'] = target_hex
            entity['current_screen_pos'] = list(target_screen)
            entity['path_index'] += 1
        else:
            # Move towards target
            t = min(1.0, (self.move_speed * dt) / dist)
            entity['current_screen_pos'][0] += dx * t
            entity['current_screen_pos'][1] += dy * t
        
        return (False, entity['current_hex'], tuple(entity['current_screen_pos']))
    
    def stop_movement(self, entity_id: str) -> bool:
        """
        Stop movement for an entity.
        
        Args:
            entity_id: Unique identifier for the entity
        
        Returns:
            True if movement was stopped
        """
        if entity_id in self.moving_entities:
            del self.moving_entities[entity_id]
            return True
        return False
    
    def get_entity_state(self, entity_id: str) -> Optional[dict]:
        """
        Get current movement state for an entity.
        
        Args:
            entity_id: Unique identifier for the entity
        
        Returns:
            Movement state dictionary, or None if not moving
        """
        return self.moving_entities.get(entity_id)
    
    def clear_all_movement(self):
        """Stop all movement for all entities."""
        self.moving_entities.clear()
    
    def is_entity_moving(self, entity_id: str) -> bool:
        """
        Check if an entity is currently moving.
        
        Args:
            entity_id: Unique identifier for the entity
        
        Returns:
            True if entity is moving
        """
        entity = self.moving_entities.get(entity_id)
        return entity is not None and entity['is_moving']