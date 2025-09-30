"""
DW Reference: N/A - Client-only visual enhancement.
Purpose: Load and render character sprites, handling animation during movement.
Dependencies: pygame, os.
Ext Hooks: Support multiple characters, directions, states (e.g., combat poses).
Client Only: All visuals; no server impact.
Grand Scheme: Provides modular sprite management for the game's visual layer, enabling rich character representation without bloating the main game loop.
"""

import pygame
import os
<<<<<<< HEAD
from pathlib import Path
=======
>>>>>>> ee48eee (initial commit - existing game files)

class CharacterRenderer:
    def __init__(self, spritesheet_path='client/sprites/character.png', frame_count=8, frame_size=(64, 64)):
        self.frame_count = frame_count
        self.frame_size = frame_size
        self.animation_fps = 12.0
        self.current_frame = 0
        self.time_since_last_frame = 0.0
        self.frames = []
        self.is_moving = False

<<<<<<< HEAD
        # Load spritesheet using absolute path relative to module location
        module_dir = Path(__file__).parent
        full_path = module_dir.parent / 'sprites' / 'character.png'
        try:
            spritesheet = pygame.image.load(str(full_path)).convert_alpha()
=======
        # Load spritesheet
        full_path = os.path.join(os.getcwd(), spritesheet_path)
        try:
            spritesheet = pygame.image.load(full_path).convert_alpha()
>>>>>>> ee48eee (initial commit - existing game files)
            sheet_width = spritesheet.get_width()
            sheet_height = spritesheet.get_height()
            frame_width, frame_height = frame_size

            for i in range(frame_count):
                if i * frame_width + frame_width <= sheet_width:
                    rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
                    frame = spritesheet.subsurface(rect)
                    self.frames.append(frame.copy())  # Copy to prevent subsurface dependency
<<<<<<< HEAD
        except (FileNotFoundError, pygame.error):
            print(f"Warning: Spritesheet not found at {full_path}. Using placeholder.")
            # Create dummy frames if spritesheet missing - fully fill them so they're visible
            self.frames = [pygame.Surface(frame_size, pygame.SRCALPHA) for _ in range(frame_count)]
            for i, surf in enumerate(self.frames):
                # Fill the entire surface with color instead of just an outline
                pygame.draw.rect(surf, (255 - i * 30, 100, i * 30), surf.get_rect())
=======
        except FileNotFoundError:
            print(f"Warning: Spritesheet not found at {full_path}. Using placeholder.")
            # Create dummy frames if spritesheet missing
            self.frames = [pygame.Surface(frame_size, pygame.SRCALPHA) for _ in range(frame_count)]
            for i, surf in enumerate(self.frames):
                pygame.draw.rect(surf, (255 - i * 30, 100, i * 30), surf.get_rect(), 1)
>>>>>>> ee48eee (initial commit - existing game files)
                pygame.draw.circle(surf, (255, 255, 255), (frame_size[0]//2, frame_size[1]//2), 20)

    def update(self, dt, is_moving_now):
        self.is_moving = is_moving_now
        if self.is_moving:
            self.time_since_last_frame += dt
            if self.time_since_last_frame >= 1.0 / self.animation_fps:
                self.time_since_last_frame = 0.0
                self.current_frame = (self.current_frame + 1) % self.frame_count
        else:
            self.current_frame = 0

    def draw_character(self, screen, x, y):
        if self.frames:
            frame = self.frames[self.current_frame]
            screen.blit(frame, (x - self.frame_size[0] // 2, y - self.frame_size[1] // 2))
