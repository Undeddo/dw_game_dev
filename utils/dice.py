"""
DW Reference: Book 1, p. 2-3 (dice rolls).
Purpose: RNG for d20/d100/d6.
Dependencies: None.
Ext Hooks: Add stat rolls.
"""

import random

def roll_d20(seed=None):
    if seed is not None:
        random.seed(seed)
    return random.randint(1, 20)

def roll_d6(seed=None):
    if seed is not None:
        random.seed(seed)
    return random.randint(1, 6)

def roll_3d6(seed=None):
    return roll_d6(seed) + roll_d6() + roll_d6()

# Ext: Stat calculation uses roll_3d6
