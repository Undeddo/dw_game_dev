"""
DW Reference: N/A (setup).
<<<<<<< HEAD
Purpose: Central configs from yaml for easy customization.
Dependencies: pyyaml.
Ext Hooks: Add game modes.
"""
import yaml
import os

current_dir = os.path.dirname(__file__)
config_file = os.path.join(current_dir, 'config.yaml')

with open(config_file, 'r') as f:
    config = yaml.safe_load(f)

# Game configs
TICK_TIME = config['game']['tick_time']
SERVER_URL = config['game']['server_url']
ENEMY_RANGED_ATTACK_ENABLED = config['game']['enemy_ranged_attack_enabled']
WIN_DURATION = config['game']['win_duration']
MESSAGE_DURATION = config['game']['message_duration']
FLASH_DURATION = config['game']['flash_duration']
MOVE_SPEED = config['game']['move_speed']
MV_LIMIT = config['game']['mv_limit']

# Paths
PLAYER_SPRITE = config['paths']['player_sprite']
ENEMY_SPRITE = config['paths']['enemy_sprite']

# Combat
AUTO_ATTACK_INTERVAL = config['combat']['auto_attack_interval']
DICE_SIDES = config['combat']['dice_sides']

HEX_SIZE = 50  # Can move to yaml if needed
=======
Purpose: Configs for ticks/hexes.
Dependencies: None.
Ext Hooks: Add game modes.
"""

TICK_TIME = 3.0
HEX_SIZE = 50
SERVER_URL = "http://localhost:5000"
>>>>>>> ee48eee (initial commit - existing game files)
