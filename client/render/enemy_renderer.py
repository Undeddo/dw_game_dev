"""
DW Reference: Inspired by player characters/NPCs in DW, with turn-based movement (Book 1, p.87-88).
Purpose: Load and render enemy sprites, handling animation during movement. Mirrors CharacterRenderer but for enemy (red-tinted for visual distinction).
Dependencies: pygame, os; references utils/generate_sprite.py for dynamic sprite if char_sprite absent.
Ext Hooks: Support enemy variants (e.g., color tints for types); extend to combat poses/attacks later.
Client Only: Visuals; enemy logic in client/enemy.py for movement AI.
Grand Scheme: Modular renderer for enemy characters, enabling rich representation (animations, tints) without bloating game.py. Reuses animation logic from character_renderer.py for consistency/smoth movement.
"""

import pygame
import os

class EnemyRenderer:
    def __init__(self, spritesheet_path='client/sprites/enemy.png', frame_count=8, frame_size=(64, 64)):
        """
        Initializes enemy renderer. Tries to load enemy.png; falls back to generating red-tinted player sprite or colored circle placeholder.
        - References: Reuses frame loading from character_renderer.py but applies red tint for enemy identity (visually distinct from green player).
        - Purpose: Provide animated enemy sprite for smooth combat/exploration visuals.
        """
        self.frame_count = frame_count
        self.frame_size = frame_size
        self.animation_fps = 12.0  # Matches player (character_renderer.py) for consistency in smooth animations.
        self.current_frame = 0
        self.time_since_last_frame = 0.0
        self.frames = []
        self.is_moving = False
        frame_width, frame_height = self.frame_size  # Define for all blocks

        # Load enemy spritesheet (parallel to character_renderer.py's try/except)
        full_path = os.path.join(os.getcwd(), spritesheet_path)
        try:
            spritesheet = pygame.image.load(full_path).convert_alpha()
            sheet_width = spritesheet.get_width()
            sheet_height = spritesheet.get_height()
            frame_width, frame_height = self.frame_size

            for i in range(self.frame_count):
                if i * frame_width + frame_width <= sheet_width:
                    rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
                    frame = spritesheet.subsurface(rect).copy()
                    # Apply red tint for enemy contrast (references pygame visuals in tile.py/hex_grid.py)
                    frame.fill((100, 0, 0, 100), special_flags=pygame.BLEND_RGBA_ADD)  # Semi-transparent red overlay for blood-like hue
                    self.frames.append(frame)
        except (FileNotFoundError, pygame.error):
            print(f"Warning: Enemy spritesheet not found at {full_path}. Generating red-tinted player sprite or placeholder.")
            # Fallback: Generate or tint existing sprite (references utils/generate_sprite.py and character_util.png)
            try:
                char_path = 'client/sprites/character.png'
                char_full = os.path.join(os.getcwd(), char_path)
                char_sheet = pygame.image.load(char_full).convert_alpha()
                if char_sheet.get_width() >= self.frame_count * frame_width:
                    for i in range(self.frame_count):
                        rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
                        frame = char_sheet.subsurface(rect).copy()
                        frame.fill((150, 0, 0), special_flags=pygame.BLEND_RGB_ADD)  # Red tint to distinguish from player
                        self.frames.append(frame)
                else:
                    raise FileNotFoundError
            except (FileNotFoundError, pygame.error):
                # Ultimate fallback: Colored circles (references character_renderer.py placeholder)
                self.frames = [pygame.Surface(self.frame_size, pygame.SRCALPHA) for _ in range(self.frame_count)]
                for i, surf in enumerate(self.frames):
                    pygame.draw.circle(surf, (255, 0, 0), (frame_size[0]//2, frame_size[1]//2), 25)  # Red circle for simple enemy
                    pygame.draw.circle(surf, (255, 255, 255), (frame_size[0]//2, frame_size[1]//2), 20)  # Inner white for eye-like effect

    def update(self, dt, is_moving_now):
        """
        Updates animation frame if moving. Mirrors character_renderer.py update for consistent smooth visuals.
        - References: Animation logic from character_renderer.py (shared for reuse in all mobiles).
        - Purpose: Drive frame progression during enemy movement, matching player's smooth LERP feel.
        """
        self.is_moving = is_moving_now
        if self.is_moving:
            self.time_since_last_frame += dt
            if self.time_since_last_frame >= 1.0 / self.animation_fps:
                self.time_since_last_frame = 0.0
                self.current_frame = (self.current_frame + 1) % self.frame_count
        else:
            self.current_frame = 0

    def draw_enemy(self, screen, x, y):
        """
        Draws current enemy frame at position. Mirrors character_renderer.py draw_character for visual consistency.
        - References: Blit logic from game.py/render, adapted for enemy.
        - Purpose: Render enemy sprite centered, usable in game.py main loop for ongoing fights/visuals.
        """
        if self.frames:
            frame = self.frames[self.current_frame]
            screen.blit(frame, (x - self.frame_size[0] // 2, y - self.frame_size[1] // 2))

    def draw_attack_arrow(self, screen, attacker_pos, victim_pos, color=(255, 100, 100)):
        """
        Draws an attack arrow from attacker to victim position.
        - References: draw_attack_arrow in game.py, but with enemy-specific color.
        - Purpose: Visual feedback for enemy attacks with distinct color.
        """
        import pygame
        import math
        
        pygame.draw.line(screen, color, attacker_pos, victim_pos, 3)
        dx = victim_pos[0] - attacker_pos[0]
        dy = victim_pos[1] - attacker_pos[1]
        length = math.hypot(dx, dy)
        if length == 0:
            return
        dx /= length
        dy /= length
        arrow_tip = victim_pos
        p1 = (arrow_tip[0] - dx * 10 - dy * 5, arrow_tip[1] - dy * 10 + dx * 5)
        p2 = (arrow_tip[0] - dx * 10 + dy * 5, arrow_tip[1] - dy * 10 - dx * 5)
        pygame.draw.polygon(screen, color, [arrow_tip, p1, p2])
