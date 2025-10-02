"""
DW Reference: Combat rounds and timing (Book 1, p.80-85).
Purpose: Scheduler for timed events like combat tick, auto-attack, player move.
Dependencies: time module.
Ext Hooks: Add ability scheduling.
Client Only: Game time management.
"""

import time
from typing import Callable, Any

class Event:
    def __init__(self, trigger_time: float, callback: Callable, *args, **kwargs):
        self.trigger_time = trigger_time
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def __lt__(self, other):
        return self.trigger_time < other.trigger_time

class Scheduler:
    def __init__(self):
        self.events = []
        self.current_time = time.time()

    def schedule(self, delay: float, callback: Callable, *args, **kwargs):
        """Schedule a callback after delay seconds."""
        trigger_time = self.current_time + delay
        event = Event(trigger_time, callback, *args, **kwargs)
        self.events.append(event)
        self.events.sort()

    def update(self, delta_seconds: float):
        """Update current time and execute due events."""
        self.current_time += delta_seconds
        while self.events and self.events[0].trigger_time <= self.current_time:
            event = self.events.pop(0)
            try:
                event.callback(*event.args, **event.kwargs)
            except Exception as e:
                print(f"Error in scheduled event: {e}")

    def cancel(self, callback: Callable, *args):
        """Cancel matching events."""
        self.events = [e for e in self.events if not (e.callback == callback and e.args == args)]
