"""
DW Reference: Book 1, p.18-19 (terrain mods to Mv).
Purpose: A* pathfinding on hex grid with costs/obstacles.
Dependencies: core.hex.utils (get_neighbors, hex_distance).
Ext Hooks: Add dynamic costs (e.g., encumbrance from future Stats).
Client/Server: Shared logic; client for viz, server for validation.
"""

import heapq
from typing import List, Tuple, Dict, Set, Optional
from core.hex.utils import get_neighbors, hex_distance


class PathfindingError(Exception):
    """Custom exception for pathfinding errors."""
    pass


def a_star(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    grid: Dict[Tuple[int, int], 'Tile'],
    max_distance: Optional[int] = None
) -> List[Tuple[int, int]]:
    """
    A* pathfinding algorithm for hex grids.
    
    Args:
        start: Starting hex coordinates (q, r)
        goal: Target hex coordinates (q, r)
        grid: Dictionary mapping hex coordinates to Tile objects
        max_distance: Optional maximum path length (number of moves)
    
    Returns:
        List of hex coordinates from start to goal (inclusive)
    
    Raises:
        PathfindingError: If start or goal is invalid
    """
    # Validate inputs
    if start not in grid:
        raise PathfindingError(f"Start position {start} not in grid")
    if goal not in grid:
        raise PathfindingError(f"Goal position {goal} not in grid")
    if start == goal:
        return [start]
    
    # Priority queue: (f_score, g_score, current_position)
    open_set: List[Tuple[int, int, int]] = []
    heapq.heappush(open_set, (0, 0, start))
    
    # Track visited nodes
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    
    # g_score: cost from start to current node
    g_score: Dict[Tuple[int, int], int] = {start: 0}
    
    # f_score: g_score + heuristic (estimated cost to goal)
    f_score: Dict[Tuple[int, int], int] = {start: hex_distance(*start, *goal)}
    
    # Track nodes in open set for O(1) lookup
    open_set_hash: Set[Tuple[int, int]] = {start}
    
    # Track max distance constraint
    max_moves = max_distance if max_distance is not None else float('inf')
    
    while open_set:
        # Get node with lowest f_score
        current_f, current_g, current = heapq.heappop(open_set)
        open_set_hash.remove(current)
        
        # Check if we've exceeded max distance
        if len(came_from) > max_moves + 1:
            # Reconstruct path up to max_distance
            return reconstruct_path(came_from, current, start, max_moves)
        
        # Check if we've reached the goal
        if current == goal:
            return reconstruct_path(came_from, current, start, max_moves)
        
        # Explore neighbors
        for neighbor in get_neighbors(current[0], current[1]):
            # Skip if neighbor is not in grid or is blocked
            if neighbor not in grid or grid[neighbor].blocked:
                continue
            
            # Calculate tentative g_score
            tentative_g = g_score[current] + grid[neighbor].cost
            
            # Skip if we've already found a better path to this neighbor
            if neighbor in g_score and tentative_g >= g_score[neighbor]:
                continue
            
            # This path is better - record it
            came_from[neighbor] = current
            g_score[neighbor] = tentative_g
            f_score[neighbor] = tentative_g + hex_distance(*neighbor, *goal)
            
            # Add to open set if not already there
            if neighbor not in open_set_hash:
                heapq.heappush(open_set, (f_score[neighbor], tentative_g, neighbor))
                open_set_hash.add(neighbor)
    
    # No path found
    return []


def reconstruct_path(
    came_from: Dict[Tuple[int, int], Tuple[int, int]],
    current: Tuple[int, int],
    start: Tuple[int, int],
    max_moves: Optional[int] = None
) -> List[Tuple[int, int]]:
    """
    Reconstruct path from came_from dictionary.
    
    Args:
        came_from: Dictionary mapping nodes to their predecessors
        current: Current node (goal)
        start: Starting node
        max_moves: Optional maximum number of moves to include
    
    Returns:
        List of hex coordinates from start to current (inclusive)
    """
    # Build path from goal to start
    path: List[Tuple[int, int]] = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    
    # Reverse to get start to goal
    path.reverse()
    
    # Remove start if it's at the end (shouldn't happen, but just in case)
    if path and path[-1] == start:
        path.pop()
    
    # Apply max distance constraint
    if max_moves is not None and len(path) > max_moves + 1:
        path = path[:max_moves + 1]
    
    return path


def get_path_cost(path: List[Tuple[int, int]], grid: Dict[Tuple[int, int], 'Tile']) -> int:
    """
    Calculate total cost of a path.
    
    Args:
        path: List of hex coordinates
        grid: Dictionary mapping hex coordinates to Tile objects
    
    Returns:
        Total cost of the path
    """
    if not path:
        return 0
    
    total_cost = 0
    for i in range(len(path) - 1):
        current = path[i]
        next_pos = path[i + 1]
        
        if current in grid and next_pos in grid:
            total_cost += grid[next_pos].cost
    
    return total_cost


def is_path_valid(path: List[Tuple[int, int]], grid: Dict[Tuple[int, int], 'Tile']) -> bool:
    """
    Check if a path is valid (all tiles are passable).
    
    Args:
        path: List of hex coordinates
        grid: Dictionary mapping hex coordinates to Tile objects
    
    Returns:
        True if all tiles in path are passable
    """
    if not path:
        return False
    
    for tile_pos in path:
        if tile_pos not in grid or grid[tile_pos].blocked:
            return False
    
    return True