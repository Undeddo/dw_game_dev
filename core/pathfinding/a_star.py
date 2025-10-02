"""
DW Reference: Book 1, p.18-19 (terrain mods to Mv).
Purpose: A* pathfinding on hex grid with costs/obstacles.
Dependencies: utils/hex_utils.py (get_neighbors, hex_distance).
Ext Hooks: Add dynamic costs (e.g., encumbrance from future Stats).
Client/Server: Shared logic; client for viz, server for validation.
"""

import heapq
from core.hex.utils import get_neighbors, hex_distance

def a_star(start, goal, grid, max_distance=6):
    """A* pathfinding with cost and obstacle support."""
    INF = float('inf')
    if start not in grid or goal not in grid:
        return []
    if start == goal:
        return [start]
    
    g_score = {start: 0}
    f_score = {start: hex_distance(start[0], start[1], goal[0], goal[1])}
    came_from = {}
    open_set = []
    heapq.heappush(open_set, (f_score[start], start))
    open_set_hash = {start}
    
    while open_set:
        current = heapq.heappop(open_set)[1]
        open_set_hash.remove(current)
        
        if current == goal:
            # Reconstruct path
            path = reconstruct_path(came_from, current, start)
            if max_distance is not None and isinstance(max_distance, int) and len(path) > max_distance + 1:
                path = path[:max_distance + 1]
            print(f"A* found path: {path}")  # Debug: Show the computed path
            return path
        
        for neighbor in get_neighbors(current[0], current[1]):
            if neighbor not in grid or grid[neighbor].blocked:
                continue
            tentative_g_score = g_score[current] + grid[neighbor].cost
            
            if tentative_g_score < g_score.get(neighbor, INF):
                from_pos = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + hex_distance(neighbor[0], neighbor[1], goal[0], goal[1])
                came_from[neighbor] = current
                if neighbor not in open_set_hash:
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
                    open_set_hash.add(neighbor)
    
    return []  # No path found

def reconstruct_path(came_from, current, start):
    """Reconstruct path from came_from dict, excluding start."""
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    # Remove start, reverse
    if path and path[-1] == start:
        path.reverse()
        path = path[1:] if path else []
        path.insert(0, start)
    else:
        path.reverse()
    return path
