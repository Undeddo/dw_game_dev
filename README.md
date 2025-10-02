# DW Game Dev - README

## Overview
This project is a 2D hex-based RPG inspired by Dragon Warriors (DW), built with Python and Pygame. It features a client-server architecture for movement validation, turn-based combat, and exploration gameplay on a hexagonal grid.

## Game Mechanics

### Core Movement System
- **Hexagonal Grid**: Flat-top hexagonal tiles using axial coordinates (q, r). Grid size defaults to 10x10.
- **Pathfinding**: A* algorithm finds optimal paths respecting movement limits (MV).
- **Smooth Movement**: Linear interpolation (LERP) at 100 pixels/second for fluid animation.

### Game Modes
- **Exploration Mode**: Free movement with high MV (99). Click hexes to plan and queue paths, validated asynchronously by server.
  - Switch with 'E' key.
- **Combat Mode**: Lockstep turn-based rounds (every 3 seconds, configurable).
  - Planned movements execute simultaneously.
  - Enemies move after player.
  - Switch with 'C' key.

### Player Mechanics
- **HP**: Starts at 10.
- **MV**: 6 hexes limit in combat mode.
- **Attacks**:
  - Melee: d6 damage if adjacent (distance=1).
  - Auto-attack in combat: Every 2 seconds if adjacent.
- **Abilities**: Click to plan movement paths; paths highlight in yellow.

### Enemy Mechanics
- **HP**: Starts at 10.
- **MV**: Unlimited for chasing.
- **AI Behaviors**:
  - **Chase**: Within 10 hexes, direct pursuit towards player.
  - **Patrol**: Random nearby hexes outside chase distance.
  - **Retreat**: Away from player if HP ≤ 30% (3 or less).
- **Attacks**:
  - Melee: d6 if distance=1.
  - Ranged: d6 minus (distance-1) if distance ≤3 (config: ENEMY_RANGED_ATTACK_ENABLED=False by default).
- **Movement**: Mirrors player movement logic for consistency.

### Combat Round Structure
1. Player plans path (planned_path set).
2. Combat tick (every TICK_TIME=3.0s):
   - Player moves along planned path.
   - Enemy takes turn: Recalculates path based on AI, then moves.
   - Enemies attack if within range (random d6 damage).
3. Player auto-attacks if adjacent to enemy (d6 damage every 2s).

### Terrain Types
- **Plain** (green, ~80%): Normal movement.
- **Forest** (brown, ~10%): Future MV modifiers (e.g., slower).
- **Wall** (gray, ~10%): Blocks movement.

### Win/Lose Conditions
- **Win**: Reach goal hex (9,9). Yellow star marker.
- **Lose**: Player HP ≤0. Gray overlay, game over message.

### UI Elements
- **Health Bars**: Green over red, above player/enemies.
- **Attack Indicators**: White arrows for player, red for enemies. Fade after 5s.
- **Sand Clock**: Shows round progress in combat mode.
- **Path Visualization**: Yellow highlights for planned paths.
- **Messages**: Red text for rejections ("Path Rejected!"); green for wins.

### Server Integration
- **Validation**: POST /api/move_path sends path for approval.
- **Offline Fallback**: Local path used if server unresponsive.
- **Rejection Feedback**: Rejected paths flash red for 1s, with message.

## Technical Architecture
- **Client**: Pygame for rendering, input, game loop.
- **Server**: Flask-based, handles validation.
- **Package Layout**:
  - `client/`: Client-side logic.
    - `game.py`: Main game loop, modes, drawing.
    - `enemy.py`: Enemy AI, movement, rendering.
    - `map/hex_grid.py`: Subclass of core HexGrid with Pygame rendering.
    - `actors/`: (Stub) Actors like Player/Enemy dataclasses and AI.
    - `combat/`: (Stub) Combat scheduler and resolver.
    - `network/`: (Stub) HTTP client for server communication.
    - `input/`: (Stub) Input handling.
    - `rendering/`: (Stub) Sprites and additional rendering.
  - `core/`: Shared logic.
    - `config.py`: Constants (TICK_TIME, etc.).
    - `hex/grid.py`: HexGrid core class (logic).
    - `hex/utils.py`: Hex utilities (distance, neighbors).
    - `pathfinding/a_star.py`: A* pathfinding algorithm.
  - `server/`: Server-side validation.
    - `app.py`: Flask server.
    - `routes/map.py`: Move path validation route.
    - `validation.py`, `models.py`: (Stub) Additional validation and Pydantic models.
  - `tests/`: Unit tests.
    - `test_hex.py`: Tests for hex utilities.
    - `test_pathfinding.py`: Tests for A* algorithm.
    - `test_combat.py`, `test_network.py`: (Stub).
  - `utils/`: Remaining utilities (dice, draw helpers).
## Developer Rules
Granulate the game mechanics into multiple files, so that each is not very big (max in the range of 500-1000 lines of code, this limit can in rare occasions be extended).

Make most features and perks configurable, preferably through config files or easily editable parameters, to allow customization without code modifications.

Include complete comments at the beginning of each file, and also inside the functions, classes, or other game mechanics and calculations.

This ensures maintainability, modularity, and easier collaboration. Large files like the current `client/game.py` (over 600 lines) should be split into smaller modules (e.g., separate combat logic, rendering, input handling).

## Testing
Unit tests are added for core functions:
- `tests/test_hex.py`: Hex distance, neighbors, map validation.
- `tests/test_pathfinding.py`: A* pathfinding, blocked cells, movement limits.
Run with `python -m pytest tests/`.

## Developer Rules
Granulate the game mechanics into multiple files, so that each is not very big (max in the range of 500-1000 lines of code, this limit can in rare occasions be extended).

Make most features and perks configurable, preferably through config files or easily editable parameters, to allow customization without code modifications.

This ensures maintainability, modularity, and easier collaboration. Large files like the current `client/game.py` (over 600 lines) should be split into smaller modules (e.g., separate combat logic, rendering, input handling).

Include complete comments at the beginning of each file, and also inside the functions, classes, or other game mechanics and calculations.
