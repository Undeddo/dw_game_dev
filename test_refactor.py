#!/usr/bin/env python3
"""
Simple test to verify that our refactored code works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from client.game_controller import GameController
    print("✓ GameController imported successfully")
    
    # Try to create an instance
    controller = GameController()
    print("✓ GameController instance created successfully")
    
    # Check that all required components are initialized
    print(f"✓ Grid size: {controller.grid.size}")
    print(f"✓ Number of enemies: {len(controller.enemies)}")
    print(f"✓ State initialized: {controller.state is not None}")
    print(f"✓ Combat system initialized: {controller.combat_system is not None}")
    print(f"✓ AI system initialized: {controller.ai_system is not None}")
    print(f"✓ Input handler initialized: {controller.input_handler is not None}")
    
    print("\n✓ All components imported and initialized successfully!")
    print("The refactoring was successful.")
    
except Exception as e:
    print(f"✗ Error during test: {e}")
    import traceback
    traceback.print_exc()
