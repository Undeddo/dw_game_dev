import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client.game_controller import GameController

if __name__ == "__main__":
    controller = GameController()
    controller.run()
