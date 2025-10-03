# Game Design Document: DW Game Dev

## Overview
DW Game Dev is a 2D tactical RPG inspired by the classic tabletop system *Dragon Warriors* (DW). Players explore a hexagonal grid-based world, engaging in turn-based combat and resolving encounters. The game emphasizes strategic movement, decision-making, and replayability through configurable mechanics and modular design.

## Core Design Principles
- **Turn-Based Strategy**: Combat is lockstep, alternating turns with timed ticks, allowing players to plan actions carefully.
- **Hexagonal Movement**: Provides more strategic options than square grids, with rotational symmetry for balanced gameplay.
- **Server Validation**: Ensures fair play and cheat prevention, with offline fallback for robustness.
- **Modularity**: All mechanics are granular, configurable, and extensible, enabling expansions without core changes.
- **Classic RPG Elements**: HP, MV, attacks inspired by DW rules, but streamlined for digital play.

## Game Mechanics

### Exploration Mode
- **Objective**: Navigate the map to reach the goal hex (e.g., quest target).
- **Movement**: Free exploration with high MV (99), paths queued via mouse clicks.
- **Enemies**: Spawn randomly, patrol, or chase based on AI.
- **Perks**: Relaxed pacing for world-building; easy to implement procedural generation.

### Combat Mode
- **Entry**: Triggered by proximity or manual switch ('C' key).
- **Structure**: Lockstep rounds every 3 seconds (configurable).
  - Player plans path within MV limit.
  - Enemies decide actions (attack or move).
  - Simultaneous execution for exciting resolution.
- **Attacks**: Melee (d6 at distance=1), ranged (d6 - distance if enabled).
- **Perks**: Tactical depth from simultaneous moves; encourages positioning.

### AI Behaviors
- **Chase**: Pursuit within 15 hexes.
- **Patrol**: Random movement when safe (outside 15 hexes).
- **Retreat**: Flee when HP ≤ 30%.
- **Perks**: Dynamic encounters without scripting; easily balanced.

## Character Progression
- (Placeholder: Not implemented) Levels, stats augmentation.
- **Perks**: Flat start for core focus; expandable with config files.

## Terrain and Environment
- Plains (normal), Forest (future modifiers), Walls (blocking).
- **Design Choice**: Procedural generation biased towards fair exploration.
- **Perks**: Easy to add biomes, weather, elevation later.

## UI and Feedback
- Health bars, attack arrows, sand clock for timers.
- **Perks**: Clear visual cues; extensible with animations.

## Server Integration
- Validates moves, paths; supports multiplayer or anti-cheat.
- **Design Choice**: REST API for simplicity.
- **Perks**: Secure; offline mode for testing.

## Perks and Advantages
- **Configurability**: All settings (MV, damage, timers) in `config.yaml` – no code edits needed.
- **Modularity**: Each mechanic in separate files (<1000 lines), with comments for easy contribution.
- **Extensibility**: Class-based design (e.g., Actor subclasses) for adding stats, abilities.
- **Testing**: Unit tests for core logic ensure reliability during development.
- **DW Foundation**: Sticks to tabletop roots for authenticity, but digital enhancements like smooth movement.
- **Developer-Friendly**: Rules enforced in code, with examples in comments.
- **Performance**: Pygame for lightweight rendering, event queue for efficiency.
- **Replayability**: Procedural maps, AI variance, configurable maps.

## Future Expansions
- Multiplayer battles.
- Character classes, magic, inventory.
- Story quests, NPCs.
- Procedural dungeons.
- **Design Note**: Perks are designed for extensibility, e.g., config can add new stats.

This design balances classic RPG depth with modern usability, maintaining DW's spirit while enabling digital innovations.
