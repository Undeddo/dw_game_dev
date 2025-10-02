"""
DW Reference: Book 1, p. 18-19 (movement).
Purpose: Axial hex math (neighbors, distance).
Dependencies: None.
Ext Hooks: Add pathfinding.
"""

def get_neighbors(q, r):
    # Axial coordinates: neighbors in 6 directions
    return [(q+1,r), (q+1,r-1), (q,r-1), (q-1,r), (q-1,r+1), (q,r+1)]

def hex_distance(q1, r1, q2, r2):
    # Formula for axial distance
    return (abs(q1 - q2) + abs(q1 + r1 - q2 - r2) + abs(r1 - r2)) // 2

# DW: 1 hex = 5ft; Mv=6 hexes/round.
