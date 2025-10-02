"""
DW Reference: Book 1, p. 18-19 (movement).
Purpose: Flask server for game logic.
Dependencies: flask, requests.
Ext Hooks: Add more routes.
Client/Server: Server for logic (echo).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify
from core.pathfinding.a_star import a_star
from client.map.tile import Tile

app = Flask(__name__)

@app.route("/api/move_path", methods=["POST"])
def handle_move_path():
    data = request.json
    if not data or 'start' not in data or 'goal' not in data or 'grid' not in data:
        return jsonify({"error": "Invalid data"}), 400

    start = tuple(data['start'])
    goal = tuple(data['goal'])
    grid_data = data['grid']
    game_mode = data.get('game_mode', 'exploration')

    # Reconstruct grid from data
    grid = {}
    for pos_str, info in grid_data.items():
        pos_str = pos_str.strip("()").replace(" ", "")
        q, r = map(int, pos_str.split(","))
        tile = Tile(info['type'])
        if info['cost'] is None:
            tile.cost = float('inf')
            tile.blocked = info['blocked']
        grid[(q, r)] = tile

    # Compute path
    max_distance = 6 if game_mode == 'combat' else None
    path = a_star(start, goal, grid, max_distance=max_distance)
    if not path:
        return jsonify({"error": "No valid path", "approved_path": []}), 200

    # Path already limited by a_star; no additional cost check needed
    return jsonify({"approved_path": path})

if __name__ == "__main__":
    app.run(debug=True)
