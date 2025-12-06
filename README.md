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
- **HP**: Rolled as d6 * (STR//2 + 1) where STR defaults to 12, resulting in variable starting HP (e.g., 6-36); displays max HP for health bars.
- **MV**: 6 hexes in combat mode; exploration allows 99.
- **Stats**: Players have STR (default 12), AGI (default 10), MR (STR+AGI) for future magic resistance and damage bonuses.
- **Attacks**:
  - Melee: d6 damage (+ STR bonus multiplier) if adjacent (distance=1).
  - Auto-attack in combat: Every 2 seconds if adjacent after movements.
- **Abilities**: Click to queue movement paths; paths highlight yellow; validated asynchronously by server.

### Enemy Mechanics
- **HP**: Fixed at 10; displayed with health bars.
- **MV**: Unlimited for chasing; respectable MV limits in A* calculations.
- **AI Behaviors** (managed by AISystem with throttling):
  - **Chase**: Within 15 hexes (configurable), pursue towards adjacent free hex to player.
  - **Patrol**: Random nearby hexes outside chase range; includes free hex selection to occupy valid positions.
  - **Retreat**: Move away from player if HP ≤30% (3 or less); prioritizes distance for safety.
- **Attacks**:
  - Melee: d6 if distance=1.
  - Ranged: d6 - (distance-1) if distance ≤3 and enabled (ENEMY_RANGED_ATTACK_ENABLED=false by default).
- **Movement**: Simultaneous LERP during lockstep execution phases; queuing and path planning matches player logic.

### Combat Round Structure (Lockstep)
1. **Planning Phase**: Player clicks to set planned path (highlighted); CombatSystem stores enemy plans silently (no immediate moves).
2. **Execution Phase** (every TICK_TIME=3.0s):
   - Player and enemies move simultaneously along planned paths (LERP animation).
   - After all movements complete, resolve attacks based on final positions (no interruption).
3. **Auto-Attacks**: Player auto-attacks adjacent enemies (d6 damage) post-movement if alive; enemies auto-attack player.

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
- **Client**: Pygame for rendering, input, game loop. Modular split into subsystems (state, combat, AI, rendering).
- **Server**: Flask-based, handles move path validation with A* algorithm.
- **Configuration**: Centralized in `core/config.yaml`, loaded via `core/config.py` for easy customization.
- **Package Layout**:
  - `client/`: Client-side logic and rendering.
    - `game.py`: Main Pygame loop, event handling, drawing; integrates subsystems like CombatSystem and AISystem.
    - `game_state.py`: Central GameState dataclass for mutable game state (player/enemies pos, mode, HP, etc.); prevents globals.
    - `enemy.py`: Enemy class with HP, movement, AI path calculation (chase/patrol/retreat), and rendering.
    - `actors/base.py`: ActorStats dataclass for player/enemy stats (STR/AGI/HP/MR, rolled on init), extensible for future character creation.
    - `combat_system.py`: CombatSystem class for lockstep combat rounds (plan then execute phases), handling player/enemy paths and attack resolution.
    - `ai_system.py`: AISystem class for batched enemy AI decisions, throttling updates to reduce spam and improve performance.
    - `map/hex_grid.py`: HexGrid subclass of core HexGrid, adds Pygame rendering and path highlighting.
    - `map/tile.py`: Tile class for terrain types (plain, forest, blocked), with colors and costs.
    - `network/client.py`: NetworkClient class for async HTTP requests with retry and backoff for server communication.
    - `render/character_renderer.py`, `render/enemy_renderer.py`: Renderer classes for animated sprite drawing (player/enemies).
    - `ui/manager.py`: UIManager class for drawing health bars, attack indicators, sand-clock, messages, and popups.
    - `input/`, `rendering/`: Stub modules for future input handling and additional rendering logic.
  - `core/`: Shared logic between client and server.
    - `config.py`: Loads `config.yaml` for configurable settings (timers, sprites, combat params); supports easy modding without code changes.
    - `hex/grid.py`: HexGrid class for core hex math, tile generation, and axial coordinate conversions.
    - `hex/utils.py`: Utilities for hex neighbors and distance calculations.
    - `pathfinding/a_star.py`: A* pathfinding with cost, obstacle, and MV limit support.
  - `server/`: Server-side validation and rules enforcement.
    - `app.py`: Main Flask app with route handlers.
    - `routes/map.py`: Blueprint for /api/move_path validation; reconstructs client grid state for server-side A* computation.
    - `models.py`, `validation.py`: Stub Pydantic models and additional validation logic for future expansions.
  - `tests/`: Unit tests for core functions.
    - `test_hex.py`: Hex distance, neighbors, coordinate conversions.
    - `test_pathfinding.py`: A* pathfinding with blockers, MV limits, costs.
    - `test_combat.py`, `test_network.py`: (Stub) Combat calculations, network requests.
  - `utils/`: Utilities and helpers.
    - `dice.py`: Dice rolling for combat (d6 for damage, extensible to d20/d100).
    - `draw_utils.py`, `draw_combat_ui.py`: Pygame drawing helpers for UI elements (health bars, sand-clock).
    - `generate_sprite.py`: Script to generate placeholder sprite assets (can be ran standalone).
## Developer Rules
Granulate the game mechanics into multiple files, so that each is not very big (max in the range of 500-1000 lines of code, this limit can in rare occasions be extended).

Make most features and perks configurable, preferably through config files or easily editable parameters, to allow customization without code modifications.

Include complete comments at the beginning of each file, and also inside the functions, classes, or other game mechanics and calculations.

## Recent Changes
- **Modular Refactor**: Split monolithic `game.py` into subsystems: `GameState` for centralized state management, `CombatSystem` for lockstep combat logic, `AISystem` for throttled enemy AI, and separate renderers (`CharacterRenderer`, `EnemyRenderer`) for sprite handling.
- **Actor Stats**: Introduced `ActorStats` dataclass for player/enemy stats (STR/AGI/HP/MR) with randomized HP rolling based on STR, enabling future character customization and magic resistance mechanics.
- **Lockstep Combat**: Implemented true simultaneous movement in combat rounds: plan phase stores actions, execute phase moves all entities at once, then resolves attacks.
- **Enhanced AI**: Enemy behaviors (chase/patrol/retreat) managed by `AISystem` with decision-making logic based on distance, HP thresholds, and configurable ranges.
- **Async Server Validation**: Network requests handled asynchronously with retry/backoff; rejection feedback includes path flashing and messages.
- **Configuration System**: All balance/timers (e.g., MV limits, attack intervals) centralized in `core/config.yaml` for easy modding without code changes.
- **UI Manager**: Added `UIManager` for centralized drawing of health bars, attack arrows, sand-clock, and on-screen messages.
- **Pathfinding Extensions**: A* algorithm supports MV limits per mode, cost-based terrain (forests), and obstacle avoidance.
- **Unit Tests**: Expanded test coverage for hex utilities, pathfinding, with stubs for combat and network tests; run with `python -m pytest tests/`.

This architecture promotes maintainability, configurability, and extensibility. Core logic is shared in `core/`, rendering isolated in `client/`, validation server-side. Features like magic, equipment, or multi-level maps can be added by extending existing dataclasses (e.g., ActorStats) and subsystems.

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
